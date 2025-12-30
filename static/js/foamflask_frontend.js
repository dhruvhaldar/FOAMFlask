<<<<<<< HEAD
/**
 * FOAMFlask Frontend JavaScript
 */
import { generateContours as generateContoursFn } from "./frontend/isosurface.js";
// Utility functions
export const getElement = (id) => {
    if (typeof document === 'undefined')
        return null; // Guard for Node env in tests
    return document.getElementById(id);
};
export const getErrorMessage = (error) => {
    if (error instanceof Error)
        return error.message;
    return typeof error === "string" ? error : "Unknown error";
};
// Exporting helper functions for testing purposes
export const formatDate = (timestamp) => {
    return new Date(timestamp).toLocaleString();
};
export const isSafeCommand = (cmd) => {
    const dangerousPatterns = [';', '&', '|', '`', '$', '(', ')', '<', '>', '"', "'", '%'];
    return !dangerousPatterns.some(char => cmd.includes(char));
};
// Clear Console Log
const clearLog = () => {
    const outputDiv = document.getElementById("output");
    if (outputDiv) {
        outputDiv.innerHTML = "";
        try {
            localStorage.removeItem(CONSOLE_LOG_KEY);
        }
        catch (e) {
            // Ignore local storage errors
        }
        outputBuffer.length = 0; // Clear buffer
        showNotification("Console log cleared", "info", 2000);
    }
};
// Copy Console Log to Clipboard
const copyLogToClipboard = () => {
    const outputDiv = document.getElementById("output");
    if (!outputDiv)
        return;
    // Get text content (strip HTML tags)
    // innerText preserves newlines better than textContent for visual layout
    const text = outputDiv.innerText;
    if (!text) {
        showNotification("Log is empty", "info", 2000);
        return;
    }
    // Use navigator.clipboard if available (requires secure context)
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification("Log copied to clipboard", "success", 2000);
        }).catch((err) => {
            console.error("Failed to copy log via navigator.clipboard:", err);
            // Fallback
            fallbackCopyText(text);
        });
    }
    else {
        fallbackCopyText(text);
    }
};
const fallbackCopyText = (text) => {
    try {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        // Ensure it's not visible but part of DOM
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        textArea.style.top = "0";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);
        if (successful) {
            showNotification("Log copied to clipboard", "success", 2000);
        }
        else {
            showNotification("Failed to copy log", "error");
        }
    }
    catch (err) {
        console.error("Fallback copy failed:", err);
        showNotification("Failed to copy log", "error");
    }
};
// Storage for Console Log
const CONSOLE_LOG_KEY = "foamflask_console_log";
// Global state
let caseDir = "";
let dockerImage = "";
let openfoamVersion = "";
let activeCase = "";
// Page management
let currentPage = "setup";
// Mesh visualization state
let currentMeshPath = null;
let availableMeshes = [];
let isInteractiveMode = false;
// Geometry State
let selectedGeometry = null;
// Notification management
let notificationId = 0;
let lastErrorNotificationTime = 0;
const ERROR_NOTIFICATION_COOLDOWN = 5 * 60 * 1000;
// Plotting variables
let plotUpdateInterval = null;
let plotsVisible = true;
=======
let caseDir = "";        // will be fetched from server on load
let dockerImage = "";    // from server
let openfoamVersion = ""; // from server

// Page management
let currentPage = 'setup';

// Notification management
let notificationId = 0;

