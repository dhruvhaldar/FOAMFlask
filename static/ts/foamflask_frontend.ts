/**
 * FOAMFlask Frontend JavaScript
 * 
 * External Dependencies:
 * - isosurface.js: Provides contour generation and visualization functions
 *   Required functions: generateContours, generateContoursWithParams, downloadContourImage, etc.
 */

// FOAMFlask Frontend TypeScript External Dependencies
import { generateContours as generateContoursFn } from './frontend/isosurface';

import * as Plotly from 'plotly.js';

// Types
type MeshFile = {
  path: string;
  name: string;
};

type CameraView = 'front' | 'back' | 'left' | 'right' | 'top' | 'bottom';

// External declarations
declare const generateContours: (options: {
  tutorial: string;
  caseDir: string;
  scalarField: string;
  numIsosurfaces: number;
}) => Promise<void>;

// Utility functions
const getElement = <T extends HTMLElement>(id: string): T | null => {
  return document.getElementById(id) as T | null;
};

const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) return error.message;
  return typeof error === 'string' ? error : 'Unknown error';
};

// Global state
let caseDir: string = '';
let dockerImage: string = '';
let openfoamVersion: string = '';

// Page management
let currentPage: string = 'setup';

// Mesh visualization state
let currentMeshPath: string | null = null;
let availableMeshes: MeshFile[] = [];
let isInteractiveMode: boolean = false;

// Notification management
let notificationId: number = 0;
let lastErrorNotificationTime: number = 0;
const ERROR_NOTIFICATION_COOLDOWN: number = 5 * 60 * 1000; // 5 minutes in milliseconds

// Plotting variables and theme
let plotUpdateInterval: ReturnType<typeof setInterval> | null = null;
let plotsVisible: boolean = true;
let aeroVisible: boolean = false;
let isUpdatingPlots: boolean = false;
let pendingPlotUpdate: boolean = false;
let plotsInViewport: boolean = true;
let isFirstPlotLoad: boolean = true;

// Request management
let abortControllers = new Map<string, AbortController>();
let requestCache = new Map<string, { data: any; timestamp: number }>();
const CACHE_DURATION: number = 1000; // 1 second cache

// Performance optimization
const outputBuffer: { message: string; type: string }[] = [];
let outputFlushTimer: ReturnType<typeof setTimeout> | null = null;

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
  font: { family: 'Computer Modern Serif, serif', size: 12 },
  plot_bgcolor: 'white',
  paper_bgcolor: '#ffffff',
  margin: { l: 50, r: 20, t: 40, pad: 0 },
  height: 400,
  autosize: true,
  showlegend: true,
  legend: { orientation: 'h', y: -0.2, x: 0.1, xanchor: 'left', yanchor: 'middle', bgcolor: 'white', borderwidth: 0.5 },
  xaxis: { showgrid: false, linewidth: 1 },
  yaxis: { showgrid: false, linewidth: 1 },
};

// Plotly config
const plotConfig = {
  responsive: true,
  displayModeBar: true,
  staticPlot: false,
  scrollZoom: true,
  doubleClick: true,
  showTips: true,
  modeBarButtonsToAdd: [],
  modeBarButtonsToRemove: ['autoScale2d', 'zoomIn2d', 'zoomOut2d', 'lasso2d', 'select2d', 'pan2d', 'sendDataToCloud'],
  displaylogo: false,
};

// Helper: Common line style
const lineStyle = { width: 2, opacity: 0.9 };

// Helper: Create bold title
const createBoldTitle = (text: string): string => `<b>${text}</b>`;

// Helper: Download plot as PNG with white background
const downloadPlotAsPNG = (plotDiv: any, filename: string = 'plot.png'): void => {
  if (!plotDiv) return;
  const downloadLayout = { ...plotDiv.layout, font: plotLayout.font, color: 'black', plot_bgcolor: 'white', paper_bgcolor: 'white' };
  Plotly.toImage(plotDiv, { format: 'png', width: plotDiv.offsetWidth, height: plotDiv.offsetHeight, scale: 2, ...downloadLayout })
    .then((dataUrl: string) => {
      const link = document.createElement('a');
      link.href = dataUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    });
};

// Helper: Save current legend visibility
interface PlotTrace {
  x: any;
  y: any;
  type: string;
  mode: string;
  name: string;
  line: { width: number; opacity: number; color: string; dash?: string };
  visible?: boolean | "legendonly";
}

const getLegendVisibility = (
  plotDiv: { data?: PlotTrace[] } | null | undefined
): Record<string, boolean> => {
  if (!plotDiv || !Array.isArray(plotDiv.data)) {
    return {};
  }

  const visibility: Record<string, boolean> = {};

  for (const trace of plotDiv.data) {
    const name = trace.name ?? "";
    if (!name) {
      continue;
    }

    // trace.visible may be boolean | "legendonly" | undefined
    const vis = trace.visible;
    visibility[name] = vis === "legendonly" ? false : vis ?? true;
  }

  return visibility;
};

// Helper: Apply saved legend visibility to new traces
const applyLegendVisibility = (plotDiv: any, visibility: Record<string, boolean>): void => {
  if (!plotDiv || !plotDiv.data || !visibility) return;
  plotDiv.data.forEach((trace: PlotTrace) => {
    if (visibility.hasOwnProperty(trace.name)) {
      trace.visible = visibility[trace.name];
    }
  });
};

// Helper: Attach white-bg download button to a plot
const attachWhiteBGDownloadButton = (plotDiv: any): void => {
  if (!plotDiv || plotDiv.dataset.whiteButtonAdded) return;
  plotDiv.layout.paper_bgcolor = 'white';
  plotDiv.layout.plot_bgcolor = 'white';
  plotDiv.dataset.whiteButtonAdded = 'true';
  const configWithWhiteBG = { ...plotDiv.fullLayout?.config, ...plotConfig };
  configWithWhiteBG.toImageButtonOptions = { format: 'png', filename: `${plotDiv.id}whitebg`, height: plotDiv.clientHeight, width: plotDiv.clientWidth, scale: 2 };
  Plotly.react(plotDiv, plotDiv.data, plotDiv.layout, configWithWhiteBG).then(() => {
    plotDiv.dataset.whiteButtonAdded = 'true';
  });
};

