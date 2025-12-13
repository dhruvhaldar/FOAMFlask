/**
 * FOAMFlask Frontend JavaScript
 */
import { generateContours as generateContoursFn } from "./frontend/isosurface.js";
// Global state
let caseDir = "";
let dockerImage = "";
let openfoamVersion = "";
let activeCase = "";
// Page management
let currentPage = "setup";
// Mesh visualization state
let currentMeshPath = null;
let isInteractiveMode = false;
// Notification management
let notificationId = 0;
let shmObjectConfigs = {};
let selectedShmObject = null;
// Plotting variables
let plotUpdateInterval = null;
let isFirstPlotLoad = true;
let requestCache = new Map();
const CACHE_DURATION = 1000;
const outputBuffer = [];
let outputFlushTimer = null;
// Utility functions
const getElement = (id) => {
    return document.getElementById(id);
};
// Logging
const CONSOLE_LOG_KEY = "foamflask_console_log";
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
    outputBuffer.forEach(({ message, type }) => {
        const line = document.createElement("div");
        if (type === "stderr")
            line.className = "text-red-600";
        else if (type === "info")
            line.className = "text-yellow-600 italic";
        else
            line.className = "text-green-700";
        line.textContent = message;
        container.appendChild(line);
    });
    container.scrollTop = container.scrollHeight;
    outputBuffer.length = 0;
    localStorage.setItem(CONSOLE_LOG_KEY, container.innerHTML);
};
const showNotification = (message, type, duration = 5000) => {
    const container = document.getElementById("notificationContainer");
    if (!container)
        return null;
    const id = ++notificationId;
    const notification = document.createElement("div");
    notification.id = `notification-${id}`;
    notification.className = "notification pointer-events-auto px-4 py-3 rounded-lg shadow-lg max-w-sm overflow-hidden relative";
    const colors = { success: "bg-green-500 text-white", error: "bg-red-500 text-white", warning: "bg-yellow-500 text-white", info: "bg-blue-500 text-white" };
    const icons = { success: "✓", error: "✗", warning: "⚠", info: "ℹ" };
    const content = document.createElement("div");
    content.className = "relative z-10";
    content.innerHTML = `<div class="flex items-center justify-between gap-3"><div class="flex items-center gap-2"><span class="text-2xl font-bold">${icons[type]}</span><span class="text-lg font-medium">${message}</span></div></div>`;
    notification.appendChild(content);
    notification.className += ` ${colors[type]}`;
    container.appendChild(notification);
    setTimeout(() => removeNotification(id), duration);
    return id;
};
const removeNotification = (id) => {
    const notification = document.getElementById(`notification-${id}`);
    if (notification) {
        notification.style.opacity = "0";
        setTimeout(() => notification.remove(), 300);
    }
};
// Toggle Section
window.toggleSection = (id) => {
    const el = document.getElementById(id);
    const toggle = document.getElementById(id + "Toggle");
    if (el) {
        if (el.classList.contains("hidden")) {
            el.classList.remove("hidden");
            if (toggle)
                toggle.textContent = "▼";
        }
        else {
            el.classList.add("hidden");
            if (toggle)
                toggle.textContent = "►";
        }
    }
};
// Page Switching
const switchPage = (pageName) => {
    const pages = ["setup", "geometry", "meshing", "visualizer", "run", "plots", "post"];
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
    // Auto-refresh lists based on page
    switch (pageName) {
        case "geometry":
            refreshGeometryList();
            break;
        case "meshing":
            refreshMeshingTab();
            break;
        case "visualizer":
            refreshMeshList();
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
            break;
        case "post":
            refreshPostList();
            break;
    }
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
        showNotification("Case directory set", "info");
        refreshCaseList();
    }
    catch (e) {
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
        showNotification("Docker config updated", "success");
    }
    catch (e) {
        showNotification("Failed to set Docker config", "error");
    }
};
const loadTutorial = async () => {
    try {
        const tutorialSelect = document.getElementById("tutorialSelect");
        const selected = tutorialSelect.value;
        showNotification("Importing tutorial...", "info");
        const response = await fetch("/load_tutorial", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tutorial: selected }) });
        if (!response.ok)
            throw new Error();
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
};
// Geometry Functions
const refreshGeometryList = async () => {
    if (!activeCase)
        return [];
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
            return data.files;
        }
    }
    catch (e) {
        console.error(e);
    }
    return [];
};
const uploadGeometry = async () => {
    const input = document.getElementById("geometryUpload");
    const file = input?.files?.[0];
    if (!file || !activeCase)
        return;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("caseName", activeCase);
    try {
        await fetch("/api/geometry/upload", { method: "POST", body: formData });
        showNotification("Uploaded", "success");
        input.value = "";
        refreshGeometryList();
    }
    catch (e) {
        showNotification("Failed", "error");
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
            if (div)
                div.innerHTML = `Bounds: [${info.bounds.join(", ")}]`;
            document.getElementById("geometryInfo")?.classList.remove("hidden");
        }
    }
    catch (e) { }
};
// Meshing Functions
const refreshMeshingTab = async () => {
    const files = await refreshGeometryList(); // Re-use geometry list fetching
    // Populate Object Settings List
    const objectList = document.getElementById("shmObjectList");
    if (objectList) {
        objectList.innerHTML = "";
        files.forEach(f => {
            const opt = document.createElement("option");
            opt.value = f;
            opt.textContent = f;
            objectList.appendChild(opt);
            // Initialize config if not exists
            if (!shmObjectConfigs[f]) {
                shmObjectConfigs[f] = {
                    name: f,
                    refinement_level_min: 2,
                    refinement_level_max: 2,
                    layers: 0
                };
            }
        });
    }
};
const selectShmObject = () => {
    const objectList = document.getElementById("shmObjectList");
    const filename = objectList.value;
    if (!filename)
        return;
    selectedShmObject = filename;
    const config = shmObjectConfigs[filename];
    const propsPanel = document.getElementById("shmObjectProps");
    const placeholder = document.getElementById("shmObjectPlaceholder");
    if (propsPanel)
        propsPanel.classList.remove("hidden");
    if (placeholder)
        placeholder.classList.add("hidden");
    document.getElementById("shmSelectedObjectName").textContent = filename;
    document.getElementById("shmObjRefMin").value = config.refinement_level_min.toString();
    document.getElementById("shmObjRefMax").value = config.refinement_level_max.toString();
    document.getElementById("shmObjLayers").value = config.layers.toString();
};
const updateShmObjectConfig = () => {
    if (!selectedShmObject)
        return;
    const config = shmObjectConfigs[selectedShmObject];
    config.refinement_level_min = parseInt(document.getElementById("shmObjRefMin").value);
    config.refinement_level_max = parseInt(document.getElementById("shmObjRefMax").value);
    config.layers = parseInt(document.getElementById("shmObjLayers").value);
};
const fillBoundsFromGeometry = async () => {
    // Pick the selected one from the Geometry tab list for simplicity, or we could add a selector
    const filename = document.getElementById("geometrySelect")?.value ||
        document.getElementById("shmObjectList")?.value;
    if (!filename || !activeCase) {
        showNotification("Please select a geometry object first", "warning");
        return;
    }
    try {
        const res = await fetch("/api/geometry/info", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, filename }) });
        const info = await res.json();
        if (info.success) {
            const b = info.bounds;
            // Add slight padding
            const p = 0.1;
            const dx = b[1] - b[0];
            const dy = b[3] - b[2];
            const dz = b[5] - b[4];
            document.getElementById("bmMin").value = `${(b[0] - dx * p).toFixed(3)} ${(b[2] - dy * p).toFixed(3)} ${(b[4] - dz * p).toFixed(3)}`;
            document.getElementById("bmMax").value = `${(b[1] + dx * p).toFixed(3)} ${(b[3] + dy * p).toFixed(3)} ${(b[5] + dz * p).toFixed(3)}`;
            showNotification("Bounds auto-filled", "success");
        }
    }
    catch (e) {
        showNotification("Failed to fetch info", "error");
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
        showNotification("Generated blockMeshDict", "success");
    }
    catch (e) { }
};
const generateSnappyHexMeshDict = async () => {
    if (!activeCase)
        return;
    // Build Global Settings
    const globalSettings = {
        castellated_mesh: document.getElementById("shmCastellated").checked,
        snap: document.getElementById("shmSnap").checked,
        add_layers: document.getElementById("shmLayers").checked,
        // Advanced
        max_non_ortho: parseInt(document.getElementById("shmMaxNonOrtho").value),
        min_triangle_twist: parseFloat(document.getElementById("shmMinTriangleTwist").value),
        feature_angle: parseInt(document.getElementById("shmLayerFeatureAngle").value),
        expansion_ratio: parseFloat(document.getElementById("shmExpansionRatio").value),
        final_thickness: parseFloat(document.getElementById("shmFinalThickness").value),
        min_thickness: parseFloat(document.getElementById("shmMinThickness").value),
    };
    const location = document.getElementById("shmLocation").value.trim().split(/\s+/).map(Number);
    // Build Object List
    const objects = Object.values(shmObjectConfigs);
    if (objects.length === 0) {
        showNotification("No objects to mesh! Upload geometry first.", "warning");
        return;
    }
    const payload = {
        caseName: activeCase,
        config: {
            global_settings: globalSettings,
            objects: objects,
            location_in_mesh: location
        }
    };
    try {
        const res = await fetch("/api/meshing/snappyHexMesh/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        const data = await res.json();
        if (data.success) {
            showNotification("Generated snappyHexMeshDict", "success");
        }
        else {
            showNotification("Failed to generate", "error");
        }
    }
    catch (e) {
        showNotification("Error", "error");
    }
};
const runMeshingCommand = async (cmd) => {
    if (!activeCase)
        return;
    showNotification(`Running ${cmd}`, "info");
    try {
        const res = await fetch("/api/meshing/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, command: cmd }) });
        const data = await res.json();
        if (data.success) {
            showNotification(`${cmd} completed`, "success");
            const div = document.getElementById("meshingOutput");
            if (div)
                div.innerText += `\n> ${cmd}\n${data.output}`;
        }
        else {
            showNotification("Command failed", "error");
            const div = document.getElementById("meshingOutput");
            if (div)
                div.innerText += `\n[ERROR] ${data.message}\n${data.output || ""}`;
        }
    }
    catch (e) {
        showNotification("Error", "error");
    }
};
// ... Rest of the file (Visualization, Plots, etc. remains mostly same but I'll make sure to include placeholders)
const runCommand = async (cmd) => {
    if (!cmd || !activeCase) {
        showNotification("Select case and command", "error");
        return;
    }
    try {
        showNotification(`Running ${cmd}...`, "info");
        const response = await fetch("/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseDir, tutorial: activeCase, command: cmd }) });
        if (!response.ok)
            throw new Error();
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        const read = async () => {
            const { done, value } = (await reader?.read()) || { done: true, value: undefined };
            if (done) {
                showNotification("Done", "success");
                return;
            }
            const text = decoder.decode(value);
            text.split("\n").forEach(line => { if (line.trim())
                appendOutput(line, "stdout"); });
            await read();
        };
        await read();
    }
    catch (e) {
        showNotification("Error", "error");
    }
};
// Visualizer
const refreshMeshList = async () => {
    if (!activeCase)
        return;
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
    catch (e) { }
};
const loadMeshVisualization = async () => {
    const path = document.getElementById("meshSelect")?.value;
    if (!path)
        return;
    currentMeshPath = path;
    updateMeshView();
};
const updateMeshView = async () => {
    if (!currentMeshPath)
        return;
    try {
        const res = await fetch("/api/mesh_screenshot", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ file_path: currentMeshPath, width: 800, height: 600 }) });
        const data = await res.json();
        if (data.success) {
            document.getElementById("meshImage").src = `data:image/png;base64,${data.image}`;
            document.getElementById("meshImage")?.classList.remove("hidden");
            document.getElementById("meshPlaceholder")?.classList.add("hidden");
        }
    }
    catch (e) { }
};
// Required Placeholders
const startPlotUpdates = () => { };
const refreshPostList = async () => { };
const runPostOperation = async (op) => { };
const loadCustomVTKFile = async () => { };
const loadContourVTK = async () => { };
const toggleAeroPlots = () => { };
const toggleInteractiveMode = async () => { };
const setCameraView = (v) => { };
const resetCamera = () => { };
const downloadPlotData = (id, file) => { };
const downloadPlotAsPNG = (id, file) => { };
const runFoamToVTK = async () => {
    runCommand("foamToVTK");
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
window.selectShmObject = selectShmObject;
window.updateShmObjectConfig = updateShmObjectConfig;
window.runFoamToVTK = runFoamToVTK;
document.addEventListener('DOMContentLoaded', () => {
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
    // Initial check
    window.onload = async () => {
        try {
            const response = await fetch("/get_case_root");
            const data = await response.json();
            caseDir = data.caseDir;
            const caseDirInput = document.getElementById("caseDir");
            if (caseDirInput)
                caseDirInput.value = caseDir;
            await refreshCaseList();
        }
        catch (e) { }
    };
});
//# sourceMappingURL=foamflask_frontend.js.map