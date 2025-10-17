let caseDir = "";        // will be fetched from server on load
let dockerImage = "";    // from server
let openfoamVersion = ""; // from server

// Plotting variables
let plotUpdateInterval = null;
let plotsVisible = false;
let aeroVisible = false;

// --- Initialize on page load ---
window.onload = () => {
  // Fetch CASE_ROOT
  fetch("/get_case_root")
    .then(r => r.json())
    .then(data => {
      caseDir = data.caseDir || "";
      document.getElementById("caseDir").value = caseDir;
    });

  // Fetch Docker config (instead of OPENFOAM_ROOT)
  fetch("/get_docker_config")
    .then(r => r.json())
    .then(data => {
      dockerImage = data.dockerImage || "";
      openfoamVersion = data.openfoamVersion || "";
      document.getElementById("openfoamRoot").value =
        `${dockerImage} (OpenFOAM ${openfoamVersion})`;
    });
};

// --- Append output helper ---
function appendOutput(message, type="stdout") {
  const container = document.getElementById("output");
  const line = document.createElement("div");

  if(type === "stderr") line.className = "text-red-600";
  else if(type === "tutorial") line.className = "text-blue-600 font-semibold";
  else if(type === "info") line.className = "text-yellow-600 italic";
  else line.className = "text-green-700";

  line.textContent = message;
  container.appendChild(line);
  container.scrollTop = container.scrollHeight;
}

// --- Set case directory manually ---
function setCase() {
  caseDir = document.getElementById("caseDir").value;
  fetch("/set_case", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({caseDir: caseDir})
  })
  .then(r => r.json())
  .then(data => {
    caseDir = data.caseDir;
    document.getElementById("caseDir").value = caseDir;

    data.output.split('\n').forEach(line => {
      line = line.trim();
      if(line.startsWith("INFO::")) appendOutput(line.replace("INFO::",""), "info");
      else if(line.startsWith("[Error]")) appendOutput(line, "stderr");
      else appendOutput(line, "stdout");
    });
  });
}

// --- Update Docker config (instead of OpenFOAM root) ---
function setDockerConfig(image, version) {
  dockerImage = image;
  openfoamVersion = version;
  fetch("/set_docker_config", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      dockerImage: dockerImage,
      openfoamVersion: openfoamVersion
    })
  })
  .then(r => r.json())
  .then(data => {
    dockerImage = data.dockerImage;
    openfoamVersion = data.openfoamVersion;
    document.getElementById("openfoamRoot").value =
      `${dockerImage} (OpenFOAM ${openfoamVersion})`;

    appendOutput(`Docker config set to: ${dockerImage} (OpenFOAM ${openfoamVersion})`, "info");
  });
}

// --- Load a tutorial ---
function loadTutorial() {
  const selected = document.getElementById("tutorialSelect").value;
  fetch("/load_tutorial", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({tutorial: selected})
  })
  .then(r => r.json())
  .then(data => {
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
  });
}

// --- Run OpenFOAM commands ---
function runCommand(cmd) {
  if (!cmd) {
    appendOutput("Error: No command specified!", "stderr");
    return;
  }
  const selectedTutorial = document.getElementById("tutorialSelect").value;
  const outputDiv = document.getElementById("output");
  outputDiv.innerHTML = ""; // clear previous output

  fetch("/run", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      caseDir: caseDir,
      tutorial: selectedTutorial,
      command: cmd
    })
  }).then(response => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    function read() {
      reader.read().then(({done, value}) => {
        if (done) return;
        const text = decoder.decode(value);
        text.split("\n").forEach(line => {
          if (!line.trim()) return;
          const type = /error/i.test(line) ? "stderr" : "stdout";
          appendOutput(line, type);
        });
        read();
      });
    }
    read();
  });
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
  } else {
    container.classList.add('hidden');
    btn.textContent = 'Show Plots';
    aeroBtn.classList.add('hidden');
    stopPlotUpdates();
  }
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
  plotUpdateInterval = setInterval(updatePlots, 2000); // Update every 2 seconds
}

function stopPlotUpdates() {
  if (plotUpdateInterval) {
    clearInterval(plotUpdateInterval);
    plotUpdateInterval = null;
  }
}