// Page Switching
const switchPage = (pageName: string): void => {
  const pages = ['setup', 'run', 'mesh', 'plots', 'post'];
  pages.forEach(page => {
    const pageElement = document.getElementById(`${page}-page`);
    const navButton = document.getElementById(`nav-${page}`);
    if (pageElement) pageElement.classList.add('hidden');
    if (navButton) {
      navButton.classList.remove('bg-blue-500', 'text-white');
      navButton.classList.add('text-gray-700', 'hover:bg-gray-100');
    }
  });
  const selectedPage = document.getElementById(`${pageName}-page`);
  const selectedNav = document.getElementById(`nav-${pageName}`);
  if (selectedPage) selectedPage.classList.remove('hidden');
  if (selectedNav) {
    selectedNav.classList.add('bg-blue-500', 'text-white');
    selectedNav.classList.remove('text-gray-700', 'hover:bg-gray-100');
  }
  currentPage = pageName;

  switch (pageName) {
    case 'plots':
      const plotsContainer = document.getElementById('plotsContainer');
      if (plotsContainer) {
        plotsContainer.classList.remove('hidden');
        if (!plotsContainer.hasAttribute('data-initialized')) {
          plotsContainer.setAttribute('data-initialized', 'true');
          if (!plotUpdateInterval) startPlotUpdates();
        }
      }
      const aeroBtn = document.getElementById('toggleAeroBtn');
      if (aeroBtn) aeroBtn.classList.toggle('hidden', !aeroVisible);
      break;
    case 'mesh':
      const meshContainer = document.getElementById('page-mesh');
      if (meshContainer && !meshContainer.hasAttribute('data-initialized')) {
        meshContainer.setAttribute('data-initialized', 'true');
        console.log('Mesh page initialized');
        refreshMeshList();
      }
      break;
    case 'post':
      const postContainer = document.getElementById('page-post');
      if (postContainer && !postContainer.hasAttribute('data-initialized')) {
        postContainer.setAttribute('data-initialized', 'true');
        console.log('FOAMFlask Post processing page initialized');
        refreshPostList();
      }
      break;
  }
};

// Notification System
const showNotification = (message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info', duration: number = 5000): number | null => {
  const container = document.getElementById('notificationContainer');
  if (!container) return null;
  const id = ++notificationId;
  const notification = document.createElement('div');
  notification.id = `notification-${id}`;
  notification.className = 'notification pointer-events-auto px-4 py-3 rounded-lg shadow-lg max-w-sm overflow-hidden relative';
  const colors = { success: 'bg-green-500 text-white', error: 'bg-red-500 text-white', warning: 'bg-yellow-500 text-white', info: 'bg-blue-500 text-white' };
  const icons = { success: '✓', error: '✗', warning: '⚠', info: 'ℹ' };
  const content = document.createElement('div');
  content.className = 'relative z-10';
  content.innerHTML = `
    <div class="flex items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <span class="text-2xl font-bold">${icons[type]}</span>
        <span class="text-lg font-medium">${message}</span>
      </div>
    </div>
  `;
  notification.appendChild(content);
  if (duration > 0) {
    const progressBar = document.createElement('div');
    progressBar.className = 'h-1 bg-white bg-opacity-50 absolute bottom-0 left-0';
    progressBar.style.width = '100%';
    progressBar.style.transition = 'width linear';
    progressBar.style.transitionDuration = `${duration}ms`;
    notification.appendChild(progressBar);
    const countdown = document.createElement('div');
    countdown.className = 'flex items-center justify-end gap-2 mt-1';
    countdown.innerHTML = `<span id="countdown-${id}" class="text-xs opacity-75">${(duration / 1000).toFixed(1)}s</span>`;
    content.appendChild(countdown);
    const countdownInterval = setInterval(() => {
      duration -= 100;
      if (duration <= 0) {
        clearInterval(countdownInterval);
        removeNotification(id);
        return;
      }
      const countdownEl = document.getElementById(`countdown-${id}`);
      if (countdownEl) countdownEl.textContent = (duration / 1000).toFixed(1) + 's';
    }, 100);
    notification.dataset.intervalId = countdownInterval.toString();
    setTimeout(() => (progressBar.style.width = '0%'), 10);
  } else {
    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = '×';
    closeBtn.className = 'text-white hover:text-gray-200 font-bold text-lg leading-none';
    closeBtn.onclick = (e) => {
      e.stopPropagation();
      removeNotification(id);
    };
    closeBtn.style.position = 'absolute';
    closeBtn.style.top = '0.5rem';
    closeBtn.style.right = '0.5rem';
    notification.appendChild(closeBtn);
  }
  notification.className += ` ${colors[type]}`;
  container.appendChild(notification);
  return id;
};

const removeNotification = (id: number): void => {
  const notification = document.getElementById(`notification-${id}`);
  if (notification) {
    if (notification.dataset.intervalId) clearInterval(parseInt(notification.dataset.intervalId, 10));
    notification.style.opacity = '0';
    notification.style.transition = 'opacity 0.3s ease';
    setTimeout(() => notification.remove(), 300);
  }
};

// Initialize on page load
window.onload = async () => {
  try {
    const tutorialSelect = document.getElementById('tutorialSelect') as HTMLSelectElement;
    if (tutorialSelect) {
      const savedTutorial = localStorage.getItem('lastSelectedTutorial');
      if (savedTutorial) tutorialSelect.value = savedTutorial;
    }
    const [caseRootData, dockerConfigData] = await Promise.all([
      fetchWithCache('/getcaseroot'),
      fetchWithCache('/getdockerconfig'),
    ]);
    caseDir = caseRootData.caseDir;
    const caseDirInput = document.getElementById('caseDir') as HTMLInputElement;
    if (caseDirInput) caseDirInput.value = caseDir;
    dockerImage = dockerConfigData.dockerImage;
    openfoamVersion = dockerConfigData.openfoamVersion;
    
    const openfoamRootInput = document.getElementById('openfoamRoot') as HTMLInputElement;
    if (openfoamRootInput) openfoamRootInput.value = `${dockerImage} OpenFOAM ${openfoamVersion}`;
  } catch (error) {
    console.error('FOAMFlask Initialization error', error);
    appendOutput('FOAMFlask Failed to initialize application', 'stderr');
  }
};

// Fetch with caching and abort control
const fetchWithCache = async (url: string, options: RequestInit = {}): Promise<any> => {
  const cacheKey = `${url}${JSON.stringify(options)}`;
  const cached = requestCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < CACHE_DURATION) return cached.data;
  if (abortControllers.has(url)) abortControllers.get(url)?.abort();
  const controller = new AbortController();
  abortControllers.set(url, controller);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    requestCache.set(cacheKey, { data, timestamp: Date.now() });
    return data;
  } finally {
    abortControllers.delete(url);
  }
};

// Append output helper with buffering
const appendOutput = (message: string, type: string): void => {
  outputBuffer.push({ message, type });
  if (outputFlushTimer) clearTimeout(outputFlushTimer);
  outputFlushTimer = setTimeout(flushOutputBuffer, 16);
};

const flushOutputBuffer = (): void => {
  if (outputBuffer.length === 0) return;
  const container = document.getElementById('output');
  if (!container) return;
  const fragment = document.createDocumentFragment();
  outputBuffer.forEach(({ message, type }) => {
    const line = document.createElement('div');
    if (type === 'stderr') line.className = 'text-red-600';
    else if (type === 'tutorial') line.className = 'text-blue-600 font-semibold';
    else if (type === 'info') line.className = 'text-yellow-600 italic';
    else line.className = 'text-green-700';
    line.textContent = message;
    fragment.appendChild(line);
  });
  container.appendChild(fragment);
  container.scrollTop = container.scrollHeight;
  outputBuffer.length = 0;
};

