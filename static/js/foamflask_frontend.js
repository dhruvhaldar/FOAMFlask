let caseDir = "";        // will be fetched from server on load
let dockerImage = "";    // from server
let openfoamVersion = ""; // from server

// Page management
let currentPage = 'setup';

// Mesh visualization state
let currentMeshPath = null;
let availableMeshes = [];
let isInteractiveMode = false;

// Notification management
let notificationId = 0;

// Plotting variables and theme
let plotUpdateInterval = null;
let plotsVisible = true; // Set to true by default to show plots
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
  plot_bgcolor: 'white',      // Inside of plotting area
  paper_bgcolor: '#f9fafb',     // Outer area
  margin: { l: 50, r: 20, t: 40, pad: 0 },
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
    // bgcolor: 'white',
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
    font: {
    ...plotLayout.font,
    color: 'black'
    },
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

// --- Helper: Save current legend visibility ---
function getLegendVisibility(plotDiv) {
  if (!plotDiv || !plotDiv.data) return {};
  const visibility = {};
  plotDiv.data.forEach(trace => {
    visibility[trace.name] = trace.visible !== undefined ? trace.visible : true;
  });
  return visibility;
}

// --- Helper: Apply saved legend visibility to new traces ---
function applyLegendVisibility(plotDiv, visibility) {
  if (!plotDiv || !plotDiv.data || !visibility) return;
  plotDiv.data.forEach(trace => {
    if (visibility.hasOwnProperty(trace.name)) {
      trace.visible = visibility[trace.name];
    }
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


// --- Page Switching ---
function switchPage(pageName) {
  // Hide all pages
  const pages = ['setup', 'run', 'mesh', 'plots'];
  pages.forEach(page => {
    const pageElement = document.getElementById(`page-${page}`);
    const navButton = document.getElementById(`nav-${page}`);
    
    if (pageElement) {
      pageElement.classList.add('hidden');
    }
    
    if (navButton) {
      navButton.classList.remove('bg-blue-500', 'text-white');
      navButton.classList.add('text-gray-700', 'hover:bg-gray-100');
    }
  });
  
  // Show selected page
  const selectedPage = document.getElementById(`page-${pageName}`);
  const selectedNav = document.getElementById(`nav-${pageName}`);
  
  if (selectedPage) {
    selectedPage.classList.remove('hidden');
  }
  
  if (selectedNav) {
    selectedNav.classList.add('bg-blue-500', 'text-white');
    selectedNav.classList.remove('text-gray-700', 'hover:bg-gray-100');
  }
  
  currentPage = pageName;
  
  // Page-specific initializations
  switch(pageName) {
    case 'plots':
      // Ensure plots container is visible
      const plotsContainer = document.getElementById('plotsContainer');
      if (plotsContainer) {
        plotsContainer.classList.remove('hidden');
        
        // Initialize plots if they haven't been initialized yet
        if (!plotsContainer.hasAttribute('data-initialized')) {
          plotsContainer.setAttribute('data-initialized', 'true');
          // Start plot updates if not already running
          if (!plotUpdateInterval) {
            startPlotUpdates();
          }
        }
      }
      
      // Update the aero plots button state
      const aeroBtn = document.getElementById('toggleAeroBtn');
      if (aeroBtn) {
        aeroBtn.classList.toggle('hidden', aeroVisible);
      }
      break;
      
    case 'mesh':
      // Initialize mesh visualization if needed
      const meshContainer = document.getElementById('page-mesh');
      if (meshContainer && !meshContainer.hasAttribute('data-initialized')) {
        meshContainer.setAttribute('data-initialized', 'true');
        console.log('Mesh page initialized');
        // Load available meshes
        refreshMeshList();
      }
      break;
  }
}

// --- Notification System ---
function showNotification(message, type = 'info', duration = 3000) {
  const container = document.getElementById('notificationContainer');
  if (!container) return;
  
  const id = notificationId++;
  const notification = document.createElement('div');
  notification.id = `notification-${id}`;
  notification.className = `notification pointer-events-auto px-4 py-3 rounded-lg shadow-lg max-w-sm overflow-hidden`;
  
  // Set color based on type
  const colors = {
    'success': 'bg-green-500 text-white',
    'error': 'bg-red-500 text-white',
    'warning': 'bg-yellow-500 text-white',
    'info': 'bg-blue-500 text-white'
  };
  
  notification.className += ` ${colors[type] || colors.info}`;
  
  // Add icon based on type
  const icons = {
    'success': '✓',
    'error': '✕',
    'warning': '⚠',
    'info': 'ℹ'
  };

  // Create progress bar
  const progressBar = document.createElement('div');
  progressBar.className = 'h-1 bg-white bg-opacity-50 absolute bottom-0 left-0';
  progressBar.style.width = '100%';
  progressBar.style.transition = 'width linear';
  progressBar.style.transitionDuration = `${duration}ms`;
  
  notification.innerHTML = `
    <div class="relative">
      <div class="flex items-center justify-between gap-3 relative z-10">
        <div class="flex items-center gap-2">
          <span class="text-lg font-bold">${icons[type] || icons.info}</span>
          <span class="text-sm">${message}</span>
        </div>
        <div class="flex items-center gap-2">
          <span id="countdown-${id}" class="text-xs opacity-75">${(duration/1000).toFixed(1)}s</span>
          <button onclick="event.stopPropagation(); removeNotification(${id})" class="text-white hover:text-gray-200 font-bold text-lg leading-none">
            ×
          </button>
        </div>
      </div>
    </div>
  `;
  
  notification.style.position = 'relative';
  notification.appendChild(progressBar);
  container.appendChild(notification);
  
  // Start countdown
  let timeLeft = duration;
  const countdownInterval = setInterval(() => {
    timeLeft -= 100;
    if (timeLeft <= 0) {
      clearInterval(countdownInterval);
      removeNotification(id);
      return;
    }
    document.getElementById(`countdown-${id}`).textContent = `${(timeLeft/1000).toFixed(1)}s`;
  }, 100);
  
  // Animate progress bar
  setTimeout(() => {
    progressBar.style.width = '0%';
  }, 10);
  
  // Store the interval ID for cleanup
  notification.dataset.intervalId = countdownInterval;
}

function removeNotification(id) {
  const notification = document.getElementById(`notification-${id}`);
  if (notification) {
    // Clear the countdown interval
    if (notification.dataset.intervalId) {
      clearInterval(notification.dataset.intervalId);
    }
    notification.style.opacity = '0';
    notification.style.transition = 'opacity 0.3s ease';
    setTimeout(() => {
      notification.remove();
    }, 300);
  }
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
    console.error('[FOAMFlask] Initialization error:', error);
    appendOutput('[FOAMFlask] Failed to initialize application', 'stderr');
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
    
    showNotification('Case directory set', 'info');
  } catch (error) {
    console.error('[FOAMFlask] Error setting case:', error);
    appendOutput(`[FOAMFlask] Failed to set case directory: ${error.message}`, "stderr");
    showNotification('Failed to set case directory', 'error');
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
    showNotification('Docker config updated', 'success');
  } catch (error) {
    console.error('[FOAMFlask] Error setting Docker config:', error);
    appendOutput(`[FOAMFlask] Failed to set Docker config: ${error.message}`, "stderr");
    showNotification('Failed to set Docker config', 'error');
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
    if(line.startsWith("INFO::[FOAMFlask] Tutorial loaded::")) {
      appendOutput(line.replace("INFO::[FOAMFlask] Tutorial loaded::","[FOAMFlask] Tutorial loaded: "), "tutorial");
    } else if(line.startsWith("Source:")) {
      appendOutput(`[FOAMFlask] ${line}`, "info");
    } else if(line.startsWith("Copied to:")) {
      appendOutput(`[FOAMFlask] ${line}`, "info");
    } else {
      const type = /error/i.test(line) ? "stderr" : "stdout";
      appendOutput(line, type);
    }
  });
    
    showNotification('Tutorial loaded', 'info');
  } catch (error) {
    console.error('[FOAMFlask] Error loading tutorial:', error);
    appendOutput(`[FOAMFlask] Failed to load tutorial: ${error.message}`, "stderr");
    showNotification('Failed to load tutorial', 'error');
  }
}

