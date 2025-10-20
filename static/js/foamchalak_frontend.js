let caseDir = "";        // will be fetched from server on load
let dockerImage = "";    // from server
let openfoamVersion = ""; // from server

// Plotting variables and theme
let plotUpdateInterval = null;
let plotsVisible = false;
let aeroVisible = false;
let isUpdatingPlots = false;
let pendingPlotUpdate = false;
let plotsInViewport = true;

// Request management
let abortControllers = new Map();
let requestCache = new Map();
const CACHE_DURATION = 1000; // 1 second cache

// Performance optimization
const outputBuffer = [];
let outputFlushTimer = null;

// Custom color palette
const plotlyColors = {
  blue: '#1f77b4',
  orange: '#ff7f0e',
  green: '#2ca02c',
  red: '#d62728',
  purple: '#9467bd',
  brown: '#8c564b',
  pink: '#e377c2',
  gray: '#7f7f7f',
  yellow: '#bcbd22',
  teal: '#17becf',
  cyan: '#17becf',
  magenta: '#e377c2',
};

// Common plot layout
const plotLayout = {
  font: { family: '"Computer Modern Serif", serif', size: 12 },
  plot_bgcolor: 'rgba(0,0,0,0)',      // Inside of plotting area
  paper_bgcolor: 'rgba(0,0,0,0)',     // Outer area
  margin: { l: 50, r: 20, t: 40, pad: 10 },
  height: 400,
  autosize: true,
  showlegend: true,
  legend: {
    // For changing plot legend location
    // orientation: 'h',
    // y: -0.2,
    // x: 0.1,
    // xanchor: 'left',
    // yanchor: 'middle',
    bgcolor: 'rgba(0,0,0,0)',
    // borderwidth: 0.5
  },
  xaxis: {
    showgrid: false,
    linewidth: 1
  },
  yaxis: {
    showgrid: false,
    linewidth: 1
  }
};

// --- Plotly config ---
const plotConfig = {
  responsive: true,
  displayModeBar: true,
  staticPlot: false,
  scrollZoom: true,
  doubleClick: true,
  showTips: true,
  modeBarButtonsToAdd: [],
  modeBarButtonsToRemove: ['autoScale2d', 'zoomIn2d', 'zoomOut2d', 'lasso2d', 'select2d','pan2d','sendDataToCloud'],
  displaylogo: false
};

// --- Helper: Common line style ---
const lineStyle = {
  width: 2,
  opacity: 0.9
};

// --- Helper: Create bold title ---
const createBoldTitle = (text) => ({
  text: `<b>${text}</b>`, // use HTML bold tag
  font: {
    ...plotLayout?.font,
    size: 22
  }
});

// --- Helper: Download plot as PNG with white background ---
function downloadPlotAsPNG(plotDiv, filename = 'plot.png') {
  if (!plotDiv) return;

  const downloadLayout = {
    ...plotDiv.layout,
    plot_bgcolor: 'white',
    paper_bgcolor: 'white'
  };

  Plotly.toImage(plotDiv, {
    format: 'png',
    width: plotDiv.offsetWidth,
    height: plotDiv.offsetHeight,
    scale: 2,
    layout: downloadLayout
  }).then((dataUrl) => {
    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });
}

// --- Helper: Attach white-bg download button to a plot ---
function attachWhiteBGDownloadButton(plotDiv) {
  plotDiv.layout.paper_bgcolor = 'white';
  plotDiv.layout.plot_bgcolor = 'white';

  if (!plotDiv || plotDiv.dataset.whiteButtonAdded === 'true') return;

  // Copy existing config or default
  const configWithWhiteBG = Object.assign({}, plotDiv._fullLayout?.config || plotConfig || {});

  // Override toImageButtonOptions for white background PNG
  configWithWhiteBG.toImageButtonOptions = {
    format: 'png',
    filename: `${plotDiv.id}_whitebg`,
    height: plotDiv.clientHeight,
    width: plotDiv.clientWidth,
    scale: 2,
    // Ensure background is white
    // Note: Plotly respects paper_bgcolor/layout.bgcolor when saving
  };

  // Add default mode bar with download button (Plotly will now use our options)
  Plotly.react(plotDiv, plotDiv.data, plotDiv.layout, configWithWhiteBG).then(() => {
    plotDiv.dataset.whiteButtonAdded = 'true';
  });
}