// Set case directory manually
const setCase = async (): Promise<void> => {
  try {
    caseDir = (document.getElementById('caseDir') as HTMLInputElement).value;
    const response = await fetch('/setcase', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ caseDir }),
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    caseDir = data.caseDir;
    (document.getElementById('caseDir') as HTMLInputElement).value = caseDir;
    data.output.split('\n').forEach((line: string) => {
      line = line.trim();
      if (line.startsWith('INFO')) appendOutput(line.replace('INFO', ''), 'info');
      else if (line.startsWith('Error')) appendOutput(line, 'stderr');
      else appendOutput(line, 'stdout');
    });
    showNotification('Case directory set', 'info');
  } catch (error) {
    console.error('FOAMFlask Error setting case', error);
    appendOutput(`FOAMFlask Failed to set case directory ${getErrorMessage(error)}`, 'stderr');
    showNotification('Failed to set case directory', 'error');
  }
};

// Update Docker config instead of OpenFOAM root
const setDockerConfig = async (image: string, version: string): Promise<void> => {
  try {
    dockerImage = image;
    openfoamVersion = version;
    const response = await fetch('/setdockerconfig', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dockerImage, openfoamVersion }),
    });
    if (!response.ok) {
  throw new Error(`HTTP error: ${response.status}`);
}

const data: { dockerImage: string; openfoamVersion: string } =
  await response.json();

dockerImage = data.dockerImage;
openfoamVersion = data.openfoamVersion;

const openfoamRootInput = document.getElementById("openfoamRoot");
if (openfoamRootInput instanceof HTMLInputElement) {
  openfoamRootInput.value = `${dockerImage} OpenFOAM ${openfoamVersion}`;
}


    appendOutput(`Docker config set to ${dockerImage} OpenFOAM ${openfoamVersion}`, 'info');
    showNotification('Docker config updated', 'success');
  } catch (error) {
    console.error('FOAMFlask Error setting Docker config', error);
    appendOutput(`FOAMFlask Failed to set Docker config ${getErrorMessage(error)}`, 'stderr');
    showNotification('Failed to set Docker config', 'error');
  }
};

// Load a tutorial
const loadTutorial = async (): Promise<void> => {
  try {
    const tutorialSelect = document.getElementById('tutorialSelect') as HTMLSelectElement;
    const selected = tutorialSelect.value;
    if (selected) localStorage.setItem('lastSelectedTutorial', selected);
    const response = await fetch('/loadtutorial', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tutorial: selected }),
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    data.output.split('\n').forEach((line: string) => {
      line = line.trim();
      if (line.startsWith('INFO:FOAMFlask Tutorial loaded')) {
        appendOutput(line.replace('INFO:FOAMFlask Tutorial loaded', 'FOAMFlask Tutorial loaded'), 'tutorial');
      } else if (line.startsWith('Source')) {
        appendOutput(`FOAMFlask ${line}`, 'info');
      } else if (line.startsWith('Copied to')) {
        appendOutput(`FOAMFlask ${line}`, 'info');
      } else {
        const type = /error/i.test(line) ? 'stderr' : 'stdout';
        appendOutput(line, type);
      }
    });
    showNotification('Tutorial loaded', 'info');
  } catch (error) {
    console.error('FOAMFlask Error loading tutorial', error);
    appendOutput(`FOAMFlask Failed to load tutorial ${getErrorMessage(error)}`, 'stderr');
    showNotification('Failed to load tutorial', 'error');
  }
};

// Run OpenFOAM commands
const runCommand = async (cmd: string): Promise<void> => {
  if (!cmd) {
    appendOutput('FOAMFlask Error: No command specified!', 'stderr');
    showNotification('No command specified', 'error');
    return;
  }
  try {
    const selectedTutorial = (document.getElementById('tutorialSelect') as HTMLSelectElement).value;
    const outputDiv = document.getElementById('output');
    if (outputDiv) outputDiv.innerHTML = '';
    outputBuffer.length = 0;
    showNotification(`Running ${cmd}...`, 'info');
    const response = await fetch('/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ caseDir, tutorial: selectedTutorial, command: cmd }),
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    const read = async (): Promise<void> => {
      const { done, value } = await reader?.read() || { done: true, value: undefined };
      if (done) {
        flushOutputBuffer();
        showNotification(`${cmd} completed`, 'success');
        return;
      }
      const text = decoder.decode(value);
      text.split('\n').forEach((line) => {
        if (!line.trim()) return;
        const type = /error/i.test(line) ? 'stderr' : 'stdout';
        appendOutput(line, type);
      });
      await read();
    };
    await read();
  } catch (error) {
    appendOutput(`FOAMFlask Error reading response ${getErrorMessage(error)}`, 'stderr');
    const errorMsg = cmd.includes('foamToVTK') ? 'Failed to generate VTK files. Make sure the simulation has completed successfully.' : `Error running ${cmd}`;
    showNotification(errorMsg, 'error');
  }
};

// Realtime Plotting Functions
const togglePlots = (): void => {
  plotsVisible = !plotsVisible;
  const container = document.getElementById('plotsContainer');
  const btn = document.getElementById('togglePlotsBtn');
  const aeroBtn = document.getElementById('toggleAeroBtn');
  if (plotsVisible) {
    container?.classList.remove('hidden');
    btn!.textContent = 'Hide Plots';
    aeroBtn?.classList.remove('hidden');
    startPlotUpdates();
    setupIntersectionObserver();
  } else {
    container?.classList.add('hidden');
    btn!.textContent = 'Show Plots';
    aeroBtn?.classList.add('hidden');
    stopPlotUpdates();
  }
};

const setupIntersectionObserver = (): void => {
  const plotsContainer = document.getElementById('plotsContainer');
  if (!plotsContainer || plotsContainer.dataset.observerSetup) return;
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        plotsInViewport = entry.isIntersecting;
      });
    },
    { threshold: 0.1, rootMargin: '50px' }
  );
  observer.observe(plotsContainer);
  plotsContainer.dataset.observerSetup = 'true';
};

const toggleAeroPlots = (): void => {
  aeroVisible = !aeroVisible;
  const container = document.getElementById('aeroContainer');
  const btn = document.getElementById('toggleAeroBtn');
  if (aeroVisible) {
    container?.classList.remove('hidden');
    btn!.textContent = 'Hide Aero Plots';
    updateAeroPlots();
  } else {
    container?.classList.add('hidden');
    btn!.textContent = 'Show Aero Plots';
  }
};

const startPlotUpdates = (): void => {
  if (plotUpdateInterval) return;
  plotUpdateInterval = setInterval(() => {
    if (!plotsInViewport) return;
    if (!isUpdatingPlots) updatePlots();
    else pendingPlotUpdate = true;
  }, 2000);
};