// --- Run OpenFOAM commands ---
async function runCommand(cmd) {
  if (!cmd) {
    appendOutput("[FOAMFlask] Error: No command specified!", "stderr");
    showNotification('No command specified', 'error');
    return;
  }
  
  try {
    const selectedTutorial = document.getElementById("tutorialSelect").value;
    const outputDiv = document.getElementById("output");
    outputDiv.innerHTML = ""; // clear previous output
    outputBuffer.length = 0; // clear buffer
    
    showNotification(`Running ${cmd}...`, 'info');

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
          showNotification(`Command ${cmd} completed`, 'success');
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
          console.error('[FOAMFlask] Stream reading error:', error);
          appendOutput(`[FOAMFlask] Stream error: ${error.message}`, "stderr");
        }
      }
    }
    
    await read();
  } catch (error) {
    console.error('[FOAMFlask] Error running command:', error);
    appendOutput(`[FOAMFlask] Failed to run command: ${error.message}`, "stderr");
    showNotification('Command execution failed', 'error');
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
        console.error('[FOAMFlask] Error fetching plot data:', data.error);
        return;
      }
      
      // --- Pressure plot ---
      if (data.p && data.time) {

        const pressureDiv = document.getElementById('pressure-plot');

        // Save old legend visibility
        const legendVisibility = getLegendVisibility(pressureDiv);

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

        // Apply saved visibility to the new trace
        if (legendVisibility.hasOwnProperty(pressureTrace.name)) {
            pressureTrace.visible = legendVisibility[pressureTrace.name];
          }
        
        Plotly.react(pressureDiv, [pressureTrace], {
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
        }, plotConfig).then(() => attachWhiteBGDownloadButton(pressureDiv));
      }
      
      // --- Velocity plot ---
      if (data.U_mag && data.time) {

        const velocityDiv = document.getElementById('velocity-plot');

        // Save old legend visibility
        const legendVisibility = getLegendVisibility(velocityDiv);

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

        // Apply saved visibility to the new trace
        if (legendVisibility.hasOwnProperty(traces[0].name)) {
          traces[0].visible = legendVisibility[traces[0].name];
        }
        
        Plotly.react(velocityDiv, traces, {
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
        }, plotConfig).then(() => attachWhiteBGDownloadButton(velocityDiv));
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
    console.error('[FOAMFlask] Error updating plots:', err);
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
    console.error('[FOAMFlask] Error updating residuals:', err);
  }
}