// --- Initialize on page load ---
window.onload = async () => {
  try {
    // Load saved tutorial selection if exists
    const tutorialSelect = document.getElementById("tutorialSelect");
    if (tutorialSelect) {
      const savedTutorial = localStorage.getItem('lastSelectedTutorial');
      if (savedTutorial) {
        tutorialSelect.value = savedTutorial;
      }
    }

    // Parallel fetch for better performance
    const [caseRootData, dockerConfigData] = await Promise.all([
      fetchWithCache("/get_case_root"),
      fetchWithCache("/get_docker_config")
    ]);
    
    // Update case directory
    caseDir = caseRootData.caseDir || "";
    const caseDirInput = document.getElementById("caseDir");
    if (caseDirInput) caseDirInput.value = caseDir;
    
    // Update Docker config
    dockerImage = dockerConfigData.dockerImage || "";
    openfoamVersion = dockerConfigData.openfoamVersion || "";
    const openfoamRootInput = document.getElementById("openfoamRoot");
    if (openfoamRootInput) {
      openfoamRootInput.value = `${dockerImage} (OpenFOAM ${openfoamVersion})`;
    }
  } catch (error) {
    console.error('Initialization error:', error);
    appendOutput('Failed to initialize application', 'stderr');
  }
};

// --- Fetch with caching and abort control ---
async function fetchWithCache(url, options = {}) {
  const cacheKey = `${url}_${JSON.stringify(options)}`;
  const cached = requestCache.get(cacheKey);
  
  if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
    return cached.data;
  }
  
  // Cancel previous request to same endpoint
  if (abortControllers.has(url)) {
    abortControllers.get(url).abort();
  }
  
  const controller = new AbortController();
  abortControllers.set(url, controller);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    requestCache.set(cacheKey, { data, timestamp: Date.now() });
    return data;
  } finally {
    abortControllers.delete(url);
  }
}

// --- Append output helper with buffering ---
function appendOutput(message, type="stdout") {
  outputBuffer.push({ message, type });
  
  // Debounce DOM updates for better performance
  if (outputFlushTimer) {
    clearTimeout(outputFlushTimer);
  }
  
  outputFlushTimer = setTimeout(flushOutputBuffer, 16); // ~60fps
}

function flushOutputBuffer() {
  if (outputBuffer.length === 0) return;
  
  const container = document.getElementById("output");
  if (!container) return;
  
  const fragment = document.createDocumentFragment();
  
  outputBuffer.forEach(({ message, type }) => {
    const line = document.createElement("div");
    
    if(type === "stderr") line.className = "text-red-600";
    else if(type === "tutorial") line.className = "text-blue-600 font-semibold";
    else if(type === "info") line.className = "text-yellow-600 italic";
    else line.className = "text-green-700";
    
    line.textContent = message;
    fragment.appendChild(line);
  });
  
  container.appendChild(fragment);
  container.scrollTop = container.scrollHeight;
  outputBuffer.length = 0;
}