const stopPlotUpdates = (): void => {
  if (plotUpdateInterval) {
    clearInterval(plotUpdateInterval);
    plotUpdateInterval = null;
  }
};

const updatePlots = async (): Promise<void> => {
  const selectedTutorial = (document.getElementById('tutorialSelect') as HTMLSelectElement)?.value;
  if (!selectedTutorial || isUpdatingPlots) return;
  isUpdatingPlots = true;
  try {
    const data = await fetchWithCache(`/api/plotdata?tutorial=${encodeURIComponent(selectedTutorial)}`);
    if (data.error) {
      console.error('FOAMFlask Error fetching plot data', data.error);
      showNotification('Error fetching plot data', 'error');
      return;
    }

    // Pressure plot
if (data.p && data.time) {
  const pressureDiv = getElement<HTMLElement>('pressure-plot');
  if (!pressureDiv) {
    console.error('Pressure plot element not found');
    return;
  }

  const legendVisibility = getLegendVisibility(pressureDiv);

  const pressureTrace: PlotTrace = {
    x: data.time,
    y: data.p,
    type: 'scatter',
    mode: 'lines',
    name: 'Pressure',
    line: { color: plotlyColors.blue, ...lineStyle, width: 2.5 }
  };

  if (Object.prototype.hasOwnProperty.call(legendVisibility, pressureTrace.name)) {
    // Plotly expects boolean | "legendonly"
    pressureTrace.visible = legendVisibility[pressureTrace.name] as boolean | 'legendonly';
  }

  void Plotly.react(
    pressureDiv,
    [pressureTrace],
    {
      ...plotLayout,
      title: createBoldTitle('Pressure vs Time'),
      xaxis: {
        ...plotLayout.xaxis,
        title: 'Time (s)'
      },
      yaxis: {
        ...plotLayout.yaxis,
        title: 'Pressure (Pa)'
      }
    },
    plotConfig
  )
    .then(() => {
      attachWhiteBGDownloadButton(pressureDiv);
    })
    .catch((err: unknown) => {
      console.error('Plotly update failed:', err);
    });
}

// Velocity plot
if (data.Umag && data.time) {
  const velocityDiv = getElement<HTMLElement>('velocity-plot');
  if (!velocityDiv) {
    console.error('Velocity plot element not found');
    return;
  }

  const legendVisibility = getLegendVisibility(velocityDiv);

  const traces: PlotTrace[] = [
    {
      x: data.time,
      y: data.Umag,
      type: 'scatter',
      mode: 'lines',
      name: 'U',
      line: { color: plotlyColors.red, ...lineStyle, width: 2.5 }
    }
  ];

  if (data.Ux) {
    traces.push({
      x: data.time,
      y: data.Ux,
      type: 'scatter',
      mode: 'lines',
      name: 'Ux',
      line: { color: plotlyColors.blue, ...lineStyle, dash: 'dash', width: 2.5 }
    });
  }

  if (data.Uy) {
    traces.push({
      x: data.time,
      y: data.Uy,
      type: 'scatter',
      mode: 'lines',
      name: 'Uy',
      line: { color: plotlyColors.green, ...lineStyle, dash: 'dot', width: 2.5 }
    });
  }

  if (data.Uz) {
    traces.push({
      x: data.time,
      y: data.Uz,
      type: 'scatter',
      mode: 'lines',
      name: 'Uz',
      line: { color: plotlyColors.purple, ...lineStyle, dash: 'dashdot', width: 2.5 }
    });
  }

  // Apply saved visibility safely
  traces.forEach((tr) => {
    if (Object.prototype.hasOwnProperty.call(legendVisibility, tr.name)) {
      tr.visible = legendVisibility[tr.name] as boolean | 'legendonly';
    }
  });

  void Plotly.react(
    velocityDiv,
    traces,
    {
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
    },
    plotConfig
  ).then(() => {
    attachWhiteBGDownloadButton(velocityDiv);
  });
}

    // Turbulence plot
    const turbTraces = [];
    if (data.nut && data.time) turbTraces.push({ x: data.time, y: data.nut, type: 'scatter', mode: 'lines', name: 'nut', line: { color: plotlyColors.teal, ...lineStyle, width: 2.5 } });
    if (data.nuTilda && data.time) turbTraces.push({ x: data.time, y: data.nuTilda, type: 'scatter', mode: 'lines', name: 'nuTilda', line: { color: plotlyColors.cyan, ...lineStyle, width: 2.5 } });
    if (data.k && data.time) turbTraces.push({ x: data.time, y: data.k, type: 'scatter', mode: 'lines', name: 'k', line: { color: plotlyColors.magenta, ...lineStyle, width: 2.5 } });
    if (data.omega && data.time) turbTraces.push({ x: data.time, y: data.omega, type: 'scatter', mode: 'lines', name: 'omega', line: { color: plotlyColors.brown, ...lineStyle, width: 2.5 } });
    if (turbTraces.length > 0) {
      Plotly.react(document.getElementById('turbulence-plot'), turbTraces, { ...plotLayout, title: createBoldTitle('Turbulence Properties vs Time'), xaxis: { ...plotLayout.xaxis, title: 'Time (s)' }, yaxis: { ...plotLayout.yaxis, title: 'Value' } }, plotConfig).then(() => attachWhiteBGDownloadButton(document.getElementById('turbulence-plot')));
    }

    // Update residuals and aero plots in parallel
    const updatePromises = [updateResidualsPlot(selectedTutorial)];
    if (aeroVisible) updatePromises.push(updateAeroPlots());
    await Promise.allSettled(updatePromises);

    // After all plots are updated
    if (isFirstPlotLoad) {
      showNotification('Plots loaded successfully', 'success', 3000);
      isFirstPlotLoad = false;
    }
  } catch (err) {
    console.error('FOAMFlask Error updating plots', err);
    const currentTime = Date.now();
    const selectedTutorial = (document.getElementById('tutorialSelect') as HTMLSelectElement)?.value;
    if (selectedTutorial && currentTime - lastErrorNotificationTime > ERROR_NOTIFICATION_COOLDOWN) {
      showNotification(`Error updating plots: ${err instanceof Error ? err.message : 'Unknown error'}`, 'error');
      lastErrorNotificationTime = currentTime;
    }
  } finally {
    isUpdatingPlots = false;
    if (pendingPlotUpdate) {
      pendingPlotUpdate = false;
      requestAnimationFrame(updatePlots);
    }
  }
};

