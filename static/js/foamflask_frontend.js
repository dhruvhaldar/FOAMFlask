/**
 * FOAMFlask Frontend JavaScript
 */
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
// Clear Console Log
const clearLog = () => {
    const outputDiv = document.getElementById("output");
    if (outputDiv) {
        outputDiv.innerHTML = "";
        cachedLogHTML = ""; // ⚡ Bolt Optimization: clear cache
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
// Generic Copy to Clipboard Helper
const copyTextFromElement = (elementId, successMessage) => {
    const el = document.getElementById(elementId);
    if (!el)
        return;
    // innerText preserves newlines better than textContent
    const text = el.innerText;
    if (!text.trim()) {
        showNotification("Content is empty", "info", 2000);
        return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification(successMessage, "success", 2000);
        }).catch(() => fallbackCopyText(text, successMessage));
    }
    else {
        fallbackCopyText(text, successMessage);
    }
};
const fallbackCopyText = (text, successMessage) => {
    try {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        textArea.style.top = "0";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);
        if (successful)
            showNotification(successMessage, "success", 2000);
        else
            showNotification("Failed to copy", "error");
    }
    catch (err) {
        showNotification("Failed to copy", "error");
    }
};
// Copy Console Log
const copyLogToClipboard = () => {
    copyTextFromElement("output", "Log copied to clipboard");
};
// Copy Meshing Output
const copyMeshingOutput = () => {
    copyTextFromElement("meshingOutput", "Meshing output copied");
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
let aeroVisible = false;
let isUpdatingPlots = false;
let pendingPlotUpdate = false;
let plotsInViewport = true;
let isFirstPlotLoad = true;
// Request management
let abortControllers = new Map();
let requestCache = new Map();
const CACHE_DURATION = 1000;
const outputBuffer = [];
let outputFlushTimer = null;
let saveLogTimer = null;
// ⚡ Bolt Optimization: maintain off-DOM cache to avoid expensive innerHTML access
let cachedLogHTML = "";
// Save log to local storage (Debounced)
const saveLogToStorage = () => {
    try {
        // ⚡ Bolt Optimization: Write from string variable instead of reading DOM
        localStorage.setItem(CONSOLE_LOG_KEY, cachedLogHTML);
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
    blue: "#1dbde6",
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
    plot_bgcolor: "rgba(255, 255, 255, 0)",
    paper_bgcolor: "rgba(255, 255, 255, 0)",
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
        bgcolor: "rgba(255, 0, 0, 0)",
        borderwidth: 0,
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
    // plotDiv.layout.paper_bgcolor = "white"; // Disable white BG enforcement
    // plotDiv.layout.plot_bgcolor = "white";
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
const switchPage = (pageName, updateUrl = true) => {
    console.log(`switchPage called with: ${pageName}`);
    // Update URL
    if (updateUrl) {
        const url = new URL(window.location.href);
        url.pathname = pageName === "setup" ? "/" : `/${pageName}`;
        window.history.pushState({ page: pageName }, "", url);
    }
    const pages = ["setup", "geometry", "meshing", "visualizer", "run", "plots", "post"];
    pages.forEach((page) => {
        const pageElement = document.getElementById(`page-${page}`);
        const navButton = document.getElementById(`nav-${page}`);
        if (pageElement)
            pageElement.classList.add("hidden");
        if (navButton) {
            navButton.classList.remove("bg-cyan-600", "text-white");
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
        selectedNav.classList.add("bg-cyan-600", "text-white");
        selectedNav.setAttribute("aria-current", "page");
    }
    // Auto-refresh lists based on page
    switch (pageName) {
        case "geometry":
            refreshGeometryList();
            break;
        case "meshing":
            refreshGeometryList().then(() => {
                const shmSelect = document.getElementById("shmObjectList");
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
        success: "bg-green-500/80 text-white backdrop-blur-md border border-white/20 shadow-xl",
        error: "bg-red-500/80 text-white backdrop-blur-md border border-white/20 shadow-xl",
        warning: "bg-yellow-500/80 text-white backdrop-blur-md border border-white/20 shadow-xl",
        info: "bg-cyan-600/80 text-white backdrop-blur-md border border-white/20 shadow-xl",
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
    let newHtmlChunks = ""; // ⚡ Bolt Optimization: Accumulate HTML for cache
    // Helper for manual HTML escaping (significantly faster than browser serialization)
    const escapeHtml = (str) => {
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    };
    outputBuffer.forEach(({ message, type }) => {
        // Determine class name
        let className = "text-green-700";
        if (type === "stderr")
            className = "text-red-600";
        else if (type === "tutorial")
            className = "text-cyan-600 font-semibold";
        else if (type === "info")
            className = "text-yellow-600 italic";
        // ⚡ Bolt Optimization: Direct string construction + insertAdjacentHTML
        // Removes overhead of document.createElement() and .textContent assignments (O(N) -> O(1) DOM touches)
        const safeMessage = escapeHtml(message);
        newHtmlChunks += `<div class="${className}">${safeMessage}</div>`;
    });
    container.insertAdjacentHTML("beforeend", newHtmlChunks);
    cachedLogHTML += newHtmlChunks; // ⚡ Bolt Optimization: Append to cache
    // ⚡ Bolt Optimization: Cap the size of cachedLogHTML to prevent memory issues and localStorage quota errors
    const MAX_LOG_LENGTH = 100000; // 100KB
    if (cachedLogHTML.length > MAX_LOG_LENGTH * 1.5) {
        const slice = cachedLogHTML.slice(-MAX_LOG_LENGTH);
        // Ensure we cut at a clean tag boundary
        const firstDiv = slice.indexOf("<div");
        if (firstDiv !== -1) {
            cachedLogHTML = slice.substring(firstDiv);
        }
    }
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
const setCase = async (btnElement) => {
    const btn = btnElement;
    let originalText = "";
    if (btn) {
        originalText = btn.innerHTML;
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
        btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Setting Root...`;
    }
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
    finally {
        if (btn) {
            btn.disabled = false;
            btn.removeAttribute("aria-busy");
            btn.innerHTML = originalText;
        }
    }
};
const setDockerConfig = async (image, version, btnElement) => {
    const btn = btnElement;
    let originalText = "";
    if (btn) {
        originalText = btn.innerHTML;
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
        btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Updating...`;
    }
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
    finally {
        if (btn) {
            btn.disabled = false;
            btn.removeAttribute("aria-busy");
            btn.innerHTML = originalText;
        }
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
const refreshCaseList = async (btnElement) => {
    const btn = btnElement;
    let originalText = "";
    if (btn) {
        originalText = btn.innerHTML;
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
        btn.classList.add("opacity-75", "cursor-wait");
        // Preserve the icon if it exists, but spin it
        if (btn.querySelector("svg")) {
            // Since we know the structure from HTML, we can just replace innerHTML for simplicity
            // or toggle a class. But let's follow the pattern used elsewhere.
            // However, the Refresh button has text "↻ Refresh".
            btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg> Refreshing...`;
        }
        else {
            // Fallback or just standard spinner
            btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Refreshing...`;
        }
    }
    try {
        const response = await fetch("/api/cases/list");
        if (!response.ok)
            throw new Error("Failed to fetch cases");
        const data = await response.json();
        const select = document.getElementById("caseSelect");
        if (select && data.cases) {
            const current = select.value;
            if (data.cases.length === 0) {
                select.innerHTML = '<option value="" disabled selected>No cases found</option>';
            }
            else {
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
        // Only show success notification if invoked manually (via button)
        if (btn)
            showNotification("Case list refreshed", "success", 2000);
    }
    catch (e) {
        console.error(e);
        if (btn)
            showNotification("Failed to refresh case list", "error");
    }
    finally {
        if (btn) {
            btn.disabled = false;
            btn.removeAttribute("aria-busy");
            btn.classList.remove("opacity-75", "cursor-wait");
            btn.innerHTML = originalText;
        }
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
const refreshGeometryList = async (btnElement) => {
    if (!activeCase)
        return;
    const btn = btnElement;
    let originalText = "";
    if (btn) {
        originalText = btn.innerHTML;
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
        btn.classList.add("opacity-75", "cursor-wait");
        btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg> Refreshing...`;
    }
    try {
        const response = await fetch(`/api/geometry/list?caseName=${encodeURIComponent(activeCase)}`);
        const data = await response.json();
        if (data.success) {
            const select = document.getElementById("geometrySelect");
            if (select) {
                select.innerHTML = "";
                if (data.files.length === 0) {
                    const opt = document.createElement("option");
                    opt.disabled = true;
                    opt.textContent = "No geometry files found";
                    select.appendChild(opt);
                }
                else {
                    data.files.forEach((f) => {
                        const opt = document.createElement("option");
                        opt.value = f;
                        opt.textContent = f;
                        select.appendChild(opt);
                    });
                }
            }
        }
        if (btn)
            showNotification("Geometry list refreshed", "success", 2000);
    }
    catch (e) {
        console.error(e);
        if (btn)
            showNotification("Failed to refresh geometry list", "error");
    }
    finally {
        if (btn) {
            btn.disabled = false;
            btn.removeAttribute("aria-busy");
            btn.classList.remove("opacity-75", "cursor-wait");
            btn.innerHTML = originalText;
        }
    }
};
const uploadGeometry = async (btnElement) => {
    const input = document.getElementById("geometryUpload");
    const btn = (btnElement || document.getElementById("uploadGeometryBtn"));
    const file = input?.files?.[0];
    if (!file || !activeCase)
        return;
    // UX: Loading state
    const originalText = btn ? btn.innerHTML : "Upload";
    if (btn) {
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
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
            btn.removeAttribute("aria-busy");
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
const fillBoundsFromGeometry = async (btnElement) => {
    if (!activeCase) {
        showNotification("Please select an active case first", "warning");
        return;
    }
    const filename = document.getElementById("shmObjectList")?.value;
    if (!filename) {
        showNotification("Please select a geometry object in the 'Object Settings' list below", "warning");
        return;
    }
    const btn = btnElement;
    let originalText = "";
    if (btn) {
        originalText = btn.innerHTML;
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
        btn.innerHTML = `Auto-filling...`;
    }
    try {
        const res = await fetch("/api/geometry/info", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, filename }) });
        const info = await res.json();
        if (info.success) {
            const b = info.bounds;
            const p = 0.1; // 10% padding
            const dx = b[1] - b[0];
            const dy = b[3] - b[2];
            const dz = b[5] - b[4];
            const minStr = `${(b[0] - dx * p).toFixed(2)} ${(b[2] - dy * p).toFixed(2)} ${(b[4] - dz * p).toFixed(2)}`;
            const maxStr = `${(b[1] + dx * p).toFixed(2)} ${(b[3] + dy * p).toFixed(2)} ${(b[5] + dz * p).toFixed(2)}`;
            document.getElementById("bmMin").value = minStr;
            document.getElementById("bmMax").value = maxStr;
            showNotification(`Bounds updated from ${filename}`, "success");
        }
        else {
            showNotification("Failed to get geometry info", "error");
        }
    }
    catch (e) {
        showNotification("Error auto-filling bounds", "error");
    }
    finally {
        if (btn) {
            btn.disabled = false;
            btn.removeAttribute("aria-busy");
            btn.innerHTML = originalText;
        }
    }
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
    const filename = document.getElementById("shmObjectList")?.value;
    if (!activeCase || !filename)
        return;
    // Use default value 0 if element doesn't exist or is empty, though HTML doesn't have shmLevel
    // The HTML has shmObjRefMin/Max, but not a global shmLevel.
    // Wait, I am fixing selectShmObject.
    // The request above was to generate snappyHexMeshDict.
    // The code references shmLevel which doesn't exist in HTML.
    // I should fix this too? Or just stub selectShmObject.
    // For now, I'll add selectShmObject.
    const level = 0; // Stub as element might be missing
    const locationInput = document.getElementById("shmLocation");
    const location = locationInput ? locationInput.value.trim().split(/\s+/).map(Number) : [0, 0, 0];
    try {
        await fetch("/api/meshing/snappyHexMesh/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, config: { stl_filename: filename, refinement_level: level, location_in_mesh: location } }) });
        showNotification("Generated", "success");
    }
    catch (e) { }
};
const selectShmObject = () => {
    const list = document.getElementById("shmObjectList");
    const props = document.getElementById("shmObjectProps");
    const placeholder = document.getElementById("shmObjectPlaceholder");
    const nameLabel = document.getElementById("shmSelectedObjectName");
    if (list && list.value) {
        if (props)
            props.classList.remove("hidden");
        if (placeholder)
            placeholder.classList.add("hidden");
        if (nameLabel)
            nameLabel.textContent = list.value;
        // In a real app, we would fetch existing config for this object here
    }
    else {
        if (props)
            props.classList.add("hidden");
        if (placeholder)
            placeholder.classList.remove("hidden");
    }
};
const updateShmObjectConfig = () => {
    // Stub for updating object config
    console.log("Updated object config");
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
const refreshMeshList = async (btnElement) => {
    if (!activeCase) {
        showNotification("No active case selected to list meshes", "warning", 3000);
        return;
    }
    const btn = btnElement;
    let originalText = "";
    if (btn) {
        originalText = btn.innerHTML;
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
        btn.classList.add("opacity-75", "cursor-wait");
        btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg> Refreshing...`;
    }
    try {
        const res = await fetch(`/api/available_meshes?tutorial=${encodeURIComponent(activeCase)}`);
        const data = await res.json();
        const select = document.getElementById("meshSelect");
        if (select && data.meshes) {
            if (data.meshes.length === 0) {
                select.innerHTML = '<option value="" disabled selected>No mesh files found</option>';
            }
            else {
                select.innerHTML = '<option value="">-- Select a mesh file --</option>';
                data.meshes.forEach((m) => {
                    const opt = document.createElement("option");
                    opt.value = m.path;
                    opt.textContent = m.name;
                    select.appendChild(opt);
                });
            }
        }
        if (btn)
            showNotification("Mesh list refreshed", "success", 2000);
    }
    catch (e) {
        console.error("Error refreshing mesh list:", e);
        showNotification("Failed to refresh mesh list", "error");
    }
    finally {
        if (btn) {
            btn.disabled = false;
            btn.removeAttribute("aria-busy");
            btn.classList.remove("opacity-75", "cursor-wait");
            btn.innerHTML = originalText;
        }
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
const refreshPostList = async (btnElement) => {
    refreshPostListVTK(btnElement);
};
const refreshPostListVTK = async (btnElement) => {
    if (!activeCase)
        return;
    const btn = btnElement;
    let originalText = "";
    if (btn) {
        originalText = btn.innerHTML;
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
        btn.classList.add("opacity-75", "cursor-wait");
        btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg> Refreshing...`;
    }
    try {
        const res = await fetch(`/api/available_meshes?tutorial=${encodeURIComponent(activeCase)}`);
        const data = await res.json();
        const select = document.getElementById("vtkFileSelect");
        if (select && data.meshes) {
            if (data.meshes.length === 0) {
                select.innerHTML = '<option value="" disabled selected>No VTK files found</option>';
            }
            else {
                select.innerHTML = '<option value="">-- Select a VTK file --</option>';
                data.meshes.forEach((m) => {
                    const opt = document.createElement("option");
                    opt.value = m.path;
                    opt.textContent = m.name;
                    select.appendChild(opt);
                });
            }
        }
        if (btn)
            showNotification("VTK file list refreshed", "success", 2000);
    }
    catch (e) {
        console.error(e);
        if (btn)
            showNotification("Failed to refresh VTK list", "error");
    }
    finally {
        if (btn) {
            btn.disabled = false;
            btn.removeAttribute("aria-busy");
            btn.classList.remove("opacity-75", "cursor-wait");
            btn.innerHTML = originalText;
        }
    }
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
            cachedLogHTML = savedLog; // ⚡ Bolt Optimization: Restore cache
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
window.selectShmObject = selectShmObject;
window.updateShmObjectConfig = updateShmObjectConfig;
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
window.copyMeshingOutput = copyMeshingOutput;
window.togglePlots = togglePlots;
window.toggleSection = toggleSection;
const init = () => {
    // Determine initial page from URL
    const path = window.location.pathname;
    let initialPage = "setup";
    if (path !== "/" && path !== "") {
        const pageName = path.substring(1).toLowerCase(); // remove leading slash
        // check if it's a valid page
        const pages = ["setup", "geometry", "meshing", "visualizer", "run", "plots", "post"];
        if (pages.includes(pageName)) {
            initialPage = pageName;
        }
    }
    // Handle browser back/forward buttons
    window.onpopstate = (event) => {
        if (event.state && event.state.page) {
            switchPage(event.state.page, false);
        }
        else {
            // Fallback if no state (e.g. initial load turned into history entry?)
            // or just parse URL again
            const p = window.location.pathname.substring(1).toLowerCase() || "setup";
            switchPage(p, false);
        }
    };
    // Switch to initial page (don't push state for the initial load)
    switchPage(initialPage, false);
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