// --- Set case directory manually ---
async function setCase() {
  try {
    caseDir = document.getElementById("caseDir").value;
    
    const response = await fetch("/set_case", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({caseDir: caseDir})
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    caseDir = data.caseDir;
    document.getElementById("caseDir").value = caseDir;

    data.output.split('\n').forEach(line => {
      line = line.trim();
      if(line.startsWith("INFO::")) appendOutput(line.replace("INFO::",""), "info");
      else if(line.startsWith("[Error]")) appendOutput(line, "stderr");
      else appendOutput(line, "stdout");
    });
  } catch (error) {
    console.error('Error setting case:', error);
    appendOutput(`Failed to set case directory: ${error.message}`, "stderr");
  }
}

// --- Update Docker config (instead of OpenFOAM root) ---
async function setDockerConfig(image, version) {
  try {
    dockerImage = image;
    openfoamVersion = version;
    
    const response = await fetch("/set_docker_config", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        dockerImage: dockerImage,
        openfoamVersion: openfoamVersion
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    dockerImage = data.dockerImage;
    openfoamVersion = data.openfoamVersion;
    
    const openfoamRootInput = document.getElementById("openfoamRoot");
    if (openfoamRootInput) {
      openfoamRootInput.value = `${dockerImage} (OpenFOAM ${openfoamVersion})`;
    }

    appendOutput(`Docker config set to: ${dockerImage} (OpenFOAM ${openfoamVersion})`, "info");
  } catch (error) {
    console.error('Error setting Docker config:', error);
    appendOutput(`Failed to set Docker config: ${error.message}`, "stderr");
  }
}

// --- Load a tutorial ---
async function loadTutorial() {
  try {
    const tutorialSelect = document.getElementById("tutorialSelect");
    const selected = tutorialSelect.value;
    
    // Save the selected tutorial to localStorage
    if (selected) {
      localStorage.setItem('lastSelectedTutorial', selected);
    }

    const response = await fetch("/load_tutorial", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({tutorial: selected})
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Do not overwrite caseDir input — keep it as the run folder
    data.output.split('\n').forEach(line => {
      line = line.trim();
      if(line.startsWith("INFO::[FOAMChalak] Tutorial loaded::")) {
        appendOutput(line.replace("INFO::[FOAMChalak] Tutorial loaded::","Tutorial loaded: "), "tutorial");
      } else if(line.startsWith("Source:") || line.startsWith("Copied to:")) {
        appendOutput(line, "info");
      } else {
        const type = /error/i.test(line) ? "stderr" : "stdout";
        appendOutput(line, type);
      }
    });
  } catch (error) {
    console.error('Error loading tutorial:', error);
    appendOutput(`Failed to load tutorial: ${error.message}`, "stderr");
  }
}

// --- Run OpenFOAM commands ---
async function runCommand(cmd) {
  if (!cmd) {
    appendOutput("Error: No command specified!", "stderr");
    return;
  }
  
  try {
    const selectedTutorial = document.getElementById("tutorialSelect").value;
    const outputDiv = document.getElementById("output");
    outputDiv.innerHTML = ""; // clear previous output
    outputBuffer.length = 0; // clear buffer

    const response = await fetch("/run", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        caseDir: caseDir,
        tutorial: selectedTutorial,
        command: cmd
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    async function read() {
      try {
        const {done, value} = await reader.read();
        if (done) {
          flushOutputBuffer(); // Ensure all output is flushed
          return;
        }
        
        const text = decoder.decode(value);
        text.split("\n").forEach(line => {
          if (!line.trim()) return;
          const type = /error/i.test(line) ? "stderr" : "stdout";
          appendOutput(line, type);
        });
        
        await read();
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('Stream reading error:', error);
          appendOutput(`Stream error: ${error.message}`, "stderr");
        }
      }
    }
    
    await read();
  } catch (error) {
    console.error('Error running command:', error);
    appendOutput(`Failed to run command: ${error.message}`, "stderr");
  }
}

// --- Realtime Plotting Functions ---
function togglePlots() {
  plotsVisible = !plotsVisible;
  const container = document.getElementById('plotsContainer');
  const btn = document.getElementById('togglePlotsBtn');
  const aeroBtn = document.getElementById('toggleAeroBtn');
  
  if (plotsVisible) {
    container.classList.remove('hidden');
    btn.textContent = 'Hide Plots';
    aeroBtn.classList.remove('hidden');
    startPlotUpdates();
    setupIntersectionObserver();
  } else {
    container.classList.add('hidden');
    btn.textContent = 'Show Plots';
    aeroBtn.classList.add('hidden');
    stopPlotUpdates();
  }
}

// Setup Intersection Observer to pause updates when plots are not visible
function setupIntersectionObserver() {
  const plotsContainer = document.getElementById('plotsContainer');
  
  if (!plotsContainer || plotsContainer.dataset.observerSetup) {
    return;
  }
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      plotsInViewport = entry.isIntersecting;
    });
  }, {
    threshold: 0.1,
    rootMargin: '50px'
  });
  
  observer.observe(plotsContainer);
  plotsContainer.dataset.observerSetup = 'true';
}