const updateResidualsPlot = async (tutorial: string): Promise<void> => {
  try {
    const data = await fetchWithCache(`/api/residuals?tutorial=${encodeURIComponent(tutorial)}`);
    if (data.error || !data.time || data.time.length === 0) return;
    const traces = [];
    const fields = ['Ux', 'Uy', 'Uz', 'p'];
    const colors = [plotlyColors.blue, plotlyColors.red, plotlyColors.green, plotlyColors.magenta, plotlyColors.cyan, plotlyColors.orange];
    fields.forEach((field, idx) => {
      if (data[field] && data[field].length > 0) {
        traces.push({
          x: Array.from({ length: data[field].length }, (_, i) => i + 1),
          y: data[field],
          type: 'scatter',
          mode: 'lines',
          name: field,
          line: { color: colors[idx], width: 2.5, shape: 'linear' },
        });
      }
    });
    if (traces.length > 0) {
      const layout = {
        ...plotLayout,
        title: createBoldTitle('Residuals'),
        xaxis: { title: { text: 'Iteration' }, showline: true, mirror: 'all', showgrid: false },
        yaxis: { title: { text: 'Residual' }, type: 'log', showline: true, mirror: 'all', showgrid: true, gridwidth: 1, gridcolor: 'rgba(0,0,0,0.1)' },
      };
      Plotly.react(document.getElementById('residuals-plot'), traces, layout, { ...plotConfig, displayModeBar: true, scrollZoom: false }).then(() => attachWhiteBGDownloadButton(document.getElementById('residuals-plot')));
    }
  } catch (err) {
    console.error('FOAMFlask Error updating residuals', err);
  }
};

const updateAeroPlots = async (): Promise<void> => {
  const selectedTutorial = (document.getElementById('tutorialSelect') as HTMLSelectElement)?.value;
  if (!selectedTutorial) return;
  try {
    const response = await fetch(`/api/latestdata?tutorial=${encodeURIComponent(selectedTutorial)}`);
    const data = await response.json();
    if (data.error) return;

    // Cp plot
    if (Array.isArray(data.p) && Array.isArray(data.time) && data.p.length === data.time.length && data.p.length > 0) {
      const pinf = 101325;
      const rho = 1.225;
      const uinf = Array.isArray(data.Umag) && data.Umag.length ? data.Umag[0] : 1.0;
      const qinf = 0.5 * rho * uinf * uinf;
      const cp = data.p.map((pval: number) => (pval - pinf) / qinf);
      const cpDiv = document.getElementById('cp-plot');
      if (cpDiv) {
        const cpTrace = { x: data.time, y: cp, type: 'scatter', mode: 'lines+markers', name: 'Cp', line: { color: plotlyColors.red, width: 2.5 } };
        Plotly.react(cpDiv, [cpTrace], { ...plotLayout, title: createBoldTitle('Pressure Coefficient'), xaxis: { title: 'Time (s)' }, yaxis: { title: 'Cp' } }, plotConfig).then(() => attachWhiteBGDownloadButton(cpDiv));
      }
    }

    // Velocity profile 3D plot
    if (Array.isArray(data.Ux) && Array.isArray(data.Uy) && Array.isArray(data.Uz)) {
      const velocityDiv = document.getElementById('velocity-profile-plot');
      if (velocityDiv) {
        const velocityTrace = { x: data.Ux, y: data.Uy, z: data.Uz, type: 'scatter3d', mode: 'markers', name: 'Velocity', marker: { color: plotlyColors.blue, size: 5 } };
        Plotly.react(velocityDiv, [velocityTrace], { ...plotLayout, title: createBoldTitle('Velocity Profile'), scene: { xaxis: { title: 'Ux' }, yaxis: { title: 'Uy' }, zaxis: { title: 'Uz' } } }, plotConfig);
        attachWhiteBGDownloadButton(velocityDiv);
      }
    }
  } catch (err) {
    console.error('FOAMFlask Error updating aero plots', err);
  }
};

const downloadPlotData = (plotId: string, filename: string): void => {
  const plotDiv = document.getElementById(plotId);
  if (!plotDiv || !plotDiv.data) {
    console.error('FOAMFlask Plot data not available');
    return;
  }
  const traces = plotDiv.data;
  if (traces.length === 0) {
    console.error('FOAMFlask No traces found in the plot');
    return;
  }
  traces.forEach((trace, index) => {
    if (!trace.x || !trace.y) return;
    let csvContent = 'x,y\n';
    for (let i = 0; i < trace.x.length; i++) {
      const x = trace.x[i] ?? '';
      const y = trace.y[i] ?? '';
      csvContent += `${x},${y}\n`;
    }
    const traceName = (trace.name?.replace(/\s+/g, '').toLowerCase() || `trace${index + 1}`);
    const traceFilename = filename.replace('.csv', `${traceName}.csv`);
    try {
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
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
      console.error(`FOAMFlask Error downloading ${traceName} data`, error);
    }
  });
};

// Mesh Visualization Functions
const refreshMeshList = async (): Promise<void> => {
  try {
    const tutorial = (document.getElementById('tutorialSelect') as HTMLSelectElement)?.value;
    if (!tutorial) {
      showNotification('Please select a tutorial first', 'error');
      return;
    }
    const response = await fetch(`/api/availablemeshes?tutorial=${encodeURIComponent(tutorial)}`);
    if (!response.ok) throw new Error('Failed to fetch mesh files');
    const data = await response.json();
    if (data.error) {
      showNotification(data.error, 'error');
      return;
    }
    availableMeshes = data.meshes;
    const meshSelect = document.getElementById('meshSelect') as HTMLSelectElement;
    const meshActionButtons = document.getElementById('meshActionButtons');
    if (!meshSelect) {
      console.error('meshSelect element not found');
      return;
    }
    meshSelect.innerHTML = '<option value="">-- Select a mesh file --</option>';
    if (availableMeshes.length === 0) {
      showNotification('No mesh files found in this case', 'warning');
      meshSelect.innerHTML = '<option value="" disabled>No mesh files found</option>';
      if (meshActionButtons) {
        meshActionButtons.classList.remove('opacity-50', 'h-0', 'overflow-hidden', 'mb-0');
        meshActionButtons.classList.add('opacity-100', 'h-auto', 'mb-2');
      }
      return;
    }
    availableMeshes.forEach((mesh) => {
      const option = document.createElement('option');
      option.value = mesh.path;
      option.textContent = mesh.name;
      meshSelect.appendChild(option);
    });
    showNotification(`Found ${availableMeshes.length} mesh files`, 'success');
    if (meshActionButtons) {
      meshActionButtons.classList.add('opacity-50', 'h-0', 'overflow-hidden', 'mb-0');
      meshActionButtons.classList.remove('opacity-100', 'h-auto', 'mb-2');
    }
  } catch (error) {
    console.error('Error refreshing mesh list', error);
    showNotification(`Error loading mesh files: ${getErrorMessage(error)}`, 'error');
  }
};