async function updateAeroPlots() {
  const selectedTutorial = document.getElementById("tutorialSelect").value;
  if (!selectedTutorial) return;

  try {
    const response = await fetch(`/api/latest_data?tutorial=${encodeURIComponent(selectedTutorial)}`);
    const data = await response.json();
    if (data.error) return;

    // --- Cp plot ---
    if (Array.isArray(data.p) && Array.isArray(data.time) && data.p.length === data.time.length && data.p.length > 0) {
      const p_inf = 101325;
      const rho = 1.225;
      const u_inf = Array.isArray(data.U_mag) && data.U_mag.length ? data.U_mag[0] : 1.0;
      const q_inf = 0.5 * rho * u_inf * u_inf;

      const cp = data.p.map(p_val => (p_val - p_inf) / q_inf);

      const cpDiv = document.getElementById('cp-plot');
      if (cpDiv) {
        const cpTrace = { x: data.time, y: cp, type: 'scatter', mode: 'lines+markers', name: 'Cp', line: {color: plotlyColors.red, width: 2.5} };
        Plotly.react(cpDiv, [cpTrace], {
          ...plotLayout,
          title: createBoldTitle('Pressure Coefficient'),
          xaxis: {title: 'Time (s)'},
          yaxis: {title: 'Cp'}
        }, plotConfig).then(() => attachWhiteBGDownloadButton(cpDiv));
      }
    }

    // --- Velocity profile 3D plot ---
    if (Array.isArray(data.Ux) && Array.isArray(data.Uy) && Array.isArray(data.Uz)) {
      const velocityDiv = document.getElementById('velocity-profile-plot');
      if (velocityDiv) {
        const velocityTrace = { x: data.Ux, y: data.Uy, z: data.Uz, type: 'scatter3d', mode: 'markers', name: 'Velocity', marker: {color: plotlyColors.blue, size: 5} };
        Plotly.react(velocityDiv, [velocityTrace], {
          ...plotLayout,
          title: createBoldTitle('Velocity Profile'),
          scene: { xaxis: {title: 'Ux'}, yaxis: {title: 'Uy'}, zaxis: {title: 'Uz'} }
        }, plotConfig);
        attachWhiteBGDownloadButton(velocityDiv);
      }
    }

  } catch (err) {
    console.error('[FOAMFlask] Error updating aero plots:', err);
  }
}