function toggleAeroPlots() {
  aeroVisible = !aeroVisible;
  const container = document.getElementById('aeroContainer');
  const btn = document.getElementById('toggleAeroBtn');
  
  if (aeroVisible) {
    container.classList.remove('hidden');
    btn.textContent = 'Hide Aero Plots';
    updateAeroPlots();
  } else {
    container.classList.add('hidden');
    btn.textContent = 'Show Aero Plots';
  }
}

function startPlotUpdates() {
  updatePlots(); // Initial update
  plotUpdateInterval = setInterval(() => {
    // Skip updates if plots are not in viewport or already updating
    if (!plotsInViewport) {
      return;
    }
    if (!isUpdatingPlots) {
      updatePlots();
    } else {
      pendingPlotUpdate = true;
    }
  }, 2000); // Update every 2 seconds
}

function stopPlotUpdates() {
  if (plotUpdateInterval) {
    clearInterval(plotUpdateInterval);
    plotUpdateInterval = null;
  }
}

async function updatePlots() {
  const selectedTutorial = document.getElementById("tutorialSelect").value;
  if (!selectedTutorial || isUpdatingPlots) {
    return;
  }
  
  isUpdatingPlots = true;
  
  try {
    const data = await fetchWithCache(`/api/plot_data?tutorial=${encodeURIComponent(selectedTutorial)}`);
      if (data.error) {
        console.error('Error fetching plot data:', data.error);
        return;
      }
      
      // --- Pressure plot ---
      if (data.p && data.time) {
        const pressureTrace = {
          x: data.time,
          y: data.p,
          type: 'scatter',
          mode: 'lines',
          name: 'Pressure',
          line: {
            color: plotlyColors.blue,
            ...lineStyle,
            width: 2.5
          },
        };
        
        Plotly.react('pressure-plot', [pressureTrace], {
          ...plotLayout,
          title: createBoldTitle('Pressure vs Time'),
          xaxis: {
            ...plotLayout.xaxis,
            title: 'Time (s)'
          },
          yaxis: {
            ...plotLayout.yaxis,
            title: 'Pressure (Pa)'
          },
        }, plotConfig).then(() => attachWhiteBGDownloadButton(document.getElementById('pressure-plot')));
      }
      
      // --- Velocity plot ---
      if (data.U_mag && data.time) {
        const traces = [
          {
            x: data.time,
            y: data.U_mag,
            type: 'scatter',
            mode: 'lines',
            name: '|U|',
            line: {
              color: plotlyColors.red,
              ...lineStyle,
              width: 2.5
            }
          }
        ];
        
        if (data.Ux) {
          traces.push({
            x: data.time,
            y: data.Ux,
            type: 'scatter',
            mode: 'lines',
            name: 'Ux',
            line: {
              color: plotlyColors.blue,
              ...lineStyle,
              dash: 'dash',
              width: 2.5
            }
          });
        }
        if (data.Uy) {
          traces.push({
            x: data.time,
            y: data.Uy,
            type: 'scatter',
            mode: 'lines',
            name: 'Uy',
            line: {
              color: plotlyColors.green,
              ...lineStyle,
              dash: 'dot',
              width: 2.5
            }
          });
        }
        if (data.Uz) {
          traces.push({
            x: data.time,
            y: data.Uz,
            type: 'scatter',
            mode: 'lines',
            name: 'Uz',
            line: {
              color: plotlyColors.purple,
              ...lineStyle,
              dash: 'dashdot',
              width: 2.5
            }
          });
        }
        
        Plotly.react('velocity-plot', traces, {
          ...plotLayout,
          title: createBoldTitle('Velocity vs Time'),
          xaxis: {
            ...plotLayout.xaxis,
            title: 'Time (s)'
          },
          yaxis: {
            ...plotLayout.yaxis,
            title: 'Velocity (m/s)'
          }
        }, plotConfig).then(() => attachWhiteBGDownloadButton(document.getElementById('velocity-plot')));
      }
      
      // --- Turbulence plot ---
      const turbTraces = [];
      if (data.nut && data.time) {
        turbTraces.push({
          x: data.time,
          y: data.nut,
          type: 'scatter',
          mode: 'lines',
          name: 'nut',
          line: {
            color: plotlyColors.teal,
            ...lineStyle,
            width: 2.5},
        });
      }
      if (data.nuTilda && data.time) {
        turbTraces.push({
          x: data.time,
          y: data.nuTilda,
          type: 'scatter',
          mode: 'lines',
          name: 'nuTilda',
          line: {
            color: plotlyColors.cyan,
            ...lineStyle,
            width: 2.5},
        });
      }
      if (data.k && data.time) {
        turbTraces.push({
          x: data.time,
          y: data.k,
          type: 'scatter',
          mode: 'lines',
          name: 'k',
          line: {
            color: plotlyColors.magenta,
            ...lineStyle,
            width: 2.5},
        });
      }
      if (data.omega && data.time) {
        turbTraces.push({
          x: data.time,
          y: data.omega,
          type: 'scatter',
          mode: 'lines',
          name: 'omega',
          line: {
            color: plotlyColors.brown,
            ...lineStyle,
            width: 2.5},
        });
      }
      
      if (turbTraces.length > 0) {
        Plotly.react('turbulence-plot', turbTraces, {
          ...plotLayout,
          title: createBoldTitle('Turbulence Properties vs Time'),
          xaxis: {
            ...plotLayout.xaxis,
            title: 'Time (s)'
          },
          yaxis: {
            ...plotLayout.yaxis,
            title: 'Value'
          },
        }, plotConfig).then(() => attachWhiteBGDownloadButton(document.getElementById('turbulence-plot')));
      }
      
      // Update residuals and aero plots in parallel
      const updatePromises = [updateResidualsPlot(selectedTutorial)];
      if (aeroVisible) {
        updatePromises.push(updateAeroPlots());
      }
      
      await Promise.allSettled(updatePromises);
  } catch (err) {
    console.error('Error updating plots:', err);
  } finally {
    isUpdatingPlots = false;
    if (pendingPlotUpdate) {
      pendingPlotUpdate = false;
      requestAnimationFrame(updatePlots);
    }
  }
}