const runFoamToVTK = async (): Promise<void> => {
  const selectedTutorial = (document.getElementById('tutorialSelect') as HTMLSelectElement)?.value;
  if (!selectedTutorial) {
    showNotification('Please select a tutorial first', 'error');
    return;
  }
  const outputDiv = document.getElementById('output');
  if (outputDiv) outputDiv.innerHTML = '';
  outputBuffer.length = 0;
  showNotification('Running foamToVTK...', 'info');
  showNotification('Check <strong>RunLog Console Log</strong> for more details', 'info', 10000);
  try {
    const response = await fetch('/runfoamtovtk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ caseDir, tutorial: selectedTutorial }),
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader?.read() || { done: true, value: undefined };
      if (done) break;
      const text = decoder.decode(value);
      appendOutput(text, 'stdout');
    }
    showNotification('foamToVTK completed', 'success');
  } catch (error) {
    console.error('Error running foamToVTK', error);
    appendOutput(`Error: ${getErrorMessage(error)}`, 'stderr');
    showNotification('Failed to run foamToVTK', 'error');
  }
};

const loadMeshVisualization = async (): Promise<void> => {
  const meshSelect = document.getElementById('meshSelect') as HTMLSelectElement;
  const selectedPath = meshSelect.value;
  if (!selectedPath) {
    showNotification('Please select a mesh file', 'warning');
    return;
  }
  try {
    showNotification('Loading mesh...', 'info');
    const infoResponse = await fetch('/api/loadmesh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filepath: selectedPath }),
    });
    if (!infoResponse.ok) throw new Error(`HTTP error! status: ${infoResponse.status}`);
    const meshInfo = await infoResponse.json();
    if (!meshInfo.success) {
      showNotification(`${meshInfo.error} Failed to load mesh`, 'error');
      return;
    }
    displayMeshInfo(meshInfo);
    currentMeshPath = selectedPath;
    await updateMeshView();
    document.getElementById('meshControls')?.classList.remove('hidden');
    showNotification('Mesh loaded successfully', 'success');
  } catch (error) {
    console.error('FOAMFlask Error loading mesh', error);
    showNotification('Failed to load mesh', 'error');
  }
};

async function updateMeshView(): Promise<void> {
  if (!currentMeshPath) {
    showNotification('No mesh loaded', 'warning');
    return;
  }

  let loadingNotification: number | null = null;

  try {
    const showEdgesInput = document.getElementById('showEdges') as HTMLInputElement | null;
    const colorInput = document.getElementById('meshColor') as HTMLInputElement | null;
    const cameraPositionSelect = document.getElementById('cameraPosition') as HTMLSelectElement | null;

    if (!showEdgesInput || !colorInput || !cameraPositionSelect) {
      showNotification('Required mesh controls not found', 'error');
      return;
    }

    const showEdges = showEdgesInput.checked;
    const color = colorInput.value;
    const cameraPosition = cameraPositionSelect.value;

    // Show persistent loading notification
    loadingNotification = showNotification('Rendering mesh...', 'info', 0);

    const response = await fetch('/api/mesh_screenshot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_path: currentMeshPath,
        width: 1200,
        height: 800,
        show_edges: showEdges,
        color: color,
        camera_position: cameraPosition || null,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to render mesh');
    }

    // Display the image
    const meshImage = document.getElementById('meshImage') as HTMLImageElement | null;
    const meshPlaceholder = document.getElementById('meshPlaceholder');

    if (!meshImage || !meshPlaceholder) {
      showNotification('Mesh image or placeholder element not found', 'error');
      return;
    }

    meshImage.onload = function () {
      // Only remove loading notification after image is fully loaded
      if (loadingNotification !== null) {
        removeNotification(loadingNotification);
      }
      showNotification('Mesh rendered successfully', 'success', 2000);
    };

    meshImage.src = `data:image/png;base64,${data.image}`;
    meshImage.classList.remove('hidden');
    meshPlaceholder.classList.add('hidden');
  } catch (error) {
    console.error('[FOAMFlask] Error rendering mesh:', error);
    if (loadingNotification !== null) {
      removeNotification(loadingNotification);
    }
    showNotification(`Error: ${getErrorMessage(error)}`, 'error', 3000);
  }
}

function displayMeshInfo(meshInfo: {
  success: boolean;
  n_points?: number;
  n_cells?: number;
  length?: number;
  volume?: number;
  bounds?: number[];
  center?: number[];
}): void {
  const meshInfoDiv = document.getElementById('meshInfo');
  const meshInfoContent = document.getElementById('meshInfoContent');

  if (!meshInfoDiv || !meshInfoContent) {
    console.error('Mesh info or content element not found');
    return;
  }

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

  meshInfoContent.innerHTML = infoItems
    .map((item) => `<div><strong>${item.label}:</strong> ${item.value}</div>`)
    .join('');

  // Add bounds if available
  if (meshInfo.bounds && Array.isArray(meshInfo.bounds)) {
    const boundsStr = `[${meshInfo.bounds.map((b) => b.toFixed(2)).join(', ')}]`;
    meshInfoContent.innerHTML += `<div class="col-span-2"><strong>Bounds:</strong> ${boundsStr}</div>`;
  }

  // Add center if available
  if (meshInfo.center && Array.isArray(meshInfo.center)) {
    const centerStr = `(${meshInfo.center.map((c) => c.toFixed(2)).join(', ')})`;
    meshInfoContent.innerHTML += `<div class="col-span-2"><strong>Center:</strong> ${centerStr}</div>`;
  }

  meshInfoDiv.classList.remove('hidden');
}