// Plotting variables and theme
let plotUpdateInterval = null;
let plotsVisible = true; // Set to true by default to show plots
>>>>>>> origin/dev_trame
let aeroVisible = false;
let isUpdatingPlots = false;
let pendingPlotUpdate = false;
let plotsInViewport = true;
<<<<<<< HEAD
let isFirstPlotLoad = true;
// Request management
let abortControllers = new Map();
let requestCache = new Map();
const CACHE_DURATION = 1000;
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
// Colors
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
const lineStyle = { width: 2, opacity: 0.9 };
const createBoldTitle = (text) => ({
    text: `<b>${text}</b>`,
    font: { ...plotLayout.font, size: 22 },
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
// Helper: Save current legend visibility
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
const downloadPlotData = (plotId, filename) => {
    const plotDiv = document.getElementById(plotId);
    if (!plotDiv || !plotDiv.data)
        return;
    const traces = plotDiv.data;
    traces.forEach((trace, index) => {
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
// Page Switching
const switchPage = (pageName) => {
    console.log(`switchPage called with: ${pageName}`);
    const pages = ["setup", "geometry", "meshing", "visualizer", "run", "plots", "post"];
    pages.forEach((page) => {
        const pageElement = document.getElementById(`page-${page}`);
        const navButton = document.getElementById(`nav-${page}`);
        if (pageElement)
            pageElement.classList.add("hidden");
        if (navButton) {
            navButton.classList.remove("bg-blue-500", "text-white");
            navButton.classList.add("text-gray-700", "hover:bg-gray-100");
            navButton.removeAttribute("aria-current");
        }
    });
    const selectedPage = document.getElementById(`page-${pageName}`);
    const selectedNav = document.getElementById(`nav-${pageName}`);
    if (selectedPage)
        selectedPage.classList.remove("hidden");
    if (selectedNav) {
        selectedNav.classList.remove("text-gray-700", "hover:bg-gray-100");
        selectedNav.classList.add("bg-blue-500", "text-white");
        selectedNav.setAttribute("aria-current", "page");
    }
    // Auto-refresh lists based on page
    switch (pageName) {
        case "geometry":
            refreshGeometryList();
            break;
        case "meshing":
            refreshGeometryList().then(() => {
                const shmSelect = document.getElementById("shmStlSelect");
                const geoSelect = document.getElementById("geometrySelect");
                if (shmSelect && geoSelect) {
                    shmSelect.innerHTML = geoSelect.innerHTML;
                }
            });
            break;
        case "visualizer":
            const visualizerContainer = document.getElementById("page-visualizer");
            if (visualizerContainer && !visualizerContainer.hasAttribute("data-initialized")) {
                visualizerContainer.setAttribute("data-initialized", "true");
                refreshMeshList();
            }
            break;
        case "plots":
            const plotsContainer = document.getElementById("plotsContainer");
            if (plotsContainer) {
                plotsContainer.classList.remove("hidden");
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
        case "post":
            const postContainer = document.getElementById("page-post");
            if (postContainer && !postContainer.hasAttribute("data-initialized")) {
                postContainer.setAttribute("data-initialized", "true");
                refreshPostList();
            }
            break;
    }
};
// Show notification
const showNotification = (message, type, duration = 5000) => {
    // If a notification with the same message already exists, do not show another one
    // This prevents spamming the user with the same message
    if (document.querySelector(`.notification .message-slot[data-message="${message}"]`)) {
        return null;
    }
    const container = document.getElementById("notificationContainer");
    const template = document.getElementById("notification-template");
    if (!container || !template)
        return null;
    const id = ++notificationId;
    const clone = template.content.cloneNode(true);
    const notification = clone.querySelector(".notification");
    if (!notification)
        return null;
    notification.id = `notification-${id}`;
    // Set ARIA role for accessibility
    if (type === "error" || type === "warning") {
        notification.setAttribute("role", "alert");
    }
    else {
        notification.setAttribute("role", "status");
    }
    // Set colors
    const colors = {
        success: "bg-green-500 text-white",
        error: "bg-red-500 text-white",
        warning: "bg-yellow-500 text-white",
        info: "bg-blue-500 text-white",
    };
    notification.className += ` ${colors[type]}`;
    // Set icon and message safely
    const icons = { success: "✓", error: "✗", warning: "⚠", info: "ℹ" };
    const iconSlot = notification.querySelector(".icon-slot");
    const messageSlot = notification.querySelector(".message-slot");
    if (iconSlot)
        iconSlot.textContent = icons[type];
    if (messageSlot) {
        messageSlot.textContent = message;
        // Add data attribute to help with duplicate detection
        messageSlot.setAttribute("data-message", message);
    }
    // Handle duration and progress bar
    if (duration > 0) {
        const progressBar = notification.querySelector(".progress-bar");
        if (progressBar) {
            progressBar.classList.remove("hidden");
            progressBar.style.width = "100%";
            progressBar.style.transition = `width ${duration}ms linear`;
            // Trigger reflow to ensure transition works
            requestAnimationFrame(() => {
                progressBar.style.width = "0%";
            });
        }
        // Countdown logic
        // Add fade-out class 300ms before removal
        const fadeTime = Math.max(0, duration - 300);
        // Timer for fade out animation
        const fadeTimer = setTimeout(() => {
            notification.classList.add("fade-out");
        }, fadeTime);
        // Timer for actual removal
        const countdownInterval = setTimeout(() => {
            removeNotification(id);
        }, duration);
        notification.dataset.timerId = countdownInterval.toString();
        notification.dataset.fadeTimerId = fadeTimer.toString();
    }
    // Setup close button for all notifications
    const closeBtn = notification.querySelector(".close-btn");
    if (closeBtn) {
        closeBtn.onclick = (e) => {
            e.stopPropagation();
            removeNotification(id);
        };
    }
    container.appendChild(notification);
    return id;
};
const removeNotification = (id) => {
    const notification = document.getElementById(`notification-${id}`);
    if (notification) {
        if (notification.dataset.timerId)
            clearTimeout(parseInt(notification.dataset.timerId, 10));
        if (notification.dataset.fadeTimerId)
            clearTimeout(parseInt(notification.dataset.fadeTimerId, 10));
        // Ensure fade-out class is present for manual dismissals
        notification.classList.add("fade-out");
        // Wait for animation then remove
        setTimeout(() => notification.remove(), 300);
    }
};
// Network
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
// Logging
const appendOutput = (message, type) => {
    outputBuffer.push({ message, type });
    // ⚡ Bolt Optimization: Throttle updates to ~30fps (32ms) instead of debouncing
    if (!outputFlushTimer) {
        outputFlushTimer = setTimeout(flushOutputBuffer, 32);
    }
};
const flushOutputBuffer = () => {
    if (outputBuffer.length === 0) {
        outputFlushTimer = null;
        return;
    }
    const container = document.getElementById("output");
    if (!container) {
        outputFlushTimer = null;
        return;
    }
    // ⚡ Bolt Optimization: Check scroll position BEFORE appending to avoid layout thrashing
    // Check if user is near bottom (within 50px tolerance)
    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight <= 50;
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
    // Only force scroll if user was already at the bottom
    if (isAtBottom) {
        container.scrollTop = container.scrollHeight;
    }
    outputBuffer.length = 0;
    outputFlushTimer = null;
    // Save to LocalStorage (Debounced)
    saveLogDebounced();
};
// Setup Functions
const setCase = async () => {
    try {
        caseDir = document.getElementById("caseDir").value;
        const response = await fetch("/set_case", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseDir }) });
        if (!response.ok)
            throw new Error();
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
        refreshCaseList();
    }
    catch (e) {
        console.error(e);
        showNotification("Failed to set case directory", "error");
    }
};
const setDockerConfig = async (image, version) => {
    try {
        dockerImage = image;
        openfoamVersion = version;
        const response = await fetch("/set_docker_config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ dockerImage, openfoamVersion }) });
        if (!response.ok)
            throw new Error();
        const data = await response.json();
        dockerImage = data.dockerImage;
        openfoamVersion = data.openfoamVersion;
        const openfoamRootInput = document.getElementById("openfoamRoot");
        if (openfoamRootInput instanceof HTMLInputElement) {
            openfoamRootInput.value = `${dockerImage} OpenFOAM ${openfoamVersion}`;
        }
        showNotification("Docker config updated", "success");
    }
    catch (e) {
        showNotification("Failed to set Docker config", "error");
    }
};
const loadTutorial = async () => {
    const btn = document.getElementById("loadTutorialBtn");
    const originalText = btn ? btn.innerHTML : "Import Tutorial";
    try {
        if (btn) {
            btn.disabled = true;
            btn.setAttribute("aria-busy", "true");
            btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Importing...`;
        }
        const tutorialSelect = document.getElementById("tutorialSelect");
        const selected = tutorialSelect.value;
        if (selected)
            localStorage.setItem("lastSelectedTutorial", selected);
        showNotification("Importing tutorial...", "info");
        const response = await fetch("/load_tutorial", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tutorial: selected }) });
        if (!response.ok)
            throw new Error();
        const data = await response.json();
        if (data.output) {
            data.output.split("\n").forEach((line) => {
                if (line.trim())
                    appendOutput(line.trim(), "info");
            });
        }
        showNotification("Tutorial imported", "success");
        await refreshCaseList();
        const importedName = selected.split('/').pop();
        if (importedName) {
            selectCase(importedName);
            const select = document.getElementById("caseSelect");
            if (select)
                select.value = importedName;
        }
    }
    catch (e) {
        showNotification("Failed to load tutorial", "error");
    }
    finally {
        if (btn) {
            btn.disabled = false;
            btn.removeAttribute("aria-busy");
            btn.innerHTML = originalText;
        }
    }
};
// Toggle Section Visibility
const toggleSection = (id) => {
    const section = document.getElementById(id);
    const toggleIcon = document.getElementById(`${id}Toggle`);
    if (!section || !toggleIcon)
        return;
    const isHidden = section.classList.contains("hidden");
    if (isHidden) {
        section.classList.remove("hidden");
        toggleIcon.textContent = "▼";
        toggleIcon.classList.remove("-rotate-90");
        // If it's a button (accessible version), update aria-expanded
        const toggleBtn = toggleIcon.parentElement?.tagName === "BUTTON" ? toggleIcon.parentElement : null;
        if (toggleBtn)
            toggleBtn.setAttribute("aria-expanded", "true");
    }
    else {
        section.classList.add("hidden");
        toggleIcon.textContent = "▶";
        toggleIcon.classList.add("-rotate-90");
        // If it's a button (accessible version), update aria-expanded
        const toggleBtn = toggleIcon.parentElement?.tagName === "BUTTON" ? toggleIcon.parentElement : null;
        if (toggleBtn)
            toggleBtn.setAttribute("aria-expanded", "false");
    }
};
// Case Management
const refreshCaseList = async () => {
    try {
        const response = await fetch("/api/cases/list");
        const data = await response.json();
        const select = document.getElementById("caseSelect");
        if (select && data.cases) {
            const current = select.value;
            select.innerHTML = '<option value="">-- Select a Case --</option>';
            data.cases.forEach(c => {
                const opt = document.createElement("option");
                opt.value = c;
                opt.textContent = c;
                select.appendChild(opt);
            });
            if (current && data.cases.includes(current))
                select.value = current;
            else if (activeCase && data.cases.includes(activeCase))
                select.value = activeCase;
        }
    }
    catch (e) {
        console.error(e);
    }
};
const selectCase = (val) => {
    activeCase = val;
    localStorage.setItem("lastSelectedCase", val);
};
const createNewCase = async () => {
    const caseName = document.getElementById("newCaseName").value;
    if (!caseName) {
        showNotification("Enter case name", "warning");
        return;
    }
    const btn = document.getElementById("createCaseBtn");
    const originalText = btn ? btn.innerHTML : "Create Case";
    if (btn) {
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
        btn.innerHTML = `<svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Creating...`;
    }
    showNotification(`Creating case ${caseName}...`, "info");
    try {
        const response = await fetch("/api/case/create", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName }) });
        const data = await response.json();
        if (data.success) {
            showNotification("Case created", "success");
            document.getElementById("newCaseName").value = "";
            await refreshCaseList();
            selectCase(caseName);
            const select = document.getElementById("caseSelect");
            if (select)
                select.value = caseName;
        }
        else {
            showNotification(data.message || "Failed", "error");
        }
    }
    catch (e) {
        showNotification("Error creating case", "error");
    }
    finally {
        if (btn) {
            btn.disabled = false;
            btn.removeAttribute("aria-busy");
            btn.innerHTML = originalText;
        }
    }
};
const runCommand = async (cmd, btnElement) => {
    if (!cmd) {
        showNotification("No command specified", "error");
        return;
    }
    // Use tutorial select if activeCase is not set, or prefer tutorial select for "Run" tab
    const selectedTutorial = document.getElementById("tutorialSelect")?.value || activeCase;
    if (!selectedTutorial) {
        showNotification("Select case and command", "error");
        return;
    }
    let originalText = "";
    const btn = btnElement;
    if (btn) {
        originalText = btn.innerHTML;
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
        btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Running...`;
    }
    try {
        showNotification(`Running ${cmd}...`, "info");
        const response = await fetch("/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseDir, tutorial: selectedTutorial, command: cmd }) });
        if (!response.ok)
            throw new Error();
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        const read = async () => {
            const { done, value } = (await reader?.read()) || { done: true, value: undefined };
            if (done) {
                showNotification("Simulation completed successfully", "success");
                flushOutputBuffer();
                return;
            }
            const text = decoder.decode(value);
            text.split("\n").forEach(line => {
                if (line.trim()) {
                    const type = /error/i.test(line) ? "stderr" : "stdout";
                    appendOutput(line, type);
                }
            });
            await read();
        };
        await read();
    }
    catch (e) {
        console.error(e);
        showNotification("Error running command", "error");
    }
    finally {
        if (btn) {
            btn.disabled = false;
            btn.removeAttribute("aria-busy");
            btn.innerHTML = originalText;
        }
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
        if (btn)
            btn.textContent = "Hide Plots";
        aeroBtn?.classList.remove("hidden");
        startPlotUpdates();
        setupIntersectionObserver();
    }
    else {
        container?.classList.add("hidden");
        if (btn)
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
        if (btn)
            btn.textContent = "Hide Aero Plots";
        updateAeroPlots();
    }
    else {
        container?.classList.add("hidden");
        if (btn)
            btn.textContent = "Show Aero Plots";
    }
};
const startPlotUpdates = () => {
    if (plotUpdateInterval)
        return;
    plotUpdateInterval = setInterval(() => {
        // ⚡ Bolt Optimization: Pause polling when tab is hidden to save resources
        if (document.hidden)
            return;
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
        if (data.error || !data.time || data.time.length === 0) {
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
const updateAeroPlots = async (preFetchedData) => {
    const selectedTutorial = document.getElementById("tutorialSelect")?.value;
    if (!selectedTutorial)
        return;
    try {
        let data = preFetchedData;
        // ⚡ Bolt Optimization: Use pre-fetched data if available to save a network request
        if (!data) {
            const response = await fetch(`/api/plot_data?tutorial=${encodeURIComponent(selectedTutorial)}`);
            data = await response.json();
        }
        if (data.error)
            return;
        // Cp plot
        if (Array.isArray(data.p) &&
            Array.isArray(data.time) &&
            data.p.length === data.time.length &&
            data.p.length > 0) {
            const pinf = 101325;
            const rho = 1.225;
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
        // ⚡ Bolt Optimization: Pass the already fetched data to avoid redundant request
        if (aeroVisible)
            updatePromises.push(updateAeroPlots(data));
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
// Geometry Functions
const refreshGeometryList = async () => {
    if (!activeCase)
        return;
    try {
        const response = await fetch(`/api/geometry/list?caseName=${encodeURIComponent(activeCase)}`);
        const data = await response.json();
        if (data.success) {
            const select = document.getElementById("geometrySelect");
            if (select) {
                select.innerHTML = "";
                data.files.forEach((f) => {
                    const opt = document.createElement("option");
                    opt.value = f;
                    opt.textContent = f;
                    select.appendChild(opt);
                });
            }
        }
    }
    catch (e) {
        console.error(e);
    }
};
const uploadGeometry = async () => {
    const input = document.getElementById("geometryUpload");
    const btn = document.getElementById("uploadGeometryBtn");
    const file = input?.files?.[0];
    if (!file || !activeCase)
        return;
    // UX: Loading state
    const originalText = btn ? btn.innerHTML : "Upload";
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Uploading...`;
    }
    const formData = new FormData();
    formData.append("file", file);
    formData.append("caseName", activeCase);
    try {
        const response = await fetch("/api/geometry/upload", { method: "POST", body: formData });
        if (!response.ok)
            throw new Error("Upload failed");
        showNotification("Geometry uploaded successfully", "success");
        input.value = "";
        refreshGeometryList();
    }
    catch (e) {
        showNotification("Failed to upload geometry", "error");
    }
    finally {
        // Restore button state
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
};
const deleteGeometry = async () => {
    const filename = document.getElementById("geometrySelect")?.value;
    if (!filename || !activeCase)
        return;
    if (!confirm("Delete?"))
        return;
    try {
        await fetch("/api/geometry/delete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, filename }) });
        refreshGeometryList();
    }
    catch (e) {
        showNotification("Failed", "error");
    }
};
const loadGeometryView = async () => {
    const filename = document.getElementById("geometrySelect")?.value;
    if (!filename || !activeCase)
        return;
    showNotification("Loading...", "info");
    try {
        const res = await fetch("/api/geometry/view", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, filename }) });
        if (res.ok) {
            const html = await res.text();
            document.getElementById("geometryInteractive").srcdoc = html;
            document.getElementById("geometryPlaceholder")?.classList.add("hidden");
        }
    }
    catch (e) {
        showNotification("Failed", "error");
    }
    // Info
    try {
        const res = await fetch("/api/geometry/info", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, filename }) });
        const info = await res.json();
        if (info.success) {
            const div = document.getElementById("geometryInfoContent");
            if (div) {
                const b = info.bounds;
                const fmt = (n) => n.toFixed(3);
                const dx = (b[1] - b[0]).toFixed(3);
                const dy = (b[3] - b[2]).toFixed(3);
                const dz = (b[5] - b[4]).toFixed(3);
                const setText = (id, text) => {
                    const el = document.getElementById(id);
                    if (el)
                        el.textContent = text;
                };
                setText("geo-bound-x-min", fmt(b[0]));
                setText("geo-bound-x-max", fmt(b[1]));
                setText("geo-bound-x-len", dx);
                setText("geo-bound-y-min", fmt(b[2]));
                setText("geo-bound-y-max", fmt(b[3]));
                setText("geo-bound-y-len", dy);
                setText("geo-bound-z-min", fmt(b[4]));
                setText("geo-bound-z-max", fmt(b[5]));
                setText("geo-bound-z-len", dz);
            }
            document.getElementById("geometryInfo")?.classList.remove("hidden");
        }
    }
    catch (e) { }
};
// Meshing Functions
const fillBoundsFromGeometry = async () => {
    // simplified for brevity
    const filename = document.getElementById("shmStlSelect")?.value;
    if (!filename || !activeCase)
        return;
    try {
        const res = await fetch("/api/geometry/info", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, filename }) });
        const info = await res.json();
        if (info.success) {
            const b = info.bounds;
            const p = 0.1;
            const dx = b[1] - b[0];
            const dy = b[3] - b[2];
            const dz = b[5] - b[4];
            document.getElementById("bmMin").value = `${(b[0] - dx * p).toFixed(2)} ${(b[2] - dy * p).toFixed(2)} ${(b[4] - dz * p).toFixed(2)}`;
            document.getElementById("bmMax").value = `${(b[1] + dx * p).toFixed(2)} ${(b[3] + dy * p).toFixed(2)} ${(b[5] + dz * p).toFixed(2)}`;
        }
    }
    catch (e) { }
};
const generateBlockMeshDict = async () => {
    if (!activeCase)
        return;
    const minVal = document.getElementById("bmMin").value.trim().split(/\s+/).map(Number);
    const maxVal = document.getElementById("bmMax").value.trim().split(/\s+/).map(Number);
    const cells = document.getElementById("bmCells").value.trim().split(/\s+/).map(Number);
    const grading = document.getElementById("bmGrading").value.trim().split(/\s+/).map(Number);
    try {
        await fetch("/api/meshing/blockMesh/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, config: { min_point: minVal, max_point: maxVal, cells, grading } }) });
        showNotification("Generated", "success");
    }
    catch (e) { }
};
const generateSnappyHexMeshDict = async () => {
    const filename = document.getElementById("shmStlSelect")?.value;
    if (!activeCase || !filename)
        return;
    const level = parseInt(document.getElementById("shmLevel").value);
    const location = document.getElementById("shmLocation").value.trim().split(/\s+/).map(Number);
    try {
        await fetch("/api/meshing/snappyHexMesh/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, config: { stl_filename: filename, refinement_level: level, location_in_mesh: location } }) });
        showNotification("Generated", "success");
    }
    catch (e) { }
};
const runMeshingCommand = async (cmd, btnElement) => {
    if (!activeCase)
        return;
    const btn = btnElement;
    let originalText = "";
    if (btn) {
        originalText = btn.innerHTML;
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
        btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Running...`;
    }
    showNotification(`Running ${cmd}`, "info");
    try {
        const res = await fetch("/api/meshing/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, command: cmd }) });
        const data = await res.json();
        if (data.success) {
            showNotification("Meshing completed successfully", "success");
            const div = document.getElementById("meshingOutput");
            if (div)
                div.innerText += `\n${data.output}`;
        }
    }
    catch (e) {
        showNotification("Meshing failed", "error");
    }
    finally {
        if (btn) {
            btn.disabled = false;
            btn.removeAttribute("aria-busy");
            btn.innerHTML = originalText;
        }
    }
};
// Visualizer
const runFoamToVTK = async (btnElement) => {
    if (!activeCase) {
        showNotification("Please select a case first", "warning");
        return;
    }
    const btn = btnElement;
    let originalText = "";
    if (btn) {
        originalText = btn.innerHTML;
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
        btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Running...`;
    }
    showNotification("Running foamToVTK...", "info");
    try {
        const response = await fetch("/run_foamtovtk", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tutorial: activeCase, caseDir: caseDir }) // passing caseDir global var
        });
        if (!response.ok)
            throw new Error("Failed to start foamToVTK");
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        const read = async () => {
            const { done, value } = (await reader?.read()) || { done: true, value: undefined };
            if (done) {
                showNotification("foamToVTK completed", "success");
                flushOutputBuffer();
                refreshMeshList();
                return;
            }
            const text = decoder.decode(value);
            text.split("\n").forEach(line => {
                if (line.trim()) {
                    // Simply append to output, maybe parse for errors if needed
                    const type = /error/i.test(line) ? "stderr" : "stdout";
                    appendOutput(line, "stdout");
                }
            });
            await read();
        };
        await read();
    }
    catch (e) {
        console.error(e);
        showNotification("Error running foamToVTK", "error");
    }
    finally {
        if (btn) {
            btn.disabled = false;
            btn.removeAttribute("aria-busy");
            btn.innerHTML = originalText;
        }
    }
};
const refreshMeshList = async () => {
    if (!activeCase) {
        showNotification("No active case selected to list meshes", "warning", 3000);
        return;
    }
    try {
        const res = await fetch(`/api/available_meshes?tutorial=${encodeURIComponent(activeCase)}`);
        const data = await res.json();
        const select = document.getElementById("meshSelect");
        if (select && data.meshes) {
            select.innerHTML = '<option value="">Select</option>';
            data.meshes.forEach((m) => {
                const opt = document.createElement("option");
                opt.value = m.path;
                opt.textContent = m.name;
                select.appendChild(opt);
            });
        }
    }
    catch (e) {
        console.error("Error refreshing mesh list:", e);
        showNotification("Failed to refresh mesh list", "error");
    }
};
const loadMeshVisualization = async () => {
    const path = document.getElementById("meshSelect")?.value;
    const btn = document.getElementById("loadMeshBtn");
    if (!path)
        return;
    // UX: Loading state
    const originalText = btn ? btn.innerHTML : "Load Mesh";
    if (btn) {
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
        btn.innerHTML = `<svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Loading...`;
    }
    currentMeshPath = path;
    try {
        await updateMeshView();
    }
    finally {
        // Restore button state
        if (btn) {
            btn.disabled = false;
            btn.removeAttribute("aria-busy");
            btn.innerHTML = originalText;
        }
    }
};
const updateMeshView = async () => {
    if (!currentMeshPath)
        return;
    const showEdges = document.getElementById("showEdges")?.checked ?? true;
    const color = document.getElementById("meshColor")?.value ?? "lightblue";
    const cameraPosition = document.getElementById("cameraPosition")?.value || null;
    try {
        const res = await fetch("/api/mesh_screenshot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                file_path: currentMeshPath,
                width: 800,
                height: 600,
                show_edges: showEdges,
                color: color,
                camera_position: cameraPosition
            })
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById("meshImage").src = `data:image/png;base64,${data.image}`;
            document.getElementById("meshImage")?.classList.remove("hidden");
            document.getElementById("meshPlaceholder")?.classList.add("hidden");
            document.getElementById("meshControls")?.classList.remove("hidden");
            document.getElementById("meshActionButtons")?.classList.add("hidden");
        }
    }
    catch (e) { }
};
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
async function refreshInteractiveViewer(successMessage = "Interactive mode enabled") {
    const meshInteractive = document.getElementById("meshInteractive");
    const meshImage = document.getElementById("meshImage");
    const meshPlaceholder = document.getElementById("meshPlaceholder");
    const toggleBtn = document.getElementById("toggleInteractiveBtn");
    const cameraControl = document.getElementById("cameraPosition");
    const updateBtn = document.getElementById("updateViewBtn");
    if (!meshInteractive || !meshImage || !meshPlaceholder || !toggleBtn || !cameraControl || !updateBtn)
        return;
    showNotification("Loading interactive viewer...", "info");
    try {
        const showEdgesInput = document.getElementById("showEdges");
        const colorInput = document.getElementById("meshColor");
        if (!showEdgesInput || !colorInput) {
            showNotification("Required mesh controls not found", "error");
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
        cameraControl.parentElement?.classList.add("hidden");
        updateBtn.classList.add("hidden");
        document.getElementById("interactiveModeHint")?.classList.remove("hidden");
        showNotification(successMessage, "success", 8000);
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
        cameraControl.parentElement?.classList.remove("hidden");
        updateBtn.classList.remove("hidden");
        document.getElementById("interactiveModeHint")?.classList.add("hidden");
        meshInteractive.classList.add("hidden");
        meshImage.classList.remove("hidden");
    }
}
async function onMeshParamChange() {
    if (isInteractiveMode) {
        await refreshInteractiveViewer("Interactive mode updated");
    }
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
        await refreshInteractiveViewer("Interactive mode enabled");
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
        cameraControl.parentElement?.classList.remove("hidden");
        updateBtn.classList.remove("hidden");
        document.getElementById("interactiveModeHint")?.classList.add("hidden");
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
// Post Processing
const refreshPostList = async () => {
    refreshPostListVTK();
};
const refreshPostListVTK = async () => {
    if (!activeCase)
        return;
    try {
        const res = await fetch(`/api/available_meshes?tutorial=${encodeURIComponent(activeCase)}`);
        const data = await res.json();
        const select = document.getElementById("vtkFileSelect");
        if (select && data.meshes) {
            select.innerHTML = '<option value="">Select</option>';
            data.meshes.forEach((m) => {
                const opt = document.createElement("option");
                opt.value = m.path;
                opt.textContent = m.name;
                select.appendChild(opt);
            });
        }
    }
    catch (e) { }
};
const runPostOperation = async (operation) => {
    // Stub
};
const loadCustomVTKFile = async () => { };
const loadContourVTK = async () => { };
// Check startup status
const checkStartupStatus = async () => {
    const modal = document.createElement("div");
    modal.id = "startup-modal";
    modal.className = "fixed inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center z-50";
    modal.innerHTML = `
    <div class="bg-white p-8 rounded-lg shadow-xl max-w-md w-full text-center">
      <div class="mb-4"><svg class="animate-spin h-10 w-10 text-blue-500 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg></div>
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
                return;
            }
            setTimeout(pollStatus, 1000);
        }
        catch (e) {
            setTimeout(pollStatus, 2000);
        }
    };
    await pollStatus();
};
// Initialize
window.onload = async () => {
    try {
        await checkStartupStatus();
    }
    catch (e) {
        console.error(e);
    }
    const outputDiv = document.getElementById("output");
    if (outputDiv) {
        // Restore Log
        const savedLog = localStorage.getItem(CONSOLE_LOG_KEY);
        if (savedLog) {
            outputDiv.innerHTML = savedLog;
            outputDiv.scrollTop = outputDiv.scrollHeight;
        }
    }
    try {
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
        // Load Cases
        await refreshCaseList();
        const savedCase = localStorage.getItem("lastSelectedCase");
        if (savedCase) {
            const select = document.getElementById("caseSelect");
            let exists = false;
            for (let i = 0; i < select.options.length; i++) {
                if (select.options[i].value === savedCase) {
                    exists = true;
                    break;
                }
            }
            if (exists) {
                select.value = savedCase;
                activeCase = savedCase;
            }
        }
        // Check if we need to restore any plot state or similar
        // ...
    }
    catch (e) {
        console.error(e);
    }
};
// Exports
window.switchPage = switchPage;
window.setCase = setCase;
window.setDockerConfig = setDockerConfig;
window.loadTutorial = loadTutorial;
window.createNewCase = createNewCase;
window.selectCase = selectCase;
window.refreshCaseList = refreshCaseList;
window.uploadGeometry = uploadGeometry;
window.deleteGeometry = deleteGeometry;
window.loadGeometryView = loadGeometryView;
window.fillBoundsFromGeometry = fillBoundsFromGeometry;
window.generateBlockMeshDict = generateBlockMeshDict;
window.generateSnappyHexMeshDict = generateSnappyHexMeshDict;
window.runMeshingCommand = runMeshingCommand;
window.refreshMeshList = refreshMeshList;
window.loadMeshVisualization = loadMeshVisualization;
window.updateMeshView = updateMeshView;
window.runFoamToVTK = runFoamToVTK;
window.refreshPostList = refreshPostList;
window.toggleAeroPlots = toggleAeroPlots;
window.runCommand = runCommand;
window.toggleInteractiveMode = toggleInteractiveMode;
window.setCameraView = setCameraView;
window.resetCamera = resetCamera;
window.downloadPlotData = downloadPlotData;
window.loadCustomVTKFile = loadCustomVTKFile;
window.loadContourVTK = loadContourVTK;
window.generateContours = generateContoursFn;
window.downloadPlotAsPNG = downloadPlotAsPNG;
window.showNotification = showNotification;
window.runPostOperation = runPostOperation;
window.clearLog = clearLog;
window.copyLogToClipboard = copyLogToClipboard;
window.togglePlots = togglePlots;
window.toggleSection = toggleSection;
const init = () => {
    const navButtons = [
        { id: 'nav-setup', handler: () => switchPage('setup') },
        { id: 'nav-run', handler: () => switchPage('run') },
        { id: 'nav-geometry', handler: () => switchPage('geometry') },
        { id: 'nav-meshing', handler: () => switchPage('meshing') },
        { id: 'nav-visualizer', handler: () => switchPage('visualizer') },
        { id: 'nav-plots', handler: () => switchPage('plots') },
        { id: 'nav-post', handler: () => switchPage('post') }
    ];
    navButtons.forEach(({ id, handler }) => {
        const button = document.getElementById(id);
        if (button)
            button.addEventListener('click', handler);
    });
    const loadTutorialBtn = document.getElementById('loadTutorialBtn');
    if (loadTutorialBtn)
        loadTutorialBtn.addEventListener('click', loadTutorial);
    // ⚡ Bolt Optimization: Resume updates immediately when tab becomes visible
    document.addEventListener("visibilitychange", () => {
        if (!document.hidden && plotsVisible && plotsInViewport) {
            if (!isUpdatingPlots) {
                updatePlots();
            }
            else {
                pendingPlotUpdate = true;
            }
        }
    });
    // Persist Tutorial Selection
    const tutorialSelect = document.getElementById('tutorialSelect');
    if (tutorialSelect) {
        // Restore
        const savedTutorial = localStorage.getItem('lastSelectedTutorial');
        if (savedTutorial) {
            // Check if option exists
            let exists = false;
            for (let i = 0; i < tutorialSelect.options.length; i++) {
                if (tutorialSelect.options[i].value === savedTutorial) {
                    exists = true;
                    break;
                }
            }
            if (exists) {
                tutorialSelect.value = savedTutorial;
            }
        }
        // Save on change
        tutorialSelect.addEventListener('change', (e) => {
            const target = e.target;
            localStorage.setItem('lastSelectedTutorial', target.value);
        });
    }
    // Interactive Mode Event Listeners
    const meshColorSelect = document.getElementById("meshColor");
    if (meshColorSelect) {
        meshColorSelect.addEventListener("change", onMeshParamChange);
    }
    const showEdgesCheck = document.getElementById("showEdges");
    if (showEdgesCheck) {
        showEdgesCheck.addEventListener("change", onMeshParamChange);
    }
};
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
}
else {
    init();
}
//# sourceMappingURL=foamflask_frontend.js.map
=======

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
        // Add any mesh-specific initialization here
        console.log('Mesh page initialized');

        // Add click handler for the Load Mesh button
        const loadMeshBtn = meshContainer.querySelector('button');
        if (loadMeshBtn) {
          loadMeshBtn.addEventListener('click', function() {
            showNotification('Loading mesh visualization...', 'info');
            // Add your mesh loading logic here
          });
        }
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

// --- Mesh Viewer Functions ---

// Initialize mesh viewer when page loads
document.addEventListener('DOMContentLoaded', () => {
  // Add event listeners for mesh viewer buttons
  const loadMeshBtn = document.getElementById('loadMeshBtn');
  const resetCameraBtn = document.getElementById('resetCameraBtn');
  const isometricViewBtn = document.getElementById('isometricViewBtn');

  if (loadMeshBtn) {
    loadMeshBtn.addEventListener('click', loadMeshViewer);
  }

  // These will be connected to the iframe's trame viewer after it loads
  if (resetCameraBtn) {
    resetCameraBtn.addEventListener('click', () => {
      const iframe = document.getElementById('trame-iframe');
      if (iframe && iframe.contentWindow) {
        iframe.contentWindow.postMessage({ action: 'resetCamera' }, '*');
      }
    });
  }

  if (isometricViewBtn) {
    isometricViewBtn.addEventListener('click', () => {
      const iframe = document.getElementById('trame-iframe');
      if (iframe && iframe.contentWindow) {
        iframe.contentWindow.postMessage({ action: 'isometricView' }, '*');
      }
    });
  }

  // Listen for messages from the iframe
  window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'trame:ready') {
      // Iframe is ready, we can now communicate with it
      console.log('[FOAMFlask] Trame viewer is ready');
    }
  });
});

// Load the mesh viewer for the current case
async function loadMeshViewer() {
  const tutorial = document.getElementById('tutorialSelect').value;
  if (!tutorial) {
    showNotification('Please select a tutorial first', 'warning');
    return;
  }

  const iframe = document.getElementById('trame-iframe');
  const placeholder = document.getElementById('mesh-placeholder');

  if (!iframe || !placeholder) return;

  try {
    // Show loading state
    placeholder.innerHTML = `
      <div class="flex flex-col items-center">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
        <p class="text-gray-600">Loading mesh viewer...</p>
      </div>
    `;

    // Set the iframe source to the trame viewer endpoint
    iframe.src = `/trame?tutorial=${encodeURIComponent(tutorial)}`;

    // When iframe loads, show it and hide the placeholder
    iframe.onload = () => {
      iframe.style.display = 'block';
      placeholder.style.display = 'none';
    };

    // Handle any errors
    iframe.onerror = () => {
      showNotification('Failed to load mesh viewer', 'error');
      placeholder.innerHTML = `
        <div class="text-center">
          <div class="text-red-500 mb-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 class="text-lg font-medium text-gray-700 mb-2">Failed to Load Mesh</h3>
          <p class="text-gray-500 mb-4">Could not load the mesh viewer. Please try again.</p>
          <button onclick="loadMeshViewer()" class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors">
            Retry
          </button>
        </div>
      `;
      placeholder.style.display = 'flex';
    };

  } catch (err) {
    console.error('[FOAMFlask] Error loading mesh viewer:', err);
    showNotification('Error loading mesh viewer', 'error');

    // Reset to default placeholder
    placeholder.innerHTML = `
      <div class="text-gray-500 mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
        </svg>
      </div>
      <h3 class="text-lg font-medium text-gray-700 mb-2">No Mesh Loaded</h3>
      <p class="text-gray-500 mb-4">Select a tutorial case to view the mesh</p>
      <button id="loadMeshBtn" class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors">
        Load Mesh from Current Case
      </button>
    `;
    placeholder.style.display = 'flex';

    // Re-attach the event listener
    const loadBtn = document.getElementById('loadMeshBtn');
    if (loadBtn) {
      loadBtn.addEventListener('click', loadMeshViewer);
    }
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
>>>>>>> origin/dev_trame