async function updateResidualsPlot(tutorial) {
  try {
    const data = await fetchWithCache(`/api/residuals?tutorial=${encodeURIComponent(tutorial)}`);
    if (data.error || !data.time || data.time.length === 0) {
      return;
    }
    
    const traces = [];
    const fields = ['Ux', 'Uy', 'Uz', 'p'];
    const colors = [
      plotlyColors.blue,
      plotlyColors.red,
      plotlyColors.green,
      plotlyColors.magenta,
      plotlyColors.cyan,
      plotlyColors.orange
    ];
    
    fields.forEach((field, idx) => {
      if (data[field] && data[field].length > 0) {
        traces.push({
          x: Array.from({length: data[field].length}, (_, i) => i + 1), // Iteration number
          y: data[field],
          type: 'scatter',
          mode: 'lines',
          name: field,
          line: {
            color: colors[idx],
            width: 2.5,
            shape: 'linear'
          }
        });
      }
    });
    
    if (traces.length > 0) {
      const layout = {
        ...plotLayout,
        title: createBoldTitle('Residuals'),
        xaxis: {
          title: {
            text: 'Iteration',
          },
          showline: true,
          mirror: 'all',  // This will mirror the line on all sides
          showgrid: false
        },
        yaxis: {
          title: {
            text: 'Residual',
          },
          type: 'log',
          showline: true,
          mirror: 'all',
          showgrid: true,
          // gridwidth: 1,
          // gridcolor: 'rgba(0,0,0,0.1)'
        },
      };

      Plotly.react('residuals-plot', traces, layout, {
        ...plotConfig,
        displayModeBar: true,
        scrollZoom: false
      }).then(() => attachWhiteBGDownloadButton(document.getElementById('residuals-plot')));
    }
  } catch (err) {
    console.error('Error updating residuals:', err);
  }
}