async function toggleInteractiveMode(): Promise<void> {
  if (!currentMeshPath) {
    showNotification('Please load a mesh first', 'warning');
    return;
  }

  const meshImage = document.getElementById('meshImage') as HTMLImageElement | null;
  const meshInteractive = document.getElementById('meshInteractive') as HTMLIFrameElement | null;
  const meshPlaceholder = document.getElementById('meshPlaceholder');
  const toggleBtn = document.getElementById('toggleInteractiveBtn');
  const cameraControl = document.getElementById('cameraPosition');
  const updateBtn = document.getElementById('updateViewBtn');

  if (!meshImage || !meshInteractive || !meshPlaceholder || !toggleBtn || !cameraControl || !updateBtn) {
    showNotification('Required mesh elements not found', 'error');
    return;
  }

  isInteractiveMode = !isInteractiveMode;

  if (isInteractiveMode) {
    // Switch to interactive mode
    showNotification('Loading interactive viewer...', 'info');

    try {
      const showEdgesInput = document.getElementById('showEdges') as HTMLInputElement | null;
      const colorInput = document.getElementById('meshColor') as HTMLInputElement | null;

      if (!showEdgesInput || !colorInput) {
        showNotification('Required mesh controls not found', 'error');
        isInteractiveMode = false;
        return;
      }

      const showEdges = showEdgesInput.checked;
      const color = colorInput.value;

      // Fetch interactive viewer HTML
      const response = await fetch('/api/mesh_interactive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_path: currentMeshPath,
          show_edges: showEdges,
          color: color,
        }),
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
      toggleBtn.textContent = 'Static Mode';
      toggleBtn.classList.remove('bg-purple-500', 'hover:bg-purple-600');
      toggleBtn.classList.add('bg-orange-500', 'hover:bg-orange-600');

      // Hide camera position control (not needed in interactive mode)
      cameraControl.classList.add('hidden');
      updateBtn.classList.add('hidden');

      showNotification('Interactive mode enabled - Use mouse to rotate, zoom, and pan', 'success', 8000);
    } catch (error) {
      console.error('[FOAMFlask] Error loading interactive viewer:', error);
      const errorMessage = error instanceof Error
        ? error.name === 'AbortError'
          ? 'Loading was cancelled or timed out'
          : error.message
        : 'Failed to load interactive viewer';

      showNotification(`Failed to load interactive viewer: ${errorMessage}`, 'error');

      // Reset to static mode
      isInteractiveMode = false;

      // Safely update UI elements if they exist
      toggleBtn.textContent = 'Interactive Mode';
      toggleBtn.classList.remove('bg-orange-500', 'hover:bg-orange-600');
      toggleBtn.classList.add('bg-purple-500', 'hover:bg-purple-600');
      cameraControl.classList.remove('hidden');
      updateBtn.classList.remove('hidden');
      meshInteractive.classList.add('hidden');
      meshImage.classList.remove('hidden');
    }
  } else {
    // Switch back to static mode
    meshInteractive.classList.add('hidden');
    meshImage.classList.remove('hidden');

    // Update button text
    toggleBtn.textContent = 'Interactive Mode';
    toggleBtn.classList.remove('bg-orange-500', 'hover:bg-orange-600');
    toggleBtn.classList.add('bg-purple-500', 'hover:bg-purple-600');

    // Show camera position control again
    cameraControl.classList.remove('hidden');
    updateBtn.classList.remove('hidden');

    showNotification('Switched to static mode', 'info', 2000);
  }
}

// Set camera view for interactive mode
function setCameraView(view: CameraView): void {
  const iframe = document.getElementById('meshInteractive') as HTMLIFrameElement | null;
  if (!iframe || !iframe.contentWindow) return;

  try {
    // Send message to iframe to set camera view
    iframe.contentWindow.postMessage(
      {
        type: 'setCameraView',
        view: view,
      },
      '*'
    );

    showNotification(`Set view to ${view.toUpperCase()}`, 'info', 1500);
  } catch (error) {
    console.error('Error setting camera view:', error);
  }
}

// Reset camera to default view
function resetCamera(): void {
  const iframe = document.getElementById('meshInteractive') as HTMLIFrameElement | null;
  if (!iframe || !iframe.contentWindow) return;

  try {
    // Send message to iframe to reset camera
    iframe.contentWindow.postMessage(
      {
        type: 'resetCamera',
      },
      '*'
    );

    showNotification('Camera view reset', 'info', 1500);
  } catch (error) {
    console.error('Error resetting camera:', error);
  }
}

// Simple path join function for browser
function joinPath(...parts: string[]): string {
  // Filter out empty parts and join with forward slashes
  return parts.filter(part => part).join('/').replace(/\/+/g, '/');
}


// --- Post Processing Functions ---
async function refreshPostList(): Promise<void> {
  const postContainer = document.getElementById('post-processing-content');
  if (!postContainer) return;

  // Show loading state
  postContainer.innerHTML = '<div class="p-4 text-center text-gray-500">Loading post-processing options...</div>';

  try {
    // Simulate API call with setTimeout for placeholder content
    setTimeout(() => {
      postContainer.innerHTML = `
        <div class="space-y-4">
          <div class="bg-white p-4 rounded-lg shadow">
            <h3 class="font-medium text-gray-900">Available Operations</h3>
            <div class="mt-2 space-y-2">
              <button class="w-full text-left p-2 hover:bg-gray-50 rounded" 
                      onclick="runPostOperation('create_slice')">
                Create Slice
              </button>
              <button class="w-full text-left p-2 hover:bg-gray-50 rounded" 
                      onclick="runPostOperation('generate_streamlines')">
                Generate Streamlines
              </button>
              <button class="w-full text-left p-2 hover:bg-gray-50 rounded" 
                      onclick="runPostOperation('create_contour')">
                Create Contour
              </button>
            </div>
          </div>
          <div id="post-results" class="mt-4"></div>
        </div>
      `;
    }, 500);
  } catch (error) {
    console.error('[FOAMFlask] [refreshPostList] Error loading post-processing options:', error);
    if (postContainer) {
      postContainer.innerHTML = `
        <div class="p-4 text-red-600">
          Failed to load post-processing options. Please try again.
        </div>
      `;
    }
  }
}