function updatePlots() {
  const selectedTutorial = document.getElementById("tutorialSelect").value;
  if (!selectedTutorial) {
    return;
  }
  
  fetch(`/api/plot_data?tutorial=${encodeURIComponent(selectedTutorial)}`)
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        console.error('Error fetching plot data:', data.error);
        return;
      }
      
      // Update pressure plot
      if (data.p && data.time) {
        const pressureTrace = {
          x: data.time,
          y: data.p,
          type: 'scatter',
          mode: 'lines',
          name: 'Pressure',
          line: {color: 'blue', width: 2}
        };
        const layout = {
          title: 'Pressure vs Time',
          xaxis: {title: 'Time (s)'},
          yaxis: {title: 'Pressure (Pa)'},
          height: 400,
          margin: {t: 40, r: 20, b: 60, l: 80},
          autosize: true
        };
        Plotly.react('pressure-plot', [pressureTrace], layout);
      }
      
      // Update velocity plot
      if (data.U_mag && data.time) {
        const traces = [
          {
            x: data.time,
            y: data.U_mag,
            type: 'scatter',
            mode: 'lines',
            name: '|U|',
            line: {color: 'red', width: 2}
          }
        ];
        
        if (data.Ux) {
          traces.push({
            x: data.time,
            y: data.Ux,
            type: 'scatter',
            mode: 'lines',
            name: 'Ux',
            line: {color: 'orange', width: 1}
          });
        }
        if (data.Uy) {
          traces.push({
            x: data.time,
            y: data.Uy,
            type: 'scatter',
            mode: 'lines',
            name: 'Uy',
            line: {color: 'green', width: 1}
          });
        }
        if (data.Uz) {
          traces.push({
            x: data.time,
            y: data.Uz,
            type: 'scatter',
            mode: 'lines',
            name: 'Uz',
            line: {color: 'purple', width: 1}
          });
        }
        
        const layout = {
          title: 'Velocity vs Time',
          xaxis: {title: 'Time (s)'},
          yaxis: {title: 'Velocity (m/s)'},
          height: 400,
          margin: {t: 40, r: 20, b: 60, l: 80},
          autosize: true,
          showlegend: true
        };
        Plotly.react('velocity-plot', traces, layout);
      }
      
      // Update turbulence plot
      const turbTraces = [];
      if (data.nut && data.time) {
        turbTraces.push({
          x: data.time,
          y: data.nut,
          type: 'scatter',
          mode: 'lines',
          name: 'nut',
          line: {color: 'teal', width: 2}
        });
      }
      if (data.nuTilda && data.time) {
        turbTraces.push({
          x: data.time,
          y: data.nuTilda,
          type: 'scatter',
          mode: 'lines',
          name: 'nuTilda',
          line: {color: 'cyan', width: 2}
        });
      }
      if (data.k && data.time) {
        turbTraces.push({
          x: data.time,
          y: data.k,
          type: 'scatter',
          mode: 'lines',
          name: 'k',
          line: {color: 'magenta', width: 2}
        });
      }
      if (data.omega && data.time) {
        turbTraces.push({
          x: data.time,
          y: data.omega,
          type: 'scatter',
          mode: 'lines',
          name: 'omega',
          line: {color: 'brown', width: 2}
        });
      }
      
      if (turbTraces.length > 0) {
        const layout = {
          title: 'Turbulence Properties vs Time',
          xaxis: {title: 'Time (s)'},
          yaxis: {title: 'Value'},
          height: 400,
          margin: {t: 40, r: 20, b: 60, l: 80},
          autosize: true,
          showlegend: true
        };
        Plotly.react('turbulence-plot', turbTraces, layout);
      }
      
      // Update residuals plot
      updateResidualsPlot(selectedTutorial);
      
      // Update aero plots if visible
      if (aeroVisible) {
        updateAeroPlots();
      }
    })
    .catch(err => console.error('Error updating plots:', err));
}

function updateResidualsPlot(tutorial) {
  fetch(`/api/residuals?tutorial=${encodeURIComponent(tutorial)}`)
    .then(r => r.json())
    .then(data => {
      if (data.error || !data.time || data.time.length === 0) {
        return;
      }
      
      const traces = [];
      const fields = ['Ux', 'Uy', 'Uz', 'p', 'k', 'epsilon', 'omega'];
      const colors = ['red', 'green', 'blue', 'orange', 'purple', 'brown', 'pink'];
      
      fields.forEach((field, idx) => {
        if (data[field] && data[field].length > 0) {
          traces.push({
            x: data.time.slice(0, data[field].length),
            y: data[field],
            type: 'scatter',
            mode: 'lines',
            name: field,
            line: {color: colors[idx], width: 2}
          });
        }
      });
      
      if (traces.length > 0) {
        const layout = {
          title: 'Residuals vs Time',
          xaxis: {title: 'Time (s)'},
          yaxis: {title: 'Residual', type: 'log'},
          height: 400,
          margin: {t: 40, r: 20, b: 60, l: 80},
          autosize: true,
          showlegend: true
        };
        Plotly.react('residuals-plot', traces, layout);
      }
    })
    .catch(err => console.error('Error updating residuals:', err));
}

function updateAeroPlots() {
  const selectedTutorial = document.getElementById("tutorialSelect").value;
  if (!selectedTutorial) {
    return;
  }
  
  // Fetch latest data for aerodynamic calculations
  fetch(`/api/latest_data?tutorial=${encodeURIComponent(selectedTutorial)}`)
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        console.error('Error fetching aero data:', data.error);
        return;
      }
      
      // Calculate and plot pressure coefficient
      if (data.p) {
        const p_inf = 101325; // Standard atmospheric pressure
        const rho = 1.225; // Air density at sea level
        const u_inf = data.U_mag || 1.0;
        const q_inf = 0.5 * rho * u_inf * u_inf;
        const cp = (data.p - p_inf) / q_inf;
        
        const cpTrace = {
          x: [data.time],
          y: [cp],
          type: 'scatter',
          mode: 'markers',
          name: 'Cp',
          marker: {color: 'red', size: 10}
        };
        
        const layout = {
          title: 'Pressure Coefficient',
          xaxis: {title: 'Time (s)'},
          yaxis: {title: 'Cp'},
          height: 400,
          margin: {t: 40, r: 20, b: 60, l: 80},
          autosize: true,
          showlegend: true
        };
        Plotly.react('cp-plot', [cpTrace], layout);
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
          marker: {color: 'blue', size: 5}
        };
        
        const layout = {
          title: 'Velocity Profile',
          scene: {
            xaxis: {title: 'Ux (m/s)'},
            yaxis: {title: 'Uy (m/s)'},
            zaxis: {title: 'Uz (m/s)'}
          },
          height: 400,
          margin: {t: 40, r: 20, b: 60, l: 80},
          autosize: true,
          showlegend: true
        };
        Plotly.react('velocity-profile-plot', [velocityTrace], layout);
      }
    })
    .catch(err => console.error('Error updating aero plots:', err));
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
  stopPlotUpdates();
});