async function updateAeroPlots() {
  const selectedTutorial = document.getElementById("tutorialSelect").value;
  if (!selectedTutorial) {
    return;
  }
  
  try {
    // Fetch latest data for aerodynamic calculations
    const data = await fetchWithCache(`/api/latest_data?tutorial=${encodeURIComponent(selectedTutorial)}`);
      if (data.error) {
        console.error('Error fetching aero data:', data.error);
        return;
      }
      
      // Calculate and plot pressure coefficient
      if (Array.isArray(data.p) && Array.isArray(data.time) && data.p.length === data.time.length && data.p.length > 0) {
        const p_inf = 101325;
        const rho = 1.225;
        const u_inf = Array.isArray(data.U_mag) ? data.U_mag[0] : data.U_mag || 1.0;
        const q_inf = 0.5 * rho * u_inf * u_inf || 1.0;

        const cp = data.p.map(p_val => (p_val - p_inf) / q_inf);

        console.log('Cp plot data:', {x: data.time, y: cp, q_inf}); // debug

        const cpTrace = {
          x: data.time,
          y: cp,
          type: 'scatter',
          mode: 'lines+markers',
          name: 'Cp',
          line: {color: plotlyColors.red, width: 2.5}
        };

        const cpDiv = document.getElementById('cp-plot');
        if (cpDiv) {
          Plotly.react('cp-plot', [cpTrace], {
            ...plotLayout,
            title: createBoldTitle('Pressure Coefficient'),
            xaxis: {title: 'Time (s)'},
            yaxis: {title: 'Cp'}
          }, plotConfig).then(() => attachWhiteBGDownloadButton(document.getElementById('cp-plot')));
        } else {
          console.warn('cp-plot div not found!');
        }
      } else {
        console.warn('Cp data invalid or length mismatch:', data.p, data.time);
      }
          
      // Plot velocity profile
      if (data.Ux && data.Uy && data.Uz) {
        const velocityTrace = {
          x: [data.Ux],
          y: [data.Uy],
          z: [data.Uz],
          type: 'scatter3d',
          mode: 'markers',
          name: 'Velocity',
          marker: {color: plotlyColors.blue, size: 5}
        };
        
        Plotly.react('velocity-profile-plot', [velocityTrace], {
          ...plotLayout,
          title: createBoldTitle('Velocity Profile'),
          scene: {
            xaxis: {title: 'Ux (m/s)'},
            yaxis: {title: 'Uy (m/s)'},
            zaxis: {title: 'Uz (m/s)'}
          },
        }, plotConfig);
        
        attachWhiteBGDownloadButton(document.getElementById('velocity-profile-plot'));
      }
  } catch (err) {
    console.error('Error updating aero plots:', err);
  }
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
  stopPlotUpdates();
  
  // Cancel all pending requests
  abortControllers.forEach(controller => controller.abort());
  abortControllers.clear();
  
  // Clear cache
  requestCache.clear();
  
  // Flush any remaining output
  flushOutputBuffer();
});