// Helper function for post-processing operations
async function runPostOperation(operation: string): Promise<void> {
  const resultsDiv = document.getElementById('post-results') || document.body;

  try {
    if (operation === 'create_contour') {
      // Delegate to the isosurface module's generateContours function
      if (typeof generateContours !== 'function') {
        throw new Error('Isosurface module not loaded. Please check that isosurface.js is included.');
      }

      const tutorialSelect = document.getElementById('tutorialSelect') as HTMLSelectElement | null;
      const tutorial = tutorialSelect ? tutorialSelect.value : null;

      if (!tutorial) {
        showNotification('Please select a tutorial first', 'warning');
        return;
      }

      const caseDirInput = document.getElementById('caseDir') as HTMLInputElement | null;
      const caseDirValue = caseDirInput ? caseDirInput.value : '';

      await generateContours({
        tutorial: tutorial,
        caseDir: caseDirValue,
        scalarField: 'U_Magnitude',
        numIsosurfaces: 10,
      });
    } else {
      resultsDiv.innerHTML = `<div class="p-4 text-blue-600">Running ${operation}...</div>`;
      await new Promise((resolve) => setTimeout(resolve, 1000));
      resultsDiv.innerHTML = `
        <div class="p-4 bg-green-50 text-green-700 rounded">
          ${operation.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())} completed successfully!
        </div>
      `;
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
    resultsDiv.innerHTML = `
      <div class="p-4 bg-red-50 text-red-700 rounded">
        Error running ${operation}: ${errorMessage}
      </div>
    `;
    console.error(`[FOAMFlask] [runPostOperation] Error running ${operation}:`, error);
  }
}

// Refresh VTK file list on Post page
async function refreshPostListVTK(): Promise<void> {
  const tutorialSelect = document.getElementById('tutorialSelect') as HTMLSelectElement | null;
  const tutorial = tutorialSelect?.value;

  if (!tutorial) {
    showNotification('Please select a tutorial first', 'warning');
    return;
  }

  try {
    const response = await fetch(`/api/available_meshes?tutorial=${encodeURIComponent(tutorial)}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

    const data = await response.json();
    const vtkFiles: MeshFile[] = data.meshes || [];

    const vtkSelect = document.getElementById('vtkFileSelect') as HTMLSelectElement | null;
    if (!vtkSelect) {
      console.error('vtkFileSelect element not found');
      return;
    }

    vtkSelect.innerHTML = '<option value="">-- Select a VTK file --</option>';
    vtkFiles.forEach((file) => {
      const option = document.createElement('option');
      option.value = file.path;
      option.textContent = file.name || file.path.split('/').pop();
      vtkSelect.appendChild(option);
    });
  } catch (error) {
    console.error('[FOAMFlask] Error fetching VTK files:', error);
  }
}

// Load selected VTK file
async function loadSelectedVTK(): Promise<void> {
  const vtkSelect = document.getElementById('vtkFileSelect') as HTMLSelectElement | null;
  const selectedFile = vtkSelect?.value;

  if (!selectedFile) {
    showNotification('Please select a VTK file', 'warning');
    return;
  }

  try {
    const response = await fetch('/api/load_mesh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: selectedFile }),
    });

    const meshInfo = await response.json();

    if (meshInfo.success) {
      const scalarFieldSelect = document.getElementById('scalarField') as HTMLSelectElement | null;
      if (!scalarFieldSelect) {
        console.error('scalarField select element not found');
        return;
      }

      scalarFieldSelect.innerHTML = '';
      (meshInfo.point_arrays || []).forEach((field: string) => {
        const option = document.createElement('option');
        option.value = field;
        option.textContent = field;
        scalarFieldSelect.appendChild(option);
      });

      showNotification('VTK file loaded successfully!', 'success');
    }
  } catch (error) {
    console.error('[FOAMFlask] Error loading VTK file:', error);
    showNotification('Error loading VTK file', 'error');
  }
}

// Contour Visualization
async function loadContourVTK(): Promise<void> {
  const vtkSelect = document.getElementById('vtkFileSelect') as HTMLSelectElement | null;
  const selectedFile = vtkSelect?.value;

  if (!selectedFile) {
    showNotification('Please select a VTK file', 'warning');
    return;
  }

  try {
    showNotification('Loading VTK file for contour generation...', 'info');
    console.log('[FOAMFlask] Loading VTK file for contour:', selectedFile);

    const response = await fetch('/api/load_mesh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_path: selectedFile,
        for_contour: true,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }

    const meshInfo = await response.json();
    console.log('[FOAMFlask] Received mesh info:', meshInfo);

    if (!meshInfo.success) {
      throw new Error(meshInfo.error || 'Failed to load mesh');
    }

    const scalarFieldSelect = document.getElementById('scalarField') as HTMLSelectElement | null;
    if (!scalarFieldSelect) {
      throw new Error('Could not find scalar field select element');
    }

    const pointArrays: string[] = meshInfo.point_arrays || [];
    const cellArrays: string[] = meshInfo.cell_arrays || [];

    scalarFieldSelect.innerHTML = '';

    pointArrays.forEach((field: string) => {
      const option = document.createElement('option');
      option.value = `${field}@point`;
      option.textContent = `🔵 ${field} (Point Data)`;
      option.className = 'point-data-option';
      option.dataset.fieldType = 'point';
      scalarFieldSelect.appendChild(option);
    });

    cellArrays.forEach((field: string) => {
      const option = document.createElement('option');
      option.value = `${field}@cell`;
      option.textContent = `🟢 ${field} (Cell Data)`;
      option.className = 'cell-data-option';
      option.dataset.fieldType = 'cell';
      scalarFieldSelect.appendChild(option);
    });

    if (scalarFieldSelect.options.length === 0) {
      console.warn('[FOAMFlask] No data arrays found in mesh');
      showNotification('No scalar fields found in the mesh', 'warning');
    }

    const generateBtn = document.getElementById('generateContoursBtn');
    if (generateBtn) {
      generateBtn.disabled = false;
    } else {
      console.warn('[FOAMFlask] Could not find generateContoursBtn');
    }

    showNotification('VTK file loaded for contour generation!', 'success');
    console.log('[FOAMFlask] Successfully loaded mesh for contour generation');
  } catch (error) {
    console.error('[FOAMFlask] Error loading VTK file for contour:', error);
    showNotification(`Error: ${error instanceof Error ? error.message : 'Failed to load VTK file for contour generation'}`, 'error');
  }
}

// Handle custom VTK file upload
async function loadCustomVTKFile(): Promise<void> {
  const fileInput = document.getElementById('vtkFileBrowser') as HTMLInputElement | null;
  const file = fileInput?.files?.[0];

  if (!file) {
    showNotification('Please select a file first', 'warning');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  try {
    showNotification('Uploading and processing VTK file...', 'info');

    const response = await fetch('/api/upload_vtk', {
      method: 'POST',
      body: formData,
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || 'Failed to upload file');
    }

    const fileInfo = document.getElementById('vtkFileInfo');
    const fileInfoContent = document.getElementById('vtkFileInfoContent');

    if (fileInfo && fileInfoContent) {
      fileInfoContent.innerHTML = `
        <div><strong>File:</strong> ${file.name}</div>
        <div><strong>Type:</strong> ${file.type || 'VTK'}</div>
        <div><strong>Size:</strong> ${(file.size / 1024).toFixed(2)} KB</div>
        ${result.mesh_info ? `
        <div><strong>Points:</strong> ${(result.mesh_info.n_points || 0).toLocaleString()}</div>
        <div><strong>Cells:</strong> ${(result.mesh_info.n_cells || 0).toLocaleString()}</div>
        ` : ''}
      `;
      fileInfo.classList.remove('hidden');
    }

    const scalarFieldSelect = document.getElementById('scalarField') as HTMLSelectElement | null;
    if (scalarFieldSelect && result.mesh_info) {
      scalarFieldSelect.innerHTML = '';

      (result.mesh_info.point_arrays || []).forEach((field: string) => {
        const option = document.createElement('option');
        option.value = `${field}@point`;
        option.textContent = `🔵 ${field} (Point Data)`;
        option.className = 'point-data-option';
        scalarFieldSelect.appendChild(option);
      });

      (result.mesh_info.cell_arrays || []).forEach((field: string) => {
        const option = document.createElement('option');
        option.value = `${field}@cell`;
        option.textContent = `🟢 ${field} (Cell Data)`;
        option.className = 'cell-data-option';
        scalarFieldSelect.appendChild(option);
      });

      const generateBtn = document.getElementById('generateContoursBtn');
      if (generateBtn) {
        generateBtn.disabled = false;
      }
    }

    showNotification('VTK file loaded successfully!', 'success');
  } catch (error) {
    console.error('Error loading VTK file:', error);
    showNotification(`Error: ${error instanceof Error ? error.message : 'Failed to load VTK file'}`, 'error');
  }
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
  stopPlotUpdates();

  abortControllers.forEach((controller) => controller.abort());
  abortControllers.clear();

  requestCache.clear();

  flushOutputBuffer();
});