function downloadPlotData(plotId, filename) {
  const plotDiv = document.getElementById(plotId);
  if (!plotDiv || !plotDiv.data) {
    console.error('[FOAMFlask] Plot data not available');
    return;
  }

  // Get all traces from the plot
  const traces = plotDiv.data;
  if (traces.length === 0) {
    console.error('[FOAMFlask] No traces found in the plot');
    return;
  }

  // For velocity plot, handle multiple traces
  traces.forEach((trace, index) => {
    if (!trace.x || !trace.y) return;

    // Create CSV content for this trace
    let csvContent = "x,y\n";
    for (let i = 0; i < trace.x.length; i++) {
      const x = trace.x[i] ?? '';
      const y = trace.y[i] ?? '';
      csvContent += `${x},${y}\n`;
    }

    // Generate filename based on trace name
    const traceName = trace.name?.replace(/\s+/g, '_').toLowerCase() || `trace_${index + 1}`;
    const traceFilename = filename.replace('.csv', `_${traceName}.csv`);

    // Create and trigger download
    try {
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = traceFilename;
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
    } catch (error) {
      console.error(`[FOAMFlask] Error downloading ${traceName} data:`, error);
    }
  });
}

// --- Mesh Visualization Functions ---
async function refreshMeshList() {
  const selectedTutorial = document.getElementById("tutorialSelect").value;
  if (!selectedTutorial) {
    showNotification('Please select a tutorial first', 'warning');
    return;
  }
  
  try {
    showNotification('Searching for mesh files...', 'info', 2000);
    
    const response = await fetch(`/api/available_meshes?tutorial=${encodeURIComponent(selectedTutorial)}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (data.error) {
      showNotification(data.error, 'error');
      return;
    }
    
    availableMeshes = data.meshes || [];
    
    // Update the select dropdown
    const meshSelect = document.getElementById('meshSelect');
    meshSelect.innerHTML = '<option value="">-- Select a mesh file --</option>';
    
    if (availableMeshes.length === 0) {
      showNotification('No mesh files found in this case', 'warning');
      meshSelect.innerHTML += '<option value="" disabled>No mesh files found</option>';
      return;
    }
    
    availableMeshes.forEach(mesh => {
      const option = document.createElement('option');
      option.value = mesh.path;
      option.textContent = `${mesh.name} (${mesh.relative_path})`;
      meshSelect.appendChild(option);
    });
    
    showNotification(`Found ${availableMeshes.length} mesh file(s)`, 'success', 2000);
    
  } catch (error) {
    console.error('[FOAMFlask] Error fetching mesh list:', error);
    showNotification('Failed to fetch mesh list', 'error');
  }
}

async function loadMeshVisualization() {
  const meshSelect = document.getElementById('meshSelect');
  const selectedPath = meshSelect.value;
  
  if (!selectedPath) {
    showNotification('Please select a mesh file', 'warning');
    return;
  }
  
  try {
    showNotification('Loading mesh...', 'info');
    
    // First, load mesh info
    const infoResponse = await fetch('/api/load_mesh', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({file_path: selectedPath})
    });
    
    if (!infoResponse.ok) {
      throw new Error(`HTTP error! status: ${infoResponse.status}`);
    }
    
    const meshInfo = await infoResponse.json();
    
    if (!meshInfo.success) {
      showNotification(meshInfo.error || 'Failed to load mesh', 'error');
      return;
    }
    
    // Display mesh info
    displayMeshInfo(meshInfo);
    
    // Now generate screenshot
    currentMeshPath = selectedPath;
    await updateMeshView();
    
    // Show controls
    document.getElementById('meshControls').classList.remove('hidden');
    
    // showNotification('Mesh loaded successfully', 'success');
    
  } catch (error) {
    console.error('[FOAMFlask] Error loading mesh:', error);
    showNotification('Failed to load mesh', 'error');
  }
}

async function updateMeshView() {
  if (!currentMeshPath) {
    showNotification('No mesh loaded', 'warning');
    return;
  }
  
  try {
    const showEdges = document.getElementById('showEdges').checked;
    const color = document.getElementById('meshColor').value;
    const cameraPosition = document.getElementById('cameraPosition').value;
    
    showNotification('Rendering mesh...', 'info', 2000);
    
    const response = await fetch('/api/mesh_screenshot', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        file_path: currentMeshPath,
        width: 1200,
        height: 800,
        show_edges: showEdges,
        color: color,
        camera_position: cameraPosition || null
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (!data.success) {
      showNotification(data.error || 'Failed to render mesh', 'error');
      return;
    }
    
    // Display the image
    const meshImage = document.getElementById('meshImage');
    const meshPlaceholder = document.getElementById('meshPlaceholder');
    
    meshImage.src = `data:image/png;base64,${data.image}`;
    meshImage.classList.remove('hidden');
    meshPlaceholder.classList.add('hidden');
    
    showNotification('Mesh rendered successfully', 'success', 2000);
    
  } catch (error) {
    console.error('[FOAMFlask] Error rendering mesh:', error);
    showNotification('Failed to render mesh', 'error');
  }
}

function displayMeshInfo(meshInfo) {
  const meshInfoDiv = document.getElementById('meshInfo');
  const meshInfoContent = document.getElementById('meshInfoContent');
  
  if (!meshInfo || !meshInfo.success) {
    meshInfoDiv.classList.add('hidden');
    return;
  }
  
  // Format the mesh information
  const infoItems = [
    { label: 'Points', value: meshInfo.n_points?.toLocaleString() || 'N/A' },
    { label: 'Cells', value: meshInfo.n_cells?.toLocaleString() || 'N/A' },
    { label: 'Length', value: meshInfo.length ? meshInfo.length.toFixed(3) : 'N/A' },
    { label: 'Volume', value: meshInfo.volume ? meshInfo.volume.toFixed(3) : 'N/A' },
  ];
  
  meshInfoContent.innerHTML = infoItems.map(item => 
    `<div><strong>${item.label}:</strong> ${item.value}</div>`
  ).join('');
  
  // Add bounds if available
  if (meshInfo.bounds && Array.isArray(meshInfo.bounds)) {
    const boundsStr = `[${meshInfo.bounds.map(b => b.toFixed(2)).join(', ')}]`;
    meshInfoContent.innerHTML += `<div class="col-span-2"><strong>Bounds:</strong> ${boundsStr}</div>`;
  }
  
  // Add center if available
  if (meshInfo.center && Array.isArray(meshInfo.center)) {
    const centerStr = `(${meshInfo.center.map(c => c.toFixed(2)).join(', ')})`;
    meshInfoContent.innerHTML += `<div class="col-span-2"><strong>Center:</strong> ${centerStr}</div>`;
  }
  
  meshInfoDiv.classList.remove('hidden');
}

async function toggleInteractiveMode() {
  if (!currentMeshPath) {
    showNotification('Please load a mesh first', 'warning');
    return;
  }
  
  const meshImage = document.getElementById('meshImage');
  const meshInteractive = document.getElementById('meshInteractive');
  const meshPlaceholder = document.getElementById('meshPlaceholder');
  const toggleBtn = document.getElementById('toggleInteractiveBtn');
  const cameraControl = document.getElementById('cameraPositionControl');
  const updateBtn = document.getElementById('updateViewBtn');
  
  isInteractiveMode = !isInteractiveMode;
  
  if (isInteractiveMode) {
    // Switch to interactive mode
    showNotification('Loading interactive viewer...', 'info');
    
    try {
      const showEdges = document.getElementById('showEdges').checked;
      const color = document.getElementById('meshColor').value;
      
      // Fetch interactive viewer HTML
      const response = await fetch('/api/mesh_interactive', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          file_path: currentMeshPath,
          show_edges: showEdges,
          color: color
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const html = await response.text();
      
      // Hide static image, show iframe
      meshImage.classList.add('hidden');
      meshPlaceholder.classList.add('hidden');
      meshInteractive.classList.remove('hidden');
      
      // Load HTML into iframe using srcdoc
      meshInteractive.srcdoc = html;
      
      // Update button text
      toggleBtn.textContent = '📷 Static Mode';
      toggleBtn.classList.remove('bg-purple-500', 'hover:bg-purple-600');
      toggleBtn.classList.add('bg-orange-500', 'hover:bg-orange-600');
      
      // Hide camera position control (not needed in interactive mode)
      cameraControl.classList.add('hidden');
      updateBtn.classList.add('hidden');
      
      showNotification('Interactive mode enabled - Use mouse to rotate, zoom, and pan', 'success', 4000);
      
    } catch (error) {
      console.error('[FOAMFlask] Error loading interactive viewer:', error);
      showNotification('Failed to load interactive viewer: ' + error.message, 'error');
      isInteractiveMode = false;
    }
    
  } else {
    // Switch back to static mode
    meshInteractive.classList.add('hidden');
    meshImage.classList.remove('hidden');
    
    // Update button text
    toggleBtn.textContent = '🎮 Interactive Mode';
    toggleBtn.classList.remove('bg-orange-500', 'hover:bg-orange-600');
    toggleBtn.classList.add('bg-purple-500', 'hover:bg-purple-600');
    
    // Show camera position control again
    cameraControl.classList.remove('hidden');
    updateBtn.classList.remove('hidden');
    
    showNotification('Switched to static mode', 'info', 2000);
  }
}

// Set camera view for interactive mode
function setCameraView(view) {
  const iframe = document.getElementById('meshInteractive');
  if (!iframe || !iframe.contentWindow) return;
  
  try {
    // Send message to iframe to set camera view
    iframe.contentWindow.postMessage({
      type: 'setCameraView',
      view: view
    }, '*');
    
    showNotification(`Set view to ${view.toUpperCase()}`, 'info', 1500);
  } catch (error) {
    console.error('Error setting camera view:', error);
  }
}

// Reset camera to default view
function resetCamera() {
  const iframe = document.getElementById('meshInteractive');
  if (!iframe || !iframe.contentWindow) return;
  
  try {
    // Send message to iframe to reset camera
    iframe.contentWindow.postMessage({
      type: 'resetCamera'
    }, '*');
    
    showNotification('Camera view reset', 'info', 1500);
  } catch (error) {
    console.error('Error resetting camera:', error);
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
