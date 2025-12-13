/**
 * FOAMFlask Frontend JavaScript
 *
 * External Dependencies:
 * - isosurface.js: Provides contour generation and visualization functions
 *   Required functions: generateContours, generateContoursWithParams, downloadContourImage, etc.
 *  Plotly: Loaded via CDN in HTML, available as global object
 */
// Plotly is loaded globally via CDN in the HTML file
// Utility functions
// FOAMFlask Frontend TypeScript External Dependencies
import { generateContours as generateContoursFn } from "./frontend/isosurface.js";
// Utility functions
const getElement = (id) => {
    return document.getElementById(id);
};
const getErrorMessage = (error) => {
    if (error instanceof Error)
        return error.message;
    return typeof error === "string" ? error : "Unknown error";
};
// Storage for Console Log
const CONSOLE_LOG_KEY = "foamflask_console_log";
// Global state
let caseDir = "";
let dockerImage = "";
let openfoamVersion = "";
// Page management
let currentPage = "setup";
// Mesh visualization state
let currentMeshPath = null;
let availableMeshes = [];
let isInteractiveMode = false;
// Notification management
let notificationId = 0;
let lastErrorNotificationTime = 0;
const ERROR_NOTIFICATION_COOLDOWN = 5 * 60 * 1000; // 5 minutes in milliseconds
// Plotting variables and theme
let plotUpdateInterval = null;
let plotsVisible = true;
let aeroVisible = false;
let isUpdatingPlots = false;
let pendingPlotUpdate = false;
let plotsInViewport = true;
let isFirstPlotLoad = true;
// Request management
let abortControllers = new Map();
let requestCache = new Map();
const CACHE_DURATION = 1000; // 1 second cache
// Performance optimization
const outputBuffer = [];
let outputFlushTimer = null;
let saveLogTimer = null;
// Save log to local storage (Debounced)
const saveLogToStorage = () => {
    const container = document.getElementById("output");
    if (!container)
        return;
    try {
        localStorage.setItem(CONSOLE_LOG_KEY, container.innerHTML);
    }
    catch (e) {
        console.warn("Failed to save console log to local storage (likely quota exceeded).");
    }
};
const saveLogDebounced = () => {
    if (saveLogTimer)
        clearTimeout(saveLogTimer);
    saveLogTimer = setTimeout(saveLogToStorage, 2000);
};
// Custom color palette
const plotlyColors = {
    blue: "#1f77b4",
    orange: "#ff7f0e",
    green: "#2ca02c",
    red: "#d62728",
    purple: "#9467bd",
    brown: "#8c564b",
    pink: "#e377c2",
    gray: "#7f7f7f",
    yellow: "#bcbd22",
    teal: "#17becf",
    cyan: "#17becf",
    magenta: "#e377c2",
};
// Common plot layout
const plotLayout = {
    font: { family: "Computer Modern Serif, serif", size: 12 },
    plot_bgcolor: "white",
    paper_bgcolor: "#ffffff",
    margin: { l: 50, r: 20, t: 60, b: 80, pad: 0 },
    height: 400,
    autosize: true,
    showlegend: true,
    legend: {
        orientation: "h",
        y: -0.3,
        x: 0.5,
        xanchor: "center",
        yanchor: "top",
        bgcolor: "white",
        borderwidth: 0.5,
    },
    xaxis: { showgrid: false, linewidth: 1 },
    yaxis: { showgrid: false, linewidth: 1 },
};
// Plotly config
const plotConfig = {
    responsive: true,
    displayModeBar: true,
    staticPlot: false,
    scrollZoom: true,
    doubleClick: "reset+autosize",
    showTips: true,
    modeBarButtonsToAdd: [],
    modeBarButtonsToRemove: [
        "autoScale2d",
        "zoomIn2d",
        "zoomOut2d",
        "lasso2d",
        "select2d",
        "pan2d",
        "sendDataToCloud",
    ],
    displaylogo: false,
};
// Helper: Common line style
const lineStyle = { width: 2, opacity: 0.9 };
// Helper: Create bold title
const createBoldTitle = (text) => ({
    text: `<b>${text}</b>`,
    font: {
        ...plotLayout.font,
        size: 22,
    },
});
// Helper: Download plot as PNG
const downloadPlotAsPNG = (plotIdOrDiv, filename = "plot.png") => {
    // Handle both string ID (from HTML) or direct element
    const plotDiv = typeof plotIdOrDiv === "string"
        ? document.getElementById(plotIdOrDiv)
        : plotIdOrDiv;
    if (!plotDiv) {
        console.error(`Plot element not found: ${plotIdOrDiv}`);
        return;
    }
    // Plotly.toImage options (layout overrides are not supported here directly)
    Plotly.toImage(plotDiv, {
        format: "png",
        width: plotDiv.offsetWidth,
        height: plotDiv.offsetHeight,
        scale: 2, // Higher resolution
    }).then((dataUrl) => {
        const link = document.createElement("a");
        link.href = dataUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }).catch((err) => {
        console.error("Error downloading plot:", err);
    });
};
const getLegendVisibility = (plotDiv) => {
    try {
        const plotData = plotDiv.data;
        if (!Array.isArray(plotData)) {
            return {};
        }
        const visibility = {};
        for (const trace of plotData) {
            const name = trace.name ?? "";
            if (!name) {
                continue;
            }
            // trace.visible may be boolean | "legendonly" | undefined
            const vis = trace.visible;
            // Preserve "legendonly" state instead of converting it to false
            visibility[name] = vis === "legendonly" ? "legendonly" : (vis ?? true);
        }
        return visibility;
    }
    catch (error) {
        console.warn("Error getting legend visibility:", error);
        return {};
    }
};
// Helper: Apply saved legend visibility to new traces
const applyLegendVisibility = (plotDiv, visibility) => {
    if (!plotDiv || !plotDiv.data || !visibility)
        return;
    plotDiv.data.forEach((trace) => {
        if (trace.name && visibility.hasOwnProperty(trace.name)) {
            trace.visible = visibility[trace.name];
        }
    });
};
// Helper: Attach white-bg download button to a plot
const attachWhiteBGDownloadButton = (plotDiv) => {
    if (!plotDiv || plotDiv.dataset.whiteButtonAdded)
        return;
    plotDiv.layout.paper_bgcolor = "white";
    plotDiv.layout.plot_bgcolor = "white";
    plotDiv.dataset.whiteButtonAdded = "true";
    const configWithWhiteBG = { ...plotDiv.fullLayout?.config, ...plotConfig };
    configWithWhiteBG.toImageButtonOptions = {
        format: "png",
        filename: `${plotDiv.id}whitebg`,
        height: plotDiv.clientHeight,
        width: plotDiv.clientWidth,
        scale: 2,
    };
    void Plotly.react(plotDiv, plotDiv.data, plotDiv.layout, configWithWhiteBG)
        .then(() => {
        plotDiv.dataset.whiteButtonAdded = "true";
    })
        .catch((err) => {
        console.error("Plotly update failed:", err);
    });
};
// Page Switching
const switchPage = (pageName) => {
    console.log(`switchPage called with: ${pageName}`);
    const pages = ["setup", "run", "mesh", "plots", "post"];
    pages.forEach((page) => {
        const pageElement = document.getElementById(`page-${page}`);
        const navButton = document.getElementById(`nav-${page}`);
        if (pageElement)
            pageElement.classList.add("hidden");
        if (navButton) {
            navButton.classList.remove("bg-blue-500", "text-white");
            navButton.classList.add("text-gray-700", "hover:bg-gray-100");
        }
    });
    const selectedPage = document.getElementById(`page-${pageName}`);
    const selectedNav = document.getElementById(`nav-${pageName}`);
    if (selectedPage)
        selectedPage.classList.remove("hidden");
    if (selectedNav) {
        selectedNav.classList.remove("text-gray-700", "hover:bg-gray-100");
        selectedNav.classList.add("bg-blue-500", "text-white");
    }
    switch (pageName) {
        case "plots":
            const plotsContainer = document.getElementById("plotsContainer");
            if (plotsContainer) {
                plotsContainer.classList.remove("hidden");
                // FIX: Show loading on first load
                if (isFirstPlotLoad) {
                    const loader = document.getElementById("plotsLoading");
                    if (loader)
                        loader.classList.remove("hidden");
                }
                if (!plotsContainer.hasAttribute("data-initialized")) {
                    plotsContainer.setAttribute("data-initialized", "true");
                    if (!plotUpdateInterval)
                        startPlotUpdates();
                }
            }
            const aeroBtn = document.getElementById("toggleAeroBtn");
            if (aeroBtn)
                aeroBtn.classList.remove("hidden");
            break;
        case "mesh":
            const meshContainer = document.getElementById("page-mesh");
            if (meshContainer && !meshContainer.hasAttribute("data-initialized")) {
                meshContainer.setAttribute("data-initialized", "true");
                console.log("Mesh page initialized");
                refreshMeshList();
            }
            break;
        case "post":
            const postContainer = document.getElementById("page-post");
            if (postContainer && !postContainer.hasAttribute("data-initialized")) {
                postContainer.setAttribute("data-initialized", "true");
                console.log("Post page initialized");
                refreshPostList();
            }
            break;
        default:
            console.log(`Unknown page: ${pageName}`);
            break;
    }
};
// Show notification
const showNotification = (message, type, duration = 5000) => {
    const container = document.getElementById("notificationContainer");
    if (!container)
        return null;
    const id = ++notificationId;
    const notification = document.createElement("div");
    notification.id = `notification-${id}`;
    notification.className =
        "notification pointer-events-auto px-4 py-3 rounded-lg shadow-lg max-w-sm overflow-hidden relative";
    const colors = {
        success: "bg-green-500 text-white",
        error: "bg-red-500 text-white",
        warning: "bg-yellow-500 text-white",
        info: "bg-blue-500 text-white",
    };
    const icons = { success: "✓", error: "✗", warning: "⚠", info: "ℹ" };
    const content = document.createElement("div");
    content.className = "relative z-10";
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
        const progressBar = document.createElement("div");
        progressBar.className =
            "h-1 bg-white bg-opacity-50 absolute bottom-0 left-0";
        progressBar.style.width = "100%";
        progressBar.style.transition = "width linear";
        progressBar.style.transitionDuration = `${duration}ms`;
        notification.appendChild(progressBar);
        const countdown = document.createElement("div");
        countdown.className = "flex items-center justify-end gap-2 mt-1";
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
            if (countdownEl)
                countdownEl.textContent = (duration / 1000).toFixed(1) + "s";
        }, 100);
        notification.dataset.intervalId = countdownInterval.toString();
        setTimeout(() => (progressBar.style.width = "0%"), 10);
    }
    else {
        const closeBtn = document.createElement("button");
        closeBtn.innerHTML = "×";
        closeBtn.className =
            "text-white hover:text-gray-200 font-bold text-lg leading-none";
        closeBtn.onclick = (e) => {
            e.stopPropagation();
            removeNotification(id);
        };
        closeBtn.style.position = "absolute";
        closeBtn.style.top = "0.5rem";
        closeBtn.style.right = "0.5rem";
        notification.appendChild(closeBtn);
    }
    notification.className += ` ${colors[type]}`;
    container.appendChild(notification);
    return id;
};
const removeNotification = (id) => {
    const notification = document.getElementById(`notification-${id}`);
    if (notification) {
        if (notification.dataset.intervalId)
            clearInterval(parseInt(notification.dataset.intervalId, 10));
        notification.style.opacity = "0";
        notification.style.transition = "opacity 0.3s ease";
        setTimeout(() => notification.remove(), 300);
    }
};
// Initialize on page load
window.onload = async () => {
    // Check startup status first
    try {
        await checkStartupStatus();
    }
    catch (error) {
        console.error("Startup check failed", error);
    }
    try {
        const tutorialSelect = document.getElementById("tutorialSelect");
        if (tutorialSelect) {
            const savedTutorial = localStorage.getItem("lastSelectedTutorial");
            if (savedTutorial)
                tutorialSelect.value = savedTutorial;
        }
        // Explicitly typed responses
        const caseRootData = await fetchWithCache("/get_case_root");
        const dockerConfigData = await fetchWithCache("/get_docker_config");
        caseDir = caseRootData.caseDir;
        const caseDirInput = document.getElementById("caseDir");
        if (caseDirInput)
            caseDirInput.value = caseDir;
        dockerImage = dockerConfigData.dockerImage;
        openfoamVersion = dockerConfigData.openfoamVersion;
        const openfoamRootInput = document.getElementById("openfoamRoot");
        if (openfoamRootInput)
            openfoamRootInput.value = `${dockerImage} OpenFOAM ${openfoamVersion}`;
        // Restore Console Log from LocalStorage
        const outputDiv = document.getElementById("output");
        const savedLog = localStorage.getItem(CONSOLE_LOG_KEY);
        if (outputDiv && savedLog) {
            outputDiv.innerHTML = savedLog;
            outputDiv.scrollTop = outputDiv.scrollHeight;
        }
    }
    catch (error) {
        console.error("FOAMFlask Initialization error", error);
        appendOutput("FOAMFlask Failed to initialize application", "stderr");
    }
};
// Fetch with caching and abort control
const fetchWithCache = async (url, options = {}) => {
    const cacheKey = `${url}${JSON.stringify(options)}`;
    const cached = requestCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION)
        return cached.data;
    if (abortControllers.has(url))
        abortControllers.get(url)?.abort();
    const controller = new AbortController();
    abortControllers.set(url, controller);
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal,
        });
        if (!response.ok)
            throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        requestCache.set(cacheKey, { data, timestamp: Date.now() });
        return data;
    }
    finally {
        abortControllers.delete(url);
    }
};
// Append output helper with buffering
const appendOutput = (message, type) => {
    outputBuffer.push({ message, type });
    if (outputFlushTimer)
        clearTimeout(outputFlushTimer);
    outputFlushTimer = setTimeout(flushOutputBuffer, 16);
};
const flushOutputBuffer = () => {
    if (outputBuffer.length === 0)
        return;
    const container = document.getElementById("output");
    if (!container)
        return;
    const fragment = document.createDocumentFragment();
    outputBuffer.forEach(({ message, type }) => {
        const line = document.createElement("div");
        if (type === "stderr")
            line.className = "text-red-600";
        else if (type === "tutorial")
            line.className = "text-blue-600 font-semibold";
        else if (type === "info")
            line.className = "text-yellow-600 italic";
        else
            line.className = "text-green-700";
        line.textContent = message;
        fragment.appendChild(line);
    });
    container.appendChild(fragment);
    container.scrollTop = container.scrollHeight;
    outputBuffer.length = 0;
    // Save to LocalStorage (Debounced)
    saveLogDebounced();
};
// Set case directory manually
const setCase = async () => {
    try {
        caseDir = document.getElementById("caseDir").value;
        const response = await fetch("/set_case", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ caseDir }),
        });
        if (!response.ok)
            throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        caseDir = data.caseDir;
        document.getElementById("caseDir").value = caseDir;
        if (data.output) {
            data.output.split("\n").forEach((line) => {
                line = line.trim();
                if (line.startsWith("INFO"))
                    appendOutput(line.replace("INFO", ""), "info");
                else if (line.startsWith("Error"))
                    appendOutput(line, "stderr");
                else
                    appendOutput(line, "stdout");
            });
        }
        showNotification("Case directory set", "info");
    }
    catch (error) {
        console.error("FOAMFlask Error setting case", error);
        appendOutput(`FOAMFlask Failed to set case directory ${getErrorMessage(error)}`, "stderr");
        showNotification("Failed to set case directory", "error");
    }
};
// Update Docker config instead of OpenFOAM root
const setDockerConfig = async (image, version) => {
    try {
        dockerImage = image;
        openfoamVersion = version;
        const response = await fetch("/set_docker_config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ dockerImage, openfoamVersion }),
        });
        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }
        const data = await response.json();
        dockerImage = data.dockerImage;
        openfoamVersion = data.openfoamVersion;
        const openfoamRootInput = document.getElementById("openfoamRoot");
        if (openfoamRootInput instanceof HTMLInputElement) {
            openfoamRootInput.value = `${dockerImage} OpenFOAM ${openfoamVersion}`;
        }
        appendOutput(`Docker config set to ${dockerImage} OpenFOAM ${openfoamVersion}`, "info");
        showNotification("Docker config updated", "success");
    }
    catch (error) {
        console.error("FOAMFlask Error setting Docker config", error);
        appendOutput(`FOAMFlask Failed to set Docker config ${getErrorMessage(error)}`, "stderr");
        showNotification("Failed to set Docker config", "error");
    }
};
// Load a tutorial
const loadTutorial = async () => {
    try {
        const tutorialSelect = document.getElementById("tutorialSelect");
        const selected = tutorialSelect.value;
        if (selected)
            localStorage.setItem("lastSelectedTutorial", selected);
        const response = await fetch("/load_tutorial", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tutorial: selected }),
        });
        if (!response.ok)
            throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        if (data.output) {
            data.output.split("\n").forEach((line) => {
                line = line.trim();
                if (line.startsWith("INFO:FOAMFlask Tutorial loaded")) {
                    appendOutput(line.replace("INFO:FOAMFlask Tutorial loaded", "FOAMFlask Tutorial loaded"), "tutorial");
                }
                else if (line.startsWith("Source")) {
                    appendOutput(`FOAMFlask ${line}`, "info");
                }
                else if (line.startsWith("Copied to")) {
                    appendOutput(`FOAMFlask ${line}`, "info");
                }
                else {
                    const type = /error/i.test(line) ? "stderr" : "stdout";
                    appendOutput(line, type);
                }
            });
        }
        showNotification("Tutorial loaded", "info");
    }
    catch (error) {
        console.error("FOAMFlask Error loading tutorial", error);
        appendOutput(`FOAMFlask Failed to load tutorial ${getErrorMessage(error)}`, "stderr");
        showNotification("Failed to load tutorial", "error");
    }
};
// Run OpenFOAM commands
const runCommand = async (cmd) => {
    if (!cmd) {
        appendOutput("FOAMFlask Error: No command specified!", "stderr");
        showNotification("No command specified", "error");
        return;
    }
    try {
        // ... get selectedTutorial ...
        const selectedTutorial = document.getElementById("tutorialSelect").value;
        const outputDiv = document.getElementById("output");
        if (outputDiv) {
            outputDiv.innerHTML = "";
            localStorage.removeItem(CONSOLE_LOG_KEY);
            if (saveLogTimer)
                clearTimeout(saveLogTimer);
        }
        outputBuffer.length = 0;
        showNotification(`Running ${cmd}...`, "info");
        const response = await fetch("/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                caseDir,
                tutorial: selectedTutorial,
                command: cmd,
            }),
        });
        if (!response.ok)
            throw new Error(`HTTP error! status: ${response.status}`);
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        const read = async () => {
            const { done, value } = (await reader?.read()) || {
                done: true,
                value: undefined,
            };
            if (done) {
                flushOutputBuffer();
                showNotification(`${cmd} completed`, "success");
                return;
            }
            const text = decoder.decode(value);
            text.split("\n").forEach((line) => {
                if (!line.trim())
                    return;
                const type = /error/i.test(line) ? "stderr" : "stdout";
                appendOutput(line, type);
            });
            await read();
        };
        await read();
    }
    catch (error) {
        appendOutput(`FOAMFlask Error reading response ${getErrorMessage(error)}`, "stderr");
        const errorMsg = cmd.includes("foamToVTK")
            ? "Failed to generate VTK files. Make sure the simulation has completed successfully."
            : `Error running ${cmd}`;
        showNotification(errorMsg, "error");
    }
};
// Realtime Plotting Functions
const togglePlots = () => {
    plotsVisible = !plotsVisible;
    const container = document.getElementById("plotsContainer");
    const btn = document.getElementById("togglePlotsBtn");
    const aeroBtn = document.getElementById("toggleAeroBtn");
    if (plotsVisible) {
        container?.classList.remove("hidden");
        btn.textContent = "Hide Plots";
        aeroBtn?.classList.remove("hidden");
        startPlotUpdates();
        setupIntersectionObserver();
    }
    else {
        container?.classList.add("hidden");
        btn.textContent = "Show Plots";
        aeroBtn?.classList.add("hidden");
        stopPlotUpdates();
    }
};
const setupIntersectionObserver = () => {
    const plotsContainer = document.getElementById("plotsContainer");
    if (!plotsContainer || plotsContainer.dataset.observerSetup)
        return;
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            plotsInViewport = entry.isIntersecting;
        });
    }, { threshold: 0.1, rootMargin: "50px" });
    observer.observe(plotsContainer);
    plotsContainer.dataset.observerSetup = "true";
};
const toggleAeroPlots = () => {
    aeroVisible = !aeroVisible;
    const container = document.getElementById("aeroContainer");
    const btn = document.getElementById("toggleAeroBtn");
    if (aeroVisible) {
        container?.classList.remove("hidden");
        btn.textContent = "Hide Aero Plots";
        updateAeroPlots();
    }
    else {
        container?.classList.add("hidden");
        btn.textContent = "Show Aero Plots";
    }
};
const startPlotUpdates = () => {
    if (plotUpdateInterval)
        return;
    plotUpdateInterval = setInterval(() => {
        if (!plotsInViewport)
            return;
        if (!isUpdatingPlots)
            updatePlots();
        else
            pendingPlotUpdate = true;
    }, 2000);
};
const stopPlotUpdates = () => {
    if (plotUpdateInterval) {
        clearInterval(plotUpdateInterval);
        plotUpdateInterval = null;
    }
};
const updateResidualsPlot = async (tutorial) => {
    try {
        const data = await fetchWithCache(`/api/residuals?tutorial=${encodeURIComponent(tutorial)}`);
        // console.log("Residuals data received:", data);
        if (data.error || !data.time || data.time.length === 0) {
            console.log("Residuals plot early return:", { error: data.error, hasTime: !!data.time, timeLength: data.time?.length });
            return;
        }
        const traces = [];
        const fields = ["Ux", "Uy", "Uz", "p"];
        const colors = [
            plotlyColors.blue,
            plotlyColors.red,
            plotlyColors.green,
            plotlyColors.magenta,
            plotlyColors.cyan,
            plotlyColors.orange,
        ];
        fields.forEach((field, idx) => {
            // Need to cast data to any because ResidualsResponse doesn't allow index access easily with string literals in strict mode
            // or check property existence
            const fieldData = data[field];
            if (fieldData && fieldData.length > 0) {
                traces.push({
                    x: Array.from({ length: fieldData.length }, (_, i) => i + 1),
                    y: fieldData,
                    type: "scatter",
                    mode: "lines",
                    name: field,
                    line: { color: colors[idx], width: 2.5, shape: "linear" },
                });
            }
        });
        if (traces.length > 0) {
            const residualsPlotDiv = getElement("residuals-plot");
            if (residualsPlotDiv) {
                const layout = {
                    ...plotLayout,
                    title: createBoldTitle("Residuals"),
                    xaxis: {
                        title: { text: "Iteration" },
                        showline: true,
                        mirror: "all",
                        showgrid: false,
                    },
                    yaxis: {
                        title: { text: "Residual" },
                        type: "log",
                        showline: true,
                        mirror: "all",
                        showgrid: true,
                        gridwidth: 1,
                        gridcolor: "rgba(0,0,0,0.1)",
                    },
                };
                void Plotly.react(residualsPlotDiv, traces, layout, {
                    ...plotConfig,
                    displayModeBar: true,
                    scrollZoom: false,
                }).then(() => attachWhiteBGDownloadButton(residualsPlotDiv));
            }
        }
    }
    catch (error) {
        console.error("FOAMFlask Error updating residuals", error);
    }
};
const updateAeroPlots = async () => {
    const selectedTutorial = document.getElementById("tutorialSelect")?.value;
    if (!selectedTutorial)
        return;
    try {
        // Switch to api_plot_data to get time series data (arrays)
        const response = await fetch(`/api/plot_data?tutorial=${encodeURIComponent(selectedTutorial)}`);
        const data = await response.json();
        if (data.error)
            return;
        // Cp plot
        if (Array.isArray(data.p) &&
            Array.isArray(data.time) &&
            data.p.length === data.time.length &&
            data.p.length > 0) {
            const pinf = 101325;
            const rho = 1.225;
            // U_mag might be an array, assume we want a reference velocity.
            // If it's a time series, maybe take the last value or max?
            // Original code assumed U_mag[0].
            const uinf = Array.isArray(data.U_mag) && data.U_mag.length ? data.U_mag[0] : 1.0;
            const qinf = 0.5 * rho * uinf * uinf;
            const cp = data.p.map((pval) => (pval - pinf) / qinf);
            const cpDiv = document.getElementById("cp-plot");
            if (cpDiv) {
                const cpTrace = {
                    x: data.time,
                    y: cp,
                    type: "scatter",
                    mode: "lines+markers",
                    name: "Cp",
                    line: { color: plotlyColors.red, width: 2.5 },
                };
                void Plotly.react(cpDiv, [cpTrace], {
                    ...plotLayout,
                    title: createBoldTitle("Pressure Coefficient"),
                    xaxis: {
                        ...plotLayout.xaxis,
                        title: { text: "Time (s)" },
                    },
                    yaxis: {
                        ...plotLayout.yaxis,
                        title: { text: "Cp" },
                    },
                }, plotConfig)
                    .then(() => {
                    attachWhiteBGDownloadButton(cpDiv);
                })
                    .catch((err) => {
                    console.error("Plotly update failed:", err);
                });
            }
        }
        // Velocity profile 3D plot
        if (Array.isArray(data.Ux) &&
            Array.isArray(data.Uy) &&
            Array.isArray(data.Uz)) {
            const velocityDiv = document.getElementById("velocity-profile-plot");
            if (velocityDiv) {
                const velocityTrace = {
                    x: data.Ux,
                    y: data.Uy,
                    z: data.Uz,
                    type: "scatter3d",
                    mode: "markers",
                    name: "Velocity",
                    marker: { color: plotlyColors.blue, size: 5 },
                };
                void Plotly.react(velocityDiv, [velocityTrace], {
                    ...plotLayout,
                    title: createBoldTitle("Velocity Profile"),
                    scene: {
                        xaxis: { title: { text: "Ux" } },
                        yaxis: { title: { text: "Uy" } },
                        zaxis: { title: { text: "Uz" } },
                    },
                }, plotConfig)
                    .then(() => {
                    attachWhiteBGDownloadButton(velocityDiv);
                })
                    .catch((err) => {
                    console.error("Plotly update failed:", err);
                });
            }
        }
    }
    catch (error) {
        console.error("FOAMFlask Error updating aero plots", error);
    }
};
// UpdatePlots
const updatePlots = async () => {
    const selectedTutorial = document.getElementById("tutorialSelect")?.value;
    if (!selectedTutorial || isUpdatingPlots)
        return;
    isUpdatingPlots = true;
    try {
        const data = await fetchWithCache(`/api/plot_data?tutorial=${encodeURIComponent(selectedTutorial)}`);
        if (data.error) {
            console.error("FOAMFlask Error fetching plot data", data.error);
            showNotification("Error fetching plot data", "error");
            return;
        }
        // Pressure plot
        if (data.p && data.time) {
            const pressureDiv = getElement("pressure-plot");
            if (!pressureDiv) {
                console.error("Pressure plot element not found");
                return;
            }
            const legendVisibility = getLegendVisibility(pressureDiv);
            const pressureTrace = {
                x: data.time,
                y: data.p,
                type: "scatter",
                mode: "lines",
                name: "Pressure",
                line: { color: plotlyColors.blue, ...lineStyle, width: 2.5 },
            };
            if (pressureTrace.name && legendVisibility.hasOwnProperty(pressureTrace.name)) {
                pressureTrace.visible = legendVisibility[pressureTrace.name];
            }
            void Plotly.react(pressureDiv, [pressureTrace], {
                ...plotLayout,
                title: createBoldTitle("Pressure vs Time"),
                xaxis: {
                    ...plotLayout.xaxis,
                    title: { text: "Time (s)" },
                },
                yaxis: {
                    ...plotLayout.yaxis,
                    title: { text: "Pressure (Pa)" },
                },
            }, plotConfig)
                .then(() => {
                attachWhiteBGDownloadButton(pressureDiv);
            })
                .catch((err) => {
                console.error("Plotly update failed:", err);
            });
        }
        // Velocity plot
        if (data.U_mag && data.time) {
            const velocityDiv = getElement("velocity-plot");
            if (!velocityDiv) {
                console.error("Velocity plot element not found");
                return;
            }
            const legendVisibility = getLegendVisibility(velocityDiv);
            const traces = [
                {
                    x: data.time,
                    y: data.U_mag,
                    type: "scatter",
                    mode: "lines",
                    name: "|U|",
                    line: { color: plotlyColors.red, ...lineStyle, width: 2.5 },
                },
            ];
            if (data.Ux) {
                traces.push({
                    x: data.time,
                    y: data.Ux,
                    type: "scatter",
                    mode: "lines",
                    name: "Ux",
                    line: {
                        color: plotlyColors.blue,
                        ...lineStyle,
                        dash: "dash",
                        width: 2.5,
                    },
                });
            }
            if (data.Uy) {
                traces.push({
                    x: data.time,
                    y: data.Uy,
                    type: "scatter",
                    mode: "lines",
                    name: "Uy",
                    line: {
                        color: plotlyColors.green,
                        ...lineStyle,
                        dash: "dot",
                        width: 2.5,
                    },
                });
            }
            if (data.Uz) {
                traces.push({
                    x: data.time,
                    y: data.Uz,
                    type: "scatter",
                    mode: "lines",
                    name: "Uz",
                    line: {
                        color: plotlyColors.purple,
                        ...lineStyle,
                        dash: "dashdot",
                        width: 2.5,
                    },
                });
            }
            // Apply saved visibility safely
            traces.forEach((tr) => {
                if (tr.name && Object.prototype.hasOwnProperty.call(legendVisibility, tr.name)) {
                    tr.visible = legendVisibility[tr.name];
                }
            });
            void Plotly.react(velocityDiv, traces, {
                ...plotLayout,
                title: createBoldTitle("Velocity vs Time"),
                xaxis: {
                    ...plotLayout.xaxis,
                    title: { text: "Time (s)" },
                },
                yaxis: {
                    ...plotLayout.yaxis,
                    title: { text: "Velocity (m/s)" },
                },
            }, plotConfig).then(() => {
                attachWhiteBGDownloadButton(velocityDiv);
            });
        }
        // Turbulence plot
        const turbulenceTrace = [];
        if (data.nut && data.time) {
            turbulenceTrace.push({
                x: data.time,
                y: data.nut,
                type: "scatter",
                mode: "lines",
                name: "nut",
                line: { color: plotlyColors.teal, ...lineStyle, width: 2.5 },
            });
        }
        if (data.nuTilda && data.time) {
            turbulenceTrace.push({
                x: data.time,
                y: data.nuTilda,
                type: "scatter",
                mode: "lines",
                name: "nuTilda",
                line: { color: plotlyColors.cyan, ...lineStyle, width: 2.5 },
            });
        }
        if (data.k && data.time) {
            turbulenceTrace.push({
                x: data.time,
                y: data.k,
                type: "scatter",
                mode: "lines",
                name: "k",
                line: { color: plotlyColors.magenta, ...lineStyle, width: 2.5 },
            });
        }
        if (data.omega && data.time) {
            turbulenceTrace.push({
                x: data.time,
                y: data.omega,
                type: "scatter",
                mode: "lines",
                name: "omega",
                line: { color: plotlyColors.brown, ...lineStyle, width: 2.5 },
            });
        }
        if (turbulenceTrace.length > 0) {
            const turbPlotDiv = document.getElementById("turbulence-plot");
            if (turbPlotDiv) {
                void Plotly.react(turbPlotDiv, turbulenceTrace, {
                    ...plotLayout,
                    title: createBoldTitle("Turbulence Properties vs Time"),
                    xaxis: {
                        ...plotLayout.xaxis,
                        title: { text: "Time (s)" },
                    },
                    yaxis: {
                        ...plotLayout.yaxis,
                        title: { text: "Value" },
                    },
                }, plotConfig).then(() => {
                    attachWhiteBGDownloadButton(turbPlotDiv);
                });
            }
        }
        // Update residuals and aero plots in parallel
        const updatePromises = [updateResidualsPlot(selectedTutorial)];
        if (aeroVisible)
            updatePromises.push(updateAeroPlots());
        await Promise.allSettled(updatePromises);
        // After all plots are updated
        if (isFirstPlotLoad) {
            showNotification("Plots loaded successfully", "success", 3000);
            isFirstPlotLoad = false;
        }
    }
    catch (error) {
        console.error("FOAMFlask Error updating plots", error);
        const currentTime = Date.now();
        const selectedTutorial = document.getElementById("tutorialSelect")?.value;
        if (selectedTutorial &&
            currentTime - lastErrorNotificationTime > ERROR_NOTIFICATION_COOLDOWN) {
            showNotification(`Error updating plots: ${error instanceof Error ? error.message : "Unknown error"}`, "error");
            lastErrorNotificationTime = currentTime;
        }
    }
    finally {
        isUpdatingPlots = false;
        // FIX: Hide loader after update completes
        const loader = document.getElementById("plotsLoading");
        if (loader && !loader.classList.contains("hidden")) {
            loader.classList.add("hidden");
        }
        if (pendingPlotUpdate) {
            pendingPlotUpdate = false;
            requestAnimationFrame(updatePlots);
        }
    }
};
const downloadPlotData = (plotId, filename) => {
    const plotDiv = document.getElementById(plotId); // Cast to any for plotly data access
    if (!plotDiv || !plotDiv.data) {
        console.error("FOAMFlask Plot data not available");
        return;
    }
    const traces = plotDiv.data;
    if (traces.length === 0) {
        console.error("FOAMFlask No traces found in the plot");
        return;
    }
    traces.forEach((trace, index) => {
        // Explicit types
        if (!trace.x || !trace.y)
            return;
        let csvContent = "x,y\n";
        for (let i = 0; i < trace.x.length; i++) {
            const x = trace.x[i] ?? "";
            const y = trace.y[i] ?? "";
            csvContent += `${x},${y}\n`;
        }
        const traceName = trace.name?.replace(/\s+/g, "").toLowerCase() || `trace${index + 1}`;
        const traceFilename = filename.replace(".csv", `${traceName}.csv`);
        try {
            const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = traceFilename;
            document.body.appendChild(link);
            link.click();
            setTimeout(() => {
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
            }, 100);
        }
        catch (error) {
            console.error(`FOAMFlask Error downloading ${traceName} data`, error);
        }
    });
};
// Mesh Visualization Functions
const refreshMeshList = async () => {
    try {
        const tutorial = document.getElementById("tutorialSelect")?.value;
        if (!tutorial) {
            showNotification("Please select a tutorial first", "error");
            return;
        }
        const response = await fetch(`/api/available_meshes?tutorial=${encodeURIComponent(tutorial)}`);
        if (!response.ok)
            throw new Error("Failed to fetch mesh files");
        const data = await response.json();
        if (data.error) {
            showNotification(data.error, "error");
            return;
        }
        availableMeshes = data.meshes;
        const meshSelect = document.getElementById("meshSelect");
        const meshActionButtons = document.getElementById("meshActionButtons");
        if (!meshSelect) {
            console.error("meshSelect element not found");
            return;
        }
        meshSelect.innerHTML = '<option value="">-- Select a mesh file --</option>';
        if (availableMeshes.length === 0) {
            showNotification("No mesh files found in this case", "warning");
            meshSelect.innerHTML =
                '<option value="" disabled>No mesh files found</option>';
            if (meshActionButtons) {
                meshActionButtons.classList.remove("opacity-50", "h-0", "overflow-hidden", "mb-0");
                meshActionButtons.classList.add("opacity-100", "h-auto", "mb-2");
            }
            return;
        }
        availableMeshes.forEach((mesh) => {
            const option = document.createElement("option");
            option.value = mesh.path;
            option.textContent = mesh.name;
            meshSelect.appendChild(option);
        });
        showNotification(`Found ${availableMeshes.length} mesh files`, "success");
        if (meshActionButtons) {
            meshActionButtons.classList.add("opacity-50", "h-0", "overflow-hidden", "mb-0");
            meshActionButtons.classList.remove("opacity-100", "h-auto", "mb-2");
        }
    }
    catch (error) {
        console.error("Error refreshing mesh list", error);
        showNotification(`Error loading mesh files: ${getErrorMessage(error)}`, "error");
    }
};
const runFoamToVTK = async () => {
    // ... check for selectedTutorial ...
    const selectedTutorial = document.getElementById("tutorialSelect")?.value;
    if (!selectedTutorial) {
        showNotification("Please select a tutorial first", "error");
        return;
    }
    const outputDiv = document.getElementById("output");
    if (outputDiv) {
        outputDiv.innerHTML = "";
        localStorage.removeItem(CONSOLE_LOG_KEY);
        if (saveLogTimer)
            clearTimeout(saveLogTimer);
    }
    outputBuffer.length = 0;
    showNotification("Running <strong>foamToVTK</strong>", "info");
    showNotification("Check <strong>Run/Log</strong> for more details", "info", 10000);
    try {
        const response = await fetch("/run_foamtovtk", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ caseDir, tutorial: selectedTutorial }),
        });
        if (!response.ok)
            throw new Error(`HTTP error! status: ${response.status}`);
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        while (true) {
            const { done, value } = (await reader?.read()) || {
                done: true,
                value: undefined,
            };
            if (done)
                break;
            const text = decoder.decode(value);
            appendOutput(text, "stdout");
        }
        showNotification("foamToVTK completed", "success");
    }
    catch (error) {
        console.error("Error running foamToVTK", error);
        appendOutput(`Error: ${getErrorMessage(error)}`, "stderr");
        showNotification("Failed to run foamToVTK", "error");
    }
};
const loadMeshVisualization = async () => {
    const meshSelect = document.getElementById("meshSelect");
    const selectedPath = meshSelect.value;
    if (!selectedPath) {
        showNotification("Please select a mesh file", "warning");
        return;
    }
    try {
        showNotification("Loading mesh...", "info");
        const infoResponse = await fetch("/api/load_mesh", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_path: selectedPath }),
        });
        if (!infoResponse.ok)
            throw new Error(`HTTP error! status: ${infoResponse.status}`);
        const meshInfo = await infoResponse.json();
        if (!meshInfo.success) {
            showNotification(`${meshInfo.error} Failed to load mesh`, "error");
            return;
        }
        displayMeshInfo(meshInfo);
        currentMeshPath = selectedPath;
        await updateMeshView();
        document.getElementById("meshControls")?.classList.remove("hidden");
        showNotification("Mesh loaded successfully", "success");
    }
    catch (error) {
        console.error("FOAMFlask Error loading mesh", error);
        showNotification("Failed to load mesh", "error");
    }
};
async function updateMeshView() {
    if (!currentMeshPath) {
        showNotification("No mesh loaded", "warning");
        return;
    }
    let loadingNotification = null;
    try {
        const showEdgesInput = document.getElementById("showEdges");
        const colorInput = document.getElementById("meshColor");
        const cameraPositionSelect = document.getElementById("cameraPosition");
        if (!showEdgesInput || !colorInput || !cameraPositionSelect) {
            showNotification("Required mesh controls not found", "error");
            return;
        }
        const showEdges = showEdgesInput.checked;
        const color = colorInput.value;
        const cameraPosition = cameraPositionSelect.value;
        // Show persistent loading notification
        loadingNotification = showNotification("Rendering mesh...", "info", 0);
        const response = await fetch("/api/mesh_screenshot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
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
            throw new Error(data.error || "Failed to render mesh");
        }
        // Display the image
        const meshImage = document.getElementById("meshImage");
        const meshPlaceholder = document.getElementById("meshPlaceholder");
        if (!meshImage || !meshPlaceholder) {
            showNotification("Mesh image or placeholder element not found", "error");
            return;
        }
        meshImage.onload = function () {
            // Only remove loading notification after image is fully loaded
            if (loadingNotification !== null) {
                removeNotification(loadingNotification);
            }
            showNotification("Mesh rendered successfully", "success", 2000);
        };
        meshImage.src = `data:image/png;base64,${data.image}`;
        meshImage.classList.remove("hidden");
        meshPlaceholder.classList.add("hidden");
    }
    catch (error) {
        console.error("[FOAMFlask] Error rendering mesh:", error);
        if (loadingNotification !== null) {
            removeNotification(loadingNotification);
        }
        showNotification(`Error: ${getErrorMessage(error)}`, "error", 3000);
    }
}
function displayMeshInfo(meshInfo) {
    const meshInfoDiv = document.getElementById("meshInfo");
    const meshInfoContent = document.getElementById("meshInfoContent");
    if (!meshInfoDiv || !meshInfoContent) {
        console.error("Mesh info or content element not found");
        return;
    }
    if (!meshInfo || !meshInfo.success) {
        meshInfoDiv.classList.add("hidden");
        return;
    }
    // Format the mesh information
    const infoItems = [
        { label: "Points", value: meshInfo.n_points?.toLocaleString() || "N/A" },
        { label: "Cells", value: meshInfo.n_cells?.toLocaleString() || "N/A" },
        {
            label: "Length",
            value: meshInfo.length ? meshInfo.length.toFixed(3) : "N/A",
        },
        {
            label: "Volume",
            value: meshInfo.volume ? meshInfo.volume.toFixed(3) : "N/A",
        },
    ];
    meshInfoContent.innerHTML = infoItems
        .map((item) => `<div><strong>${item.label}:</strong> ${item.value}</div>`)
        .join("");
    // Add bounds if available
    if (meshInfo.bounds && Array.isArray(meshInfo.bounds)) {
        const boundsStr = `[${meshInfo.bounds
            .map((b) => b.toFixed(2))
            .join(", ")}]`;
        meshInfoContent.innerHTML += `<div class="col-span-2"><strong>Bounds:</strong> ${boundsStr}</div>`;
    }
    // Add center if available
    if (meshInfo.center && Array.isArray(meshInfo.center)) {
        const centerStr = `(${meshInfo.center
            .map((c) => c.toFixed(2))
            .join(", ")})`;
        meshInfoContent.innerHTML += `<div class="col-span-2"><strong>Center:</strong> ${centerStr}</div>`;
    }
    meshInfoDiv.classList.remove("hidden");
}
async function toggleInteractiveMode() {
    if (!currentMeshPath) {
        showNotification("Please load a mesh first", "warning");
        return;
    }
    const meshImage = document.getElementById("meshImage");
    const meshInteractive = document.getElementById("meshInteractive");
    const meshPlaceholder = document.getElementById("meshPlaceholder");
    const toggleBtn = document.getElementById("toggleInteractiveBtn");
    const cameraControl = document.getElementById("cameraPosition");
    const updateBtn = document.getElementById("updateViewBtn");
    if (!meshImage ||
        !meshInteractive ||
        !meshPlaceholder ||
        !toggleBtn ||
        !cameraControl ||
        !updateBtn) {
        showNotification("Required mesh elements not found", "error");
        return;
    }
    isInteractiveMode = !isInteractiveMode;
    if (isInteractiveMode) {
        // Switch to interactive mode
        showNotification("Loading interactive viewer...", "info");
        try {
            const showEdgesInput = document.getElementById("showEdges");
            const colorInput = document.getElementById("meshColor");
            if (!showEdgesInput || !colorInput) {
                showNotification("Required mesh controls not found", "error");
                isInteractiveMode = false;
                return;
            }
            const showEdges = showEdgesInput.checked;
            const color = colorInput.value;
            // Fetch interactive viewer HTML
            const response = await fetch("/api/mesh_interactive", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
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
            meshImage.classList.add("hidden");
            meshPlaceholder.classList.add("hidden");
            meshInteractive.classList.remove("hidden");
            // Load HTML into iframe using srcdoc
            meshInteractive.srcdoc = html;
            // Update button text
            toggleBtn.textContent = "Static Mode";
            toggleBtn.classList.remove("bg-purple-500", "hover:bg-purple-600");
            toggleBtn.classList.add("bg-orange-500", "hover:bg-orange-600");
            // Hide camera position control (not needed in interactive mode)
            cameraControl.classList.add("hidden");
            updateBtn.classList.add("hidden");
            showNotification("Interactive mode enabled - Use mouse to rotate, zoom, and pan", "success", 8000);
        }
        catch (error) {
            console.error("[FOAMFlask] Error loading interactive viewer:", error);
            const errorMessage = error instanceof Error
                ? error.name === "AbortError"
                    ? "Loading was cancelled or timed out"
                    : error.message
                : "Failed to load interactive viewer";
            showNotification(`Failed to load interactive viewer: ${errorMessage}`, "error");
            // Reset to static mode
            isInteractiveMode = false;
            // Safely update UI elements if they exist
            toggleBtn.textContent = "Interactive Mode";
            toggleBtn.classList.remove("bg-orange-500", "hover:bg-orange-600");
            toggleBtn.classList.add("bg-purple-500", "hover:bg-purple-600");
            cameraControl.classList.remove("hidden");
            updateBtn.classList.remove("hidden");
            meshInteractive.classList.add("hidden");
            meshImage.classList.remove("hidden");
        }
    }
    else {
        // Switch back to static mode
        meshInteractive.classList.add("hidden");
        meshImage.classList.remove("hidden");
        // Update button text
        toggleBtn.textContent = "Interactive Mode";
        toggleBtn.classList.remove("bg-orange-500", "hover:bg-orange-600");
        toggleBtn.classList.add("bg-purple-500", "hover:bg-purple-600");
        // Show camera position control again
        cameraControl.classList.remove("hidden");
        updateBtn.classList.remove("hidden");
        showNotification("Switched to static mode", "info", 2000);
    }
}
// Set camera view for interactive mode
function setCameraView(view) {
    const iframe = document.getElementById("meshInteractive");
    if (!iframe || !iframe.contentWindow)
        return;
    try {
        // Send message to iframe to set camera view
        iframe.contentWindow.postMessage({
            type: "setCameraView",
            view: view,
        }, "*");
        showNotification(`Set view to ${view.toUpperCase()}`, "info", 1500);
    }
    catch (error) {
        console.error("Error setting camera view:", error);
    }
}
// Reset camera to default view
function resetCamera() {
    const iframe = document.getElementById("meshInteractive");
    if (!iframe || !iframe.contentWindow)
        return;
    try {
        // Send message to iframe to reset camera
        iframe.contentWindow.postMessage({
            type: "resetCamera",
        }, "*");
        showNotification("Camera view reset", "info", 1500);
    }
    catch (error) {
        console.error("Error resetting camera:", error);
    }
}
// Simple path join function for browser
function joinPath(...parts) {
    // Filter out empty parts and join with forward slashes
    return parts
        .filter((part) => part)
        .join("/")
        .replace(/\/+/g, "/");
}
// --- Post Processing Functions ---
async function refreshPostList() {
    const postContainer = document.getElementById("post-processing-content");
    if (!postContainer)
        return;
    // Show loading state
    postContainer.innerHTML =
        '<div class="p-4 text-center text-gray-500">Loading post-processing options...</div>';
    // Call VTK file loading function
    await refreshPostListVTK();
    try {
        postContainer.innerHTML = `
        <div class="space-y-4">
          <div class="bg-white p-4 rounded-lg shadow">
            <h3 class="font-medium text-gray-900">VTK File Selection</h3>
            <div class="mt-2">
              <select id="vtkFileSelect" class="border border-gray-300 rounded px-3 py-2 w-full">
                <option value="">-- Select a VTK file --</option>
              </select>
            </div>
          </div>
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
    }
    catch (error) {
        console.error("[FOAMFlask] [refreshPostList] Error loading post-processing options:", error);
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
async function runPostOperation(operation) {
    const resultsDiv = document.getElementById("post-results") || document.body;
    try {
        if (operation === "create_contour") {
            const tutorialSelect = document.getElementById("tutorialSelect");
            const tutorial = tutorialSelect ? tutorialSelect.value : null;
            if (!tutorial) {
                showNotification("Please select a tutorial first", "warning");
                return;
            }
            const caseDirInput = document.getElementById("caseDir");
            const caseDirValue = caseDirInput ? caseDirInput.value : "";
            await generateContoursFn({
                tutorial: tutorial,
                caseDir: caseDirValue,
                scalarField: "U_Magnitude",
                numIsosurfaces: 10,
            });
        }
        else {
            resultsDiv.innerHTML = `<div class="p-4 text-blue-600">Running ${operation}...</div>`;
            await new Promise((resolve) => setTimeout(resolve, 1000));
            resultsDiv.innerHTML = `
        <div class="p-4 bg-green-50 text-green-700 rounded">
          ${operation
                .replace(/_/g, " ")
                .replace(/\b\w/g, (l) => l.toUpperCase())} completed successfully!
        </div>
      `;
        }
    }
    catch (error) {
        const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
        resultsDiv.innerHTML = `
      <div class="p-4 bg-red-50 text-red-700 rounded">
        Error running ${operation}: ${errorMessage}
      </div>
    `;
        console.error(`[FOAMFlask] [runPostOperation] Error running ${operation}:`, error);
    }
}
// Refresh VTK file list on Post page
async function refreshPostListVTK() {
    const tutorialSelect = document.getElementById("tutorialSelect");
    const tutorial = tutorialSelect?.value;
    if (!tutorial) {
        showNotification("Please select a tutorial first", "warning");
        return;
    }
    try {
        const response = await fetch(`/api/available_meshes?tutorial=${encodeURIComponent(tutorial)}`);
        if (!response.ok)
            throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        const vtkFiles = data.meshes || [];
        const vtkSelect = document.getElementById("vtkFileSelect");
        if (!vtkSelect) {
            console.error("vtkFileSelect element not found");
            return;
        }
        vtkSelect.innerHTML = '<option value="">-- Select a VTK file --</option>';
        vtkFiles.forEach((file) => {
            const option = document.createElement("option");
            option.value = file.path;
            option.textContent = file.name || file.path.split("/").pop() || null;
            vtkSelect.appendChild(option);
        });
    }
    catch (error) {
        console.error("[FOAMFlask] Error fetching VTK files:", error);
    }
}
// Load selected VTK file
async function loadSelectedVTK() {
    const vtkSelect = document.getElementById("vtkFileSelect");
    const selectedFile = vtkSelect?.value;
    if (!selectedFile) {
        showNotification("Please select a VTK file", "warning");
        return;
    }
    try {
        const response = await fetch("/api/load_mesh", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_path: selectedFile }),
        });
        const meshInfo = await response.json();
        if (meshInfo.success) {
            const scalarFieldSelect = document.getElementById("scalarField");
            if (!scalarFieldSelect) {
                console.error("scalarField select element not found");
                return;
            }
            scalarFieldSelect.innerHTML = "";
            (meshInfo.point_arrays || []).forEach((field) => {
                const option = document.createElement("option");
                option.value = field;
                option.textContent = field;
                scalarFieldSelect.appendChild(option);
            });
            showNotification("VTK file loaded successfully!", "success");
        }
    }
    catch (error) {
        console.error("[FOAMFlask] Error loading VTK file:", error);
        showNotification("Error loading VTK file", "error");
    }
}
// Contour Visualization
async function loadContourVTK() {
    const vtkSelect = document.getElementById("vtkFileSelect");
    const selectedFile = vtkSelect?.value;
    if (!selectedFile) {
        showNotification("Please select a VTK file", "warning");
        return;
    }
    try {
        showNotification("Loading VTK file for contour generation...", "info");
        console.log("[FOAMFlask] Loading VTK file for contour:", selectedFile);
        const response = await fetch("/api/load_mesh", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
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
        console.log("[FOAMFlask] Received mesh info:", meshInfo);
        if (!meshInfo.success) {
            throw new Error(meshInfo.error || "Failed to load mesh");
        }
        const scalarFieldSelect = document.getElementById("scalarField");
        if (!scalarFieldSelect) {
            throw new Error("Could not find scalar field select element");
        }
        const pointArrays = meshInfo.point_arrays || [];
        const cellArrays = meshInfo.cell_arrays || [];
        scalarFieldSelect.innerHTML = "";
        pointArrays.forEach((field) => {
            const option = document.createElement("option");
            option.value = `${field}@point`;
            option.textContent = `🔵 ${field} (Point Data)`;
            option.className = "point-data-option";
            option.dataset.fieldType = "point";
            scalarFieldSelect.appendChild(option);
        });
        cellArrays.forEach((field) => {
            const option = document.createElement("option");
            option.value = `${field}@cell`;
            option.textContent = `🟢 ${field} (Cell Data)`;
            option.className = "cell-data-option";
            option.dataset.fieldType = "cell";
            scalarFieldSelect.appendChild(option);
        });
        if (scalarFieldSelect.options.length === 0) {
            console.warn("[FOAMFlask] No data arrays found in mesh");
            showNotification("No scalar fields found in the mesh", "warning");
        }
        const generateBtn = document.getElementById("generateContoursBtn");
        if (generateBtn) {
            generateBtn.disabled = false;
        }
        else {
            console.warn("[FOAMFlask] Could not find generateContoursBtn");
        }
        showNotification("VTK file loaded for contour generation!", "success");
        console.log("[FOAMFlask] Successfully loaded mesh for contour generation");
    }
    catch (error) {
        console.error("[FOAMFlask] Error loading VTK file for contour:", error);
        showNotification(`Error: ${error instanceof Error
            ? error.message
            : "Failed to load VTK file for contour generation"}`, "error");
    }
}
// Handle custom VTK file upload
async function loadCustomVTKFile() {
    const fileInput = document.getElementById("vtkFileBrowser");
    const file = fileInput?.files?.[0];
    if (!file) {
        showNotification("Please select a file first", "warning");
        return;
    }
    const formData = new FormData();
    formData.append("file", file);
    try {
        showNotification("Uploading and processing VTK file...", "info");
        const response = await fetch("/api/upload_vtk", {
            method: "POST",
            body: formData,
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || "Failed to upload file");
        }
        const fileInfo = document.getElementById("vtkFileInfo");
        const fileInfoContent = document.getElementById("vtkFileInfoContent");
        if (fileInfo && fileInfoContent) {
            fileInfoContent.innerHTML = `
        <div><strong>File:</strong> ${file.name}</div>
        <div><strong>Type:</strong> ${file.type || "VTK"}</div>
        <div><strong>Size:</strong> ${(file.size / 1024).toFixed(2)} KB</div>
        ${result.mesh_info
                ? `
        <div><strong>Points:</strong> ${(result.mesh_info.n_points || 0).toLocaleString()}</div>
        <div><strong>Cells:</strong> ${(result.mesh_info.n_cells || 0).toLocaleString()}</div>
        `
                : ""}
      `;
            fileInfo.classList.remove("hidden");
        }
        const scalarFieldSelect = document.getElementById("scalarField");
        if (scalarFieldSelect && result.mesh_info) {
            scalarFieldSelect.innerHTML = "";
            (result.mesh_info.point_arrays || []).forEach((field) => {
                const option = document.createElement("option");
                option.value = `${field}@point`;
                option.textContent = `🔵 ${field} (Point Data)`;
                option.className = "point-data-option";
                scalarFieldSelect.appendChild(option);
            });
            (result.mesh_info.cell_arrays || []).forEach((field) => {
                const option = document.createElement("option");
                option.value = `${field}@cell`;
                option.textContent = `🟢 ${field} (Cell Data)`;
                option.className = "cell-data-option";
                scalarFieldSelect.appendChild(option);
            });
            const generateBtn = document.getElementById("generateContoursBtn");
            if (generateBtn) {
                generateBtn.disabled = false;
            }
        }
        showNotification("VTK file loaded successfully!", "success");
    }
    catch (error) {
        console.error("Error loading VTK file:", error);
        showNotification(`Error: ${error instanceof Error ? error.message : "Failed to load VTK file"}`, "error");
    }
}
// Check startup status
const checkStartupStatus = async () => {
    const modal = document.createElement("div");
    modal.id = "startup-modal";
    modal.className = "fixed inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center z-50";
    modal.innerHTML = `
    <div class="bg-white p-8 rounded-lg shadow-xl max-w-md w-full text-center">
      <div class="mb-4">
        <svg class="animate-spin h-10 w-10 text-blue-500 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>
      <h2 class="text-xl font-bold mb-2">System Check</h2>
      <p id="startup-message" class="text-gray-600">Checking Docker permissions...</p>
    </div>
  `;
    document.body.appendChild(modal);
    const pollStatus = async () => {
        try {
            const response = await fetch("/api/startup_status");
            const data = await response.json();
            const messageEl = document.getElementById("startup-message");
            if (messageEl)
                messageEl.textContent = data.message;
            if (data.status === "completed") {
                modal.remove();
                return;
            }
            else if (data.status === "failed") {
                if (messageEl) {
                    messageEl.className = "text-red-600";
                    messageEl.textContent = `Error: ${data.message}. Please check server logs.`;
                }
                // Don't remove modal on error, let user see it
                // Add retry button?
                const contentDiv = modal.querySelector("div > div");
                if (contentDiv && !document.getElementById("startup-retry-btn")) {
                    const retryBtn = document.createElement("button");
                    retryBtn.id = "startup-retry-btn";
                    retryBtn.className = "mt-4 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600";
                    retryBtn.textContent = "Retry (Reload Page)";
                    retryBtn.onclick = () => window.location.reload();
                    contentDiv.appendChild(retryBtn);
                }
                return;
            }
            // Continue polling
            setTimeout(pollStatus, 1000);
        }
        catch (e) {
            console.error("Error polling startup status:", e);
            setTimeout(pollStatus, 2000);
        }
    };
    await pollStatus();
};
// Clean up on page unload
window.addEventListener("beforeunload", () => {
    stopPlotUpdates();
    abortControllers.forEach((controller) => controller.abort());
    abortControllers.clear();
    requestCache.clear();
    flushOutputBuffer();
    // Force save log if pending
    if (saveLogTimer) {
        clearTimeout(saveLogTimer);
        saveLogToStorage();
    }
});
// Make functions globally available for HTML onclick handlers
// The error Uncaught ReferenceError: showNotification is not defined happens because foamflask_frontend.js is loaded as a JavaScript module. In modules, functions are not automatically global, so inline HTML event handlers (like onclick="...") cannot see them unless they are explicitly attached to the window object
window.switchPage = switchPage;
window.setCase = setCase;
window.setDockerConfig = setDockerConfig;
window.loadTutorial = loadTutorial;
window.runCommand = runCommand;
window.runFoamToVTK = runFoamToVTK;
window.refreshMeshList = refreshMeshList;
window.loadMeshVisualization = loadMeshVisualization;
window.updateMeshView = updateMeshView;
window.toggleInteractiveMode = toggleInteractiveMode;
window.setCameraView = setCameraView;
window.resetCamera = resetCamera;
window.toggleAeroPlots = toggleAeroPlots;
window.downloadPlotData = downloadPlotData;
window.loadCustomVTKFile = loadCustomVTKFile;
window.loadContourVTK = loadContourVTK;
window.generateContours = generateContoursFn;
window.downloadPlotAsPNG = downloadPlotAsPNG;
window.showNotification = showNotification;
// Attach event listeners for navigation buttons
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, attaching event listeners...');
    // Navigation buttons
    const navButtons = [
        { id: 'nav-setup', handler: () => switchPage('setup') },
        { id: 'nav-run', handler: () => switchPage('run') },
        { id: 'nav-mesh', handler: () => switchPage('mesh') },
        { id: 'nav-plots', handler: () => switchPage('plots') },
        { id: 'nav-post', handler: () => switchPage('post') }
    ];
    navButtons.forEach(({ id, handler }) => {
        const button = document.getElementById(id);
        if (button) {
            console.log(`Attaching listener to ${id}`);
            button.addEventListener('click', handler);
        }
        else {
            console.error(`Button ${id} not found`);
        }
    });
    // Load Tutorial button
    const loadTutorialBtn = document.getElementById('loadTutorialBtn');
    if (loadTutorialBtn) {
        console.log('Attaching listener to loadTutorialBtn');
        loadTutorialBtn.addEventListener('click', loadTutorial);
    }
    else {
        console.error('Load Tutorial button not found');
    }
});
//# sourceMappingURL=foamflask_frontend.js.map