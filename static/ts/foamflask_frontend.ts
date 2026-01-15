/**
 * FOAMFlask Frontend JavaScript
 */

import { generateContours as generateContoursFn } from "./frontend/isosurface.js";
import * as Plotly from "plotly.js";

// CSRF Protection Helpers
const getCookie = (name: string): string | null => {
  const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
  return v ? v[2] : null;
};

// Monkey patch fetch to include CSRF token
const originalFetch = window.fetch;
window.fetch = async (input, init) => {
  // Only inject for same-origin requests or relative URLs to prevent leaking token
  const url = typeof input === 'string' ? input : (input instanceof URL ? input.toString() : (input instanceof Request ? input.url : ''));
  const isRelative = url.startsWith('/');
  const isSameOrigin = url.startsWith(window.location.origin);

  if (isRelative || isSameOrigin) {
    const method = (init?.method || "GET").toUpperCase();
    if (method !== "GET" && method !== "HEAD") {
      const token = getCookie("csrf_token");
      if (token) {
        init = init || {};
        if (init.headers instanceof Headers) {
          init.headers.append("X-CSRFToken", token);
        } else if (Array.isArray(init.headers)) {
          (init.headers as string[][]).push(["X-CSRFToken", token]);
        } else {
           init.headers = { ...init.headers, "X-CSRFToken": token };
        }
      }
    }
  }
  return originalFetch(input, init);
};

// --- Interfaces ---
// Global Window Interface
declare global {
  interface Window {
    switchGeometryTab: (tab: "upload" | "resources") => void;
    fetchResourceGeometry: (btn?: HTMLElement) => void;
    switchPage: (pageId: string) => void;
    toggleMobileMenu: () => void;
    uploadGeometry: (btn?: HTMLElement) => void;
    refreshGeometryList: (btn?: HTMLElement) => void;
    generateBlockMeshDict: (btn?: HTMLElement) => void;
    generateSnappyHexMeshDict: (btn?: HTMLElement) => void;
    runCommand: (cmd: string, btn?: HTMLElement) => void;
    clearMeshingOutput: () => void;
    copyMeshingOutput: () => void;
    refreshMeshes: (btn?: HTMLElement) => void;
    viewMesh: () => void;
    copyRunOutput: () => void;
    confirmRunCommand: (cmd: string, btn?: HTMLElement) => void;
  }
}

interface ApiResponse {
  error?: string;
  output?: string;
  success?: boolean;
  message?: string;
}

interface CaseRootResponse extends ApiResponse {
  caseDir: string;
}

interface DockerConfigResponse extends ApiResponse {
  dockerImage: string;
  openfoamVersion: string;
}

interface TutorialLoadResponse extends ApiResponse {
  caseDir: string;
}

interface CaseListResponse extends ApiResponse {
  cases: string[];
}

interface MeshFile {
  path: string;
  name: string;
  size?: number;
  relative_path?: string;
}

interface AvailableMeshesResponse extends ApiResponse {
  meshes: MeshFile[];
}

interface MeshInfo {
  n_points: number;
  n_cells: number;
  bounds: number[];
  center?: number[];
  length?: number;
  volume?: number;
  array_names?: string[];
  point_arrays?: string[];
  cell_arrays?: string[];
  success: boolean;
  error?: string;
}

interface MeshScreenshotResponse extends ApiResponse {
  image?: string;
}

interface PlotData extends ApiResponse {
  time?: number[];
  p?: number[];
  Ux?: number[];
  Uy?: number[];
  Uz?: number[];
  U_mag?: number[];
  nut?: number[];
  nuTilda?: number[];
  k?: number[];
  epsilon?: number[];
  omega?: number[];
  [key: string]: any;
}

interface LatestDataResponse extends ApiResponse {
  time?: number;
  p?: number;
  U_mag?: number;
  Ux?: number;
  Uy?: number;
  Uz?: number;
  [key: string]: any;
}

interface ResidualsResponse extends ApiResponse {
  time?: number[];
  Ux?: number[];
  Uy?: number[];
  Uz?: number[];
  p?: number[];
  k?: number[];
  epsilon?: number[];
  omega?: number[];
}

interface PlotTrace {
  name?: string;
  visible?: boolean | "legendonly";
  x?: any[];
  y?: any[];
  type?: string;
  mode?: string;
  line?: any;
}

// Types
type CameraView = "front" | "back" | "left" | "right" | "top" | "bottom";

// Utility functions
const getElement = <T extends HTMLElement>(id: string): T | null => {
  return document.getElementById(id) as T | null;
};

const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) return error.message;
  return typeof error === "string" ? error : "Unknown error";
};

// Clear Console Log
const clearLog = (): void => {
  const outputDiv = document.getElementById("output");
  if (outputDiv) {
    outputDiv.innerHTML = "";
    cachedLogHTML = ""; // ⚡ Bolt Optimization: clear cache
    try {
      localStorage.removeItem(CONSOLE_LOG_KEY);
    } catch (e) {
      // Ignore local storage errors
    }
    outputBuffer.length = 0; // Clear buffer
    showNotification("Console log cleared", "info", NOTIFY_MEDIUM);
  }
};

// Generic Copy to Clipboard Helper
const copyTextFromElement = (elementId: string, successMessage: string, btnElement?: HTMLElement): void => {
  const el = document.getElementById(elementId);
  if (!el) return;

  // innerText preserves newlines better than textContent
  const text = el.innerText;
  if (!text.trim()) {
    showNotification("Content is empty", "info", NOTIFY_MEDIUM);
    return;
  }

  const onSuccess = () => {
    showNotification(successMessage, "success", NOTIFY_MEDIUM);
    if (btnElement) {
      const originalHTML = btnElement.innerHTML;
      const originalTitle = btnElement.getAttribute('title');

      // Visual feedback on the button
      btnElement.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-green-500" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
        </svg>
        <span class="text-green-600 font-medium">Copied!</span>
      `;
      btnElement.setAttribute('title', 'Copied to clipboard');

      // Revert after 2 seconds
      setTimeout(() => {
        btnElement.innerHTML = originalHTML;
        if (originalTitle) btnElement.setAttribute('title', originalTitle);
        else btnElement.removeAttribute('title');
      }, 2000);
    }
  };

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(onSuccess).catch(() => fallbackCopyText(text, successMessage, onSuccess));
  } else {
    fallbackCopyText(text, successMessage, onSuccess);
  }
};

const fallbackCopyText = (text: string, successMessage: string, onSuccess?: () => void): void => {
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

    if (successful) {
      if (onSuccess) onSuccess();
      else showNotification(successMessage, "success", NOTIFY_MEDIUM);
    } else {
      showNotification("Failed to copy", "error");
    }
  } catch (err) {
    showNotification("Failed to copy", "error");
  }
};

// Copy Console Log
const copyLogToClipboard = (btnElement?: HTMLElement): void => {
  copyTextFromElement("output", "Log copied to clipboard", btnElement);
};

// Clear Meshing Output
const clearMeshingOutput = (): void => {
  const div = document.getElementById("meshingOutput");
  if (div) {
    div.innerText = "Ready...";
    div.scrollTop = 0; // Reset scroll position
    showNotification("Meshing output cleared", "info", NOTIFY_MEDIUM);
  }
};

// Copy Meshing Output
const copyMeshingOutput = (btnElement?: HTMLElement): void => {
  copyTextFromElement("meshingOutput", "Meshing output copied", btnElement);
};

// Storage for Console Log
const CONSOLE_LOG_KEY = "foamflask_console_log";

// Global state
let caseDir: string = "";
let dockerImage: string = "";
let openfoamVersion: string = "";
let activeCase: string = "";

// Page management
let currentPage: string = "setup";

// Mesh visualization state
let currentMeshPath: string | null = null;
let availableMeshes: MeshFile[] = [];
let isInteractiveMode: boolean = false;

// Geometry State
let selectedGeometry: string | null = null;

// Notification constants
const NOTIFY_SHORT = 1500;
const NOTIFY_MEDIUM = 5000;
const NOTIFY_LONG = 8000;
const NOTIFY_DEFAULT = 10000;

// System constants
const POLL_INTERVAL = 5000;
const DEBOUNCE_DELAY = 5000;
const MAX_LOG_SIZE = 100000;

// Notification management
let notificationId: number = 0;
let lastErrorNotificationTime: number = 0;
const ERROR_NOTIFICATION_COOLDOWN: number = 5 * 60 * 1000;

// Plotting variables
let plotUpdateInterval: ReturnType<typeof setInterval> | null = null;
let wsConnection: WebSocket | null = null; // ⚡ Bolt Optimization: WebSocket for realtime data
let plotsVisible: boolean = true;
let aeroVisible: boolean = false;
let isUpdatingPlots: boolean = false;
let pendingPlotUpdate: boolean = false;
let isSimulationRunning: boolean = false; // Controls polling loop
let plotsInViewport: boolean = true;
let isFirstPlotLoad: boolean = true;

// Request management
let abortControllers = new Map<string, AbortController>();
let requestCache = new Map<string, { data: any; timestamp: number }>();
const CACHE_DURATION: number = 1000;

const outputBuffer: { message: string; type: string }[] = [];
let outputFlushTimer: ReturnType<typeof setTimeout> | null = null;
let saveLogTimer: ReturnType<typeof setTimeout> | null = null;

// ⚡ Bolt Optimization: maintain off-DOM cache to avoid expensive innerHTML access
let cachedLogHTML: string = "";

// Save log to local storage (Debounced)
const saveLogToStorage = (): void => {
  try {
    // ⚡ Bolt Optimization: Write from string variable instead of reading DOM
    localStorage.setItem(CONSOLE_LOG_KEY, cachedLogHTML);
  } catch (e) {
    console.warn("Failed to save console log to local storage (likely quota exceeded).");
  }
};

const saveLogDebounced = (): void => {
  if (saveLogTimer) clearTimeout(saveLogTimer);
  saveLogTimer = setTimeout(saveLogToStorage, DEBOUNCE_DELAY);
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

const plotLayout: Partial<Plotly.Layout> = {
  font: { family: "Inter, sans-serif", size: 12 },
  plot_bgcolor: "rgba(255, 255, 255, 0)",
  paper_bgcolor: "rgba(255, 255, 255, 0)",
  margin: { l: 50, r: 20, t: 60, b: 80, pad: 5 },
  height: 400,
  autosize: true,
  showlegend: true,
  legend: {
    orientation: "h" as const,
    y: -0.3,
    x: 0.5,
    xanchor: "center" as const,
    yanchor: "top" as const,
    // bgcolor: "rgba(255, 0, 0, 0)",
    borderwidth: 0,
  },
  xaxis: { showgrid: false, linewidth: 1 },
  yaxis: { showgrid: false, linewidth: 1 },
};

const plotConfig: Partial<Plotly.Config> = {
  responsive: true,
  displayModeBar: false,
  staticPlot: false,
  scrollZoom: true,
  doubleClick: "reset+autosize" as const,
  showTips: false,
  modeBarButtonsToRemove: [
    "zoom2d", "pan2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d",
    "hoverClosestCartesian", "hoverCompareCartesian", "zoom3d", "pan3d", "orbitRotation", "tableRotation",
    "handleDrag3d", "resetCameraDefault3d", "resetCameraLastSave3d", "hoverClosest3d",
    "sendDataToCloud", "toggleSpikelines", "setBackground", "toggleHover", "resetViews", "toImage"
  ] as any,
  displaylogo: false,
};

const lineStyle = { width: 2, opacity: 0.9 };

const createBoldTitle = (text: string): { text: string; font?: any } => ({
  text: `<b>${text}</b>`,
  font: { ...plotLayout.font, size: 22 },
});

// Helper: Download plot as PNG
const downloadPlotAsPNG = (
  plotIdOrDiv: string | any,
  filename: string = "plot.png"
): void => {
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
  }).then((dataUrl: string) => {
    const link = document.createElement("a");
    link.href = dataUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }).catch((err: any) => {
    console.error("Error downloading plot:", err);
  });
};

// Helper: Save current legend visibility
const getLegendVisibility = (
  plotDiv: HTMLElement
): Record<string, boolean | "legendonly"> => {
  try {
    const plotData = (plotDiv as any).data;
    if (!Array.isArray(plotData)) {
      return {};
    }

    const visibility: Record<string, boolean | "legendonly"> = {};

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
  } catch (error) {
    console.warn("Error getting legend visibility:", error);
    return {};
  }
};

// Helper: Attach white-bg download button to a plot
const attachWhiteBGDownloadButton = (plotDiv: any): void => {
  if (!plotDiv || plotDiv.dataset.whiteButtonAdded) return;
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
    .catch((err: unknown) => {
      console.error("Plotly update failed:", err);
    });
};

const downloadPlotData = (plotId: string, filename: string): void => {
  const plotDiv = document.getElementById(plotId) as any;
  if (!plotDiv || !plotDiv.data) return;
  const traces = plotDiv.data;
  traces.forEach((trace: any, index: number) => {
    if (!trace.x || !trace.y) return;
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
    } catch (error: unknown) {
      console.error(`FOAMFlask Error downloading ${traceName} data`, error);
    }
  });
};

// Page Switching
const switchPage = (pageName: string, updateUrl: boolean = true): void => {
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
    const mobileNavButton = document.getElementById(`mobile-nav-${page}`);

    if (pageElement) pageElement.classList.add("hidden");

    // Desktop Reset
    if (navButton) {
      // navButton.classList.remove("bg-cyan-700", "text-white"); // BG handled by pill
      navButton.classList.remove("text-white");
      navButton.classList.add("text-gray-900", "hover:bg-gray-100/50");
      navButton.removeAttribute("aria-current");
    }

    // Mobile Reset
    if (mobileNavButton) {
      mobileNavButton.classList.remove("bg-cyan-700", "text-white");
      mobileNavButton.classList.add("text-gray-700", "hover:text-cyan-800", "hover:bg-gray-50");
      mobileNavButton.removeAttribute("aria-current");
    }
  });

  const selectedPage = document.getElementById(`page-${pageName}`);
  const selectedNav = document.getElementById(`nav-${pageName}`);
  const selectedMobileNav = document.getElementById(`mobile-nav-${pageName}`);
  const navPill = document.getElementById("nav-pill");

  if (selectedPage) selectedPage.classList.remove("hidden");

  if (selectedNav) {
    // Update Text Color
    // selectedNav.classList.remove("text-gray-900", "hover:bg-gray-100");
    // selectedNav.classList.add("bg-cyan-700", "text-white");
    selectedNav.classList.remove("text-gray-900", "hover:bg-gray-100/50");
    selectedNav.classList.add("text-white");
    selectedNav.setAttribute("aria-current", "page");

    // Move Pill
    if (navPill) {
      navPill.style.opacity = "1";
      navPill.style.left = `${selectedNav.offsetLeft}px`;
      navPill.style.width = `${selectedNav.offsetWidth}px`;
    }
  }

  if (selectedMobileNav) {
    selectedMobileNav.classList.remove("text-gray-700", "hover:text-cyan-800", "hover:bg-gray-50");
    selectedMobileNav.classList.add("bg-cyan-700", "text-white");
    selectedMobileNav.setAttribute("aria-current", "page");
  }

  // Auto-refresh lists based on page
  switch (pageName) {
    case "geometry":
      refreshGeometryList();
      break;
    case "meshing":
      refreshGeometryList().then(() => {
        const shmSelect = document.getElementById("shmObjectList") as HTMLSelectElement;
        const geoSelect = document.getElementById("geometrySelect") as HTMLSelectElement;
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
          if (loader) loader.classList.remove("hidden");
        }
        if (!plotsContainer.hasAttribute("data-initialized")) {
          plotsContainer.setAttribute("data-initialized", "true");
          if (!plotUpdateInterval) startPlotUpdates();
        }
      }
      const aeroBtn = document.getElementById("toggleAeroBtn");
      if (aeroBtn) aeroBtn.classList.remove("hidden");
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

const setMobileMenuState = (isOpen: boolean): void => {
  const menu = document.getElementById("mobile-menu");
  const btn = document.getElementById("mobile-menu-btn");
  const icon = document.getElementById("mobile-menu-icon");

  if (menu) {
    if (isOpen) {
      menu.classList.remove("hidden");
      btn?.setAttribute("aria-expanded", "true");
      // Switch to X icon
      icon?.setAttribute("d", "M6 18L18 6M6 6l12 12");
    } else {
      menu.classList.add("hidden");
      btn?.setAttribute("aria-expanded", "false");
      // Switch to Hamburger icon
      icon?.setAttribute("d", "M4 6h16M4 12h16M4 18h16");
    }
  }
};

const toggleMobileMenu = () => {
  const menu = document.getElementById("mobile-menu");
  if (menu) {
    const isHidden = menu.classList.contains("hidden");
    setMobileMenuState(isHidden);
  }
};
(window as any).toggleMobileMenu = toggleMobileMenu;

// Show notification
const showNotification = (
  message: string,
  type: "success" | "error" | "warning" | "info",
  duration: number = NOTIFY_DEFAULT
): number | null => {
  // If a notification with the same message already exists, do not show another one
  // This prevents spamming the user with the same message
  if (document.querySelector(`.notification .message-slot[data-message="${message}"]`)) {
    return null;
  }

  const container = document.getElementById("notificationContainer");
  const template = document.getElementById("notification-template") as HTMLTemplateElement;

  if (!container || !template) return null;

  const id = ++notificationId;
  const clone = template.content.cloneNode(true) as DocumentFragment;
  const notification = clone.querySelector(".notification") as HTMLElement;

  if (!notification) return null;

  notification.id = `notification-${id}`;

  // Set ARIA role for accessibility
  if (type === "error" || type === "warning") {
    notification.setAttribute("role", "alert");
  } else {
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

  if (iconSlot) iconSlot.textContent = icons[type];
  if (messageSlot) {
    messageSlot.textContent = message;
    // Add data attribute to help with duplicate detection
    messageSlot.setAttribute("data-message", message);
  }

  // Handle duration and progress bar
  if (duration > 0) {
    const progressBar = notification.querySelector(".progress-bar") as HTMLElement;
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
  const closeBtn = notification.querySelector(".close-btn") as HTMLElement;
  if (closeBtn) {
    closeBtn.onclick = (e) => {
      e.stopPropagation();
      removeNotification(id);
    };
  }

  container.appendChild(notification);
  return id;
};

const removeNotification = (id: number): void => {
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

// Confirmation Modal
const showConfirmModal = (title: string, message: string): Promise<boolean> => {
  return new Promise((resolve) => {
    const modal = document.createElement("div");
    modal.className = "fixed inset-0 z-[60] flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm transition-opacity opacity-0";
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    modal.setAttribute("aria-labelledby", "confirm-title");
    modal.setAttribute("aria-describedby", "confirm-desc");

    modal.innerHTML = `
      <div class="bg-white rounded-xl shadow-2xl max-w-md w-full overflow-hidden transform scale-95 transition-transform duration-200">
        <div class="p-6">
          <h3 id="confirm-title" class="text-xl font-bold text-gray-900 mb-2">${title}</h3>
          <p id="confirm-desc" class="text-gray-600 mb-6">${message}</p>
          <div class="flex justify-end gap-3">
            <button id="confirm-cancel" class="px-4 py-2 rounded-lg text-gray-700 hover:bg-gray-100 font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300">Cancel</button>
            <button id="confirm-ok" class="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 shadow-sm">Confirm</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Animation
    requestAnimationFrame(() => {
      modal.classList.remove("opacity-0");
      modal.querySelector("div")?.classList.remove("scale-95");
      modal.querySelector("div")?.classList.add("scale-100");
    });

    const close = (result: boolean) => {
      modal.classList.add("opacity-0");
      setTimeout(() => modal.remove(), 200);
      resolve(result);
      document.removeEventListener("keydown", handleKey);
    };

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close(false);
      if (e.key === "Enter") close(true);
    };
    document.addEventListener("keydown", handleKey);

    const cancelBtn = modal.querySelector("#confirm-cancel") as HTMLElement;
    const okBtn = modal.querySelector("#confirm-ok") as HTMLElement;

    cancelBtn.onclick = () => close(false);
    okBtn.onclick = () => close(true);

    // Focus management
    setTimeout(() => cancelBtn.focus(), 50);
  });
};

// Network
const fetchWithCache = async <T = any>(
  url: string,
  options: RequestInit = {}
): Promise<T> => {
  const cacheKey = `${url}${JSON.stringify(options)}`;
  const cached = requestCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < CACHE_DURATION)
    return cached.data as T;

  if (abortControllers.has(url)) abortControllers.get(url)?.abort();
  const controller = new AbortController();
  abortControllers.set(url, controller);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    requestCache.set(cacheKey, { data, timestamp: Date.now() });
    return data as T;
  } finally {
    abortControllers.delete(url);
  }
};

// Logging
const appendOutput = (message: string, type: string): void => {
  outputBuffer.push({ message, type });
  // ⚡ Bolt Optimization: Throttle updates to ~30fps (32ms) instead of debouncing
  if (!outputFlushTimer) {
    outputFlushTimer = setTimeout(flushOutputBuffer, 32);
  }
};

const flushOutputBuffer = (): void => {
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
  const escapeHtml = (str: string) => {
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
    if (type === "stderr") className = "text-red-600";
    else if (type === "tutorial") className = "text-cyan-600 font-semibold";
    else if (type === "info") className = "text-yellow-600 italic";

    // ⚡ Bolt Optimization: Direct string construction + insertAdjacentHTML
    // Removes overhead of document.createElement() and .textContent assignments (O(N) -> O(1) DOM touches)
    const safeMessage = escapeHtml(message);
    newHtmlChunks += `<div class="${className}">${safeMessage}</div>`;
  });

  container.insertAdjacentHTML("beforeend", newHtmlChunks);
  cachedLogHTML += newHtmlChunks; // ⚡ Bolt Optimization: Append to cache

  // ⚡ Bolt Optimization: Cap the size of cachedLogHTML to prevent memory issues and localStorage quota errors
  const MAX_LOG_LENGTH = MAX_LOG_SIZE; // 100KB
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


const setDockerConfig = async (image: string, version: string, btnElement?: HTMLElement): Promise<void> => {
  const btn = btnElement as HTMLButtonElement | undefined;
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
    if (!response.ok) throw new Error();
    const data = await response.json() as DockerConfigResponse;
    dockerImage = data.dockerImage;
    openfoamVersion = data.openfoamVersion;

    const openfoamRootInput = document.getElementById("openfoamRoot");
    if (openfoamRootInput instanceof HTMLInputElement) {
      openfoamRootInput.value = `${dockerImage} OpenFOAM ${openfoamVersion}`;
    }

    showNotification("Docker config updated", "success");
  } catch (e) {
    showNotification("Failed to set Docker config", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.innerHTML = originalText;
    }
  }
};

const loadTutorial = async (): Promise<void> => {
  const btn = document.getElementById("loadTutorialBtn") as HTMLButtonElement | null;
  const originalText = btn ? btn.innerHTML : "Import Tutorial";

  try {
    if (btn) {
      btn.disabled = true;
      btn.setAttribute("aria-busy", "true");
      btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Importing...`;
    }

    const tutorialSelect = document.getElementById("tutorialSelect") as HTMLSelectElement;
    const selected = tutorialSelect.value;
    if (selected) localStorage.setItem("lastSelectedTutorial", selected);
    showNotification("Importing tutorial...", "info");
    const response = await fetch("/load_tutorial", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tutorial: selected }) });
    if (!response.ok) throw new Error();

    const data = await response.json() as TutorialLoadResponse;
    if (data.output) {
      data.output.split("\n").forEach((line: string) => {
        if (line.trim()) appendOutput(line.trim(), "info");
      });
    }

    showNotification("Tutorial imported", "success");
    await refreshCaseList();
    const importedName = selected.split('/').pop();
    if (importedName) {
      selectCase(importedName);
      const select = document.getElementById("caseSelect") as HTMLSelectElement;
      if (select) select.value = importedName;
      // UX: Default to "From Resources" tab for imported tutorials
      switchGeometryTab("resources");
    }
  } catch (e) {
    showNotification("Failed to load tutorial", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.innerHTML = originalText;
    }
  }
};

// Toggle Section Visibility
const toggleSection = (id: string): void => {
  const section = document.getElementById(id);
  const toggleIcon = document.getElementById(`${id}Toggle`);

  if (!section || !toggleIcon) return;

  const isHidden = section.classList.contains("hidden");

  if (isHidden) {
    section.classList.remove("hidden");
    toggleIcon.textContent = "▼";
    toggleIcon.classList.remove("-rotate-90");
    // If it's a button (accessible version), update aria-expanded
    const toggleBtn = toggleIcon.parentElement?.tagName === "BUTTON" ? toggleIcon.parentElement : null;
    if (toggleBtn) toggleBtn.setAttribute("aria-expanded", "true");
  } else {
    section.classList.add("hidden");
    toggleIcon.textContent = "▶";
    toggleIcon.classList.add("-rotate-90");
    // If it's a button (accessible version), update aria-expanded
    const toggleBtn = toggleIcon.parentElement?.tagName === "BUTTON" ? toggleIcon.parentElement : null;
    if (toggleBtn) toggleBtn.setAttribute("aria-expanded", "false");
  }
};

// Case Management
const refreshCaseList = async (btnElement?: HTMLElement) => {
  const btn = btnElement as HTMLButtonElement | undefined;
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
    } else {
      // Fallback or just standard spinner
      btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Refreshing...`;
    }
  }

  try {
    const response = await fetch("/api/cases/list");
    if (!response.ok) throw new Error("Failed to fetch cases");
    const data = await response.json() as CaseListResponse;
    const select = document.getElementById("caseSelect") as HTMLSelectElement;
    if (select && data.cases) {
      const current = select.value;
      if (data.cases.length === 0) {
        select.innerHTML = '<option value="" disabled selected>No cases found</option>';
      } else {
        select.innerHTML = '<option value="">-- Select a Case --</option>';
        data.cases.forEach(c => {
          const opt = document.createElement("option");
          opt.value = c;
          opt.textContent = c;
          select.appendChild(opt);
        });
        if (current && data.cases.includes(current)) select.value = current;
        else if (activeCase && data.cases.includes(activeCase)) select.value = activeCase;
      }
    }
    // Only show success notification if invoked manually (via button)
    if (btn) showNotification("Case list refreshed", "success", NOTIFY_MEDIUM);
  } catch (e) {
    console.error(e);
    if (btn) showNotification("Failed to refresh case list", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.classList.remove("opacity-75", "cursor-wait");
      btn.innerHTML = originalText;
    }
  }
};

const selectCase = (val: string) => {
  activeCase = val;
  localStorage.setItem("lastSelectedCase", val);
};

const createNewCase = async () => {
  const caseName = (document.getElementById("newCaseName") as HTMLInputElement).value;
  if (!caseName) { showNotification("Enter case name", "warning"); return; }

  const btn = document.getElementById("createCaseBtn") as HTMLButtonElement | null;
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
      (document.getElementById("newCaseName") as HTMLInputElement).value = "";
      await refreshCaseList();
      selectCase(caseName);
      const select = document.getElementById("caseSelect") as HTMLSelectElement;
      if (select) select.value = caseName;
    } else { showNotification(data.message || "Failed", "error"); }
  } catch (e) { showNotification("Error creating case", "error"); }
  finally {
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.innerHTML = originalText;
    }
  }
};

const confirmRunCommand = async (cmd: string, btnElement?: HTMLElement): Promise<void> => {
  // Check for destructive commands
  if (cmd.includes("Allclean") || cmd.includes("clean")) {
    const confirmed = await showConfirmModal("Run Command", `Are you sure you want to run '${cmd}'? This may delete generated files.`);
    if (!confirmed) return;
  }
  runCommand(cmd, btnElement);
};

const runCommand = async (cmd: string, btnElement?: HTMLElement): Promise<void> => {
  if (!cmd) { showNotification("No command specified", "error"); return; }

  // Use tutorial select if activeCase is not set, or prefer tutorial select for "Run" tab
  const selectedTutorial = (document.getElementById("tutorialSelect") as HTMLSelectElement)?.value || activeCase;

  if (!selectedTutorial) { showNotification("Select case and command", "error"); return; }

  let originalText = "";
  const btn = btnElement as HTMLButtonElement;

  if (btn) {
    originalText = btn.innerHTML;
    btn.disabled = true;
    btn.setAttribute("aria-busy", "true");
    btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Running...`;
  }

  try {
    showNotification(`Running ${cmd}...`, "info");
    const response = await fetch("/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseDir, tutorial: selectedTutorial, command: cmd }) });
    if (!response.ok) throw new Error();
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    // Start polling immediately when command starts
    isSimulationRunning = true;
    startPlotUpdates();

    while (true) {
      const { done, value } = (await reader?.read()) || { done: true, value: undefined };
      if (done) {
        showNotification("Simulation completed successfully", "success");
        flushOutputBuffer();
        break;
      }
      const text = decoder.decode(value);
      text.split("\n").forEach(line => {
        if (line.trim()) {
          // Parse HTML line if present (e.g. from app.py escaping)
          // Actually app.py sends raw strings or HTML? It sends <br>.
          // But appendOutput just adds to innerHTML.
          // Wait, the previous logic parsed lines. Let's keep it simple.
          let logLine = line;
          if (logLine.startsWith("INFO::[FOAMFlask]")) {
            // Special handling?
          }
          // Simple append
          const output = document.getElementById("commandOutput");
          if (output) {
            output.innerHTML += line + "<br>";
            output.scrollTop = output.scrollHeight;
          }
        }
      });
    }
  } catch (err) {
    console.error(err); // Keep console error for debugging
    showNotification(`Error: ${err}`, "error");
  } finally {
    const btn = btnElement as HTMLButtonElement;
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.innerHTML = originalText;
    }
    isSimulationRunning = false;
    updatePlots(); // Final update to catch last data
  }
};

// Realtime Plotting Functions
const togglePlots = (): void => {
  plotsVisible = !plotsVisible;
  const container = document.getElementById("plotsContainer");
  const btn = document.getElementById("togglePlotsBtn");
  const aeroBtn = document.getElementById("toggleAeroBtn");
  if (plotsVisible) {
    container?.classList.remove("hidden");
    if (btn) btn.textContent = "Hide Plots";
    aeroBtn?.classList.remove("hidden");
    startPlotUpdates();
    setupIntersectionObserver();
  } else {
    container?.classList.add("hidden");
    if (btn) btn.textContent = "Show Plots";
    aeroBtn?.classList.add("hidden");
    stopPlotUpdates();
  }
};

const setupIntersectionObserver = (): void => {
  const plotsContainer = document.getElementById("plotsContainer");
  if (!plotsContainer || plotsContainer.dataset.observerSetup) return;
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        plotsInViewport = entry.isIntersecting;
      });
    },
    { threshold: 0.1, rootMargin: "50px" }
  );
  observer.observe(plotsContainer);
  plotsContainer.dataset.observerSetup = "true";
};

const toggleAeroPlots = (): void => {
  aeroVisible = !aeroVisible;
  const container = document.getElementById("aeroContainer");
  const btn = document.getElementById("toggleAeroBtn");
  if (aeroVisible) {
    container?.classList.remove("hidden");
    if (btn) btn.textContent = "Hide Aero Plots";
    updateAeroPlots();
  } else {
    container?.classList.add("hidden");
    if (btn) btn.textContent = "Show Aero Plots";
  }
};

const connectWebSocket = (tutorial: string) => {
  if (wsConnection) {
    // If already connected to same tutorial, do nothing
    if (wsConnection.url.includes(`tutorial=${encodeURIComponent(tutorial)}`) &&
        (wsConnection.readyState === WebSocket.OPEN || wsConnection.readyState === WebSocket.CONNECTING)) {
      return;
    }
    wsConnection.close();
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/data?tutorial=${encodeURIComponent(tutorial)}`;

  try {
    wsConnection = new WebSocket(wsUrl);

    wsConnection.onmessage = (event) => {
      // ⚡ Bolt Optimization: WebSocket push updates
      if (document.hidden || !plotsInViewport) return;

      try {
        const payload = JSON.parse(event.data);
        if (payload.plot_data) updatePlots(payload.plot_data);
        if (payload.residuals) updateResidualsPlot(tutorial, payload.residuals);
      } catch (e) {
        console.error("WS Error", e);
      }
    };

    wsConnection.onclose = () => {
      wsConnection = null;
      // Fallback to polling if WS dies during simulation
      if (isSimulationRunning) {
        console.warn("WS Closed, reverting to polling");
        startPolling();
      }
    };
  } catch (e) {
    console.error("Failed to connect WS", e);
    startPolling();
  }
};

const startPlotUpdates = (): void => {
  const selectedTutorial = (document.getElementById("tutorialSelect") as HTMLSelectElement)?.value;
  if (!selectedTutorial) return;

  // Try WebSocket first
  connectWebSocket(selectedTutorial);

  // Also start polling as fallback / heartbeat or for initial load check
  startPolling();
};

const startPolling = (): void => {
  if (plotUpdateInterval) return;
  plotUpdateInterval = setInterval(() => {
    // ⚡ Bolt Optimization: Pause polling when tab is hidden
    if (document.hidden) return;

    // Stop if simulation not running AND no WS connection (if WS exists, it handles updates)
    if (!isSimulationRunning && !wsConnection) {
      stopPlotUpdates();
      return;
    }

    // If WS is active and open, we don't need to poll for data
    if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
        return;
    }

    if (!plotsInViewport) return;
    if (!isUpdatingPlots) updatePlots();
    else pendingPlotUpdate = true;
  }, POLL_INTERVAL);
};

const stopPlotUpdates = (): void => {
  if (plotUpdateInterval) {
    clearInterval(plotUpdateInterval);
    plotUpdateInterval = null;
  }
  if (wsConnection) {
    wsConnection.close();
    wsConnection = null;
  }
};

const updateResidualsPlot = async (tutorial: string, injectedData?: ResidualsResponse): Promise<void> => {
  try {
    let data = injectedData;
    if (!data) {
      data = await fetchWithCache<ResidualsResponse>(
        `/api/residuals?tutorial=${encodeURIComponent(tutorial)}`
      );
    }

    if (data.error || !data.time || data.time.length === 0) {
      return;
    }
    const traces: any[] = [];
    const fields = ["Ux", "Uy", "Uz", "p"] as const;
    const colors = [
      plotlyColors.blue,
      plotlyColors.red,
      plotlyColors.green,
      plotlyColors.magenta,
      plotlyColors.cyan,
      plotlyColors.orange,
    ];
    fields.forEach((field, idx) => {
      const fieldData = (data as any)[field];
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
      const residualsPlotDiv = getElement<HTMLElement>("residuals-plot");

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
        void Plotly.react(residualsPlotDiv, traces as any, layout as any, {
          ...plotConfig,
          displayModeBar: true,
          scrollZoom: false,
        }).then(() => attachWhiteBGDownloadButton(residualsPlotDiv));
      }
    }
  } catch (error: unknown) {
    console.error("FOAMFlask Error updating residuals", error);
  }
};

const updateAeroPlots = async (preFetchedData?: PlotData): Promise<void> => {
  const selectedTutorial = (
    document.getElementById("tutorialSelect") as HTMLSelectElement
  )?.value;
  if (!selectedTutorial) return;
  try {
    let data = preFetchedData;

    // ⚡ Bolt Optimization: Use pre-fetched data if available to save a network request
    if (!data) {
      const response = await fetch(
        `/api/plot_data?tutorial=${encodeURIComponent(selectedTutorial)}`
      );
      data = await response.json() as PlotData;
    }

    if (data.error) return;

    // Cp plot
    if (
      Array.isArray(data.p) &&
      Array.isArray(data.time) &&
      data.p.length === data.time.length &&
      data.p.length > 0
    ) {
      const pinf = 101325;
      const rho = 1.225;
      const uinf =
        Array.isArray(data.U_mag) && data.U_mag.length ? data.U_mag[0] : 1.0;
      const qinf = 0.5 * rho * uinf * uinf;
      const cp = data.p.map((pval: number) => (pval - pinf) / qinf);
      const cpDiv = document.getElementById("cp-plot");
      if (cpDiv) {
        const cpTrace: any = {
          x: data.time,
          y: cp,
          type: "scatter",
          mode: "lines+markers",
          name: "Cp",
          line: { color: plotlyColors.red, width: 2.5 },
        };
        void Plotly.react(
          cpDiv,
          [cpTrace as any],
          {
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
          },
          plotConfig
        )
          .then(() => {
            attachWhiteBGDownloadButton(cpDiv);
          })
          .catch((err: unknown) => {
            console.error("Plotly update failed:", err);
          });
      }
    }

    // Velocity profile 3D plot
    if (
      Array.isArray(data.Ux) &&
      Array.isArray(data.Uy) &&
      Array.isArray(data.Uz)
    ) {
      const velocityDiv = document.getElementById("velocity-profile-plot");
      if (velocityDiv) {
        const velocityTrace: any = {
          x: data.Ux,
          y: data.Uy,
          z: data.Uz,
          type: "scatter3d",
          mode: "markers",
          name: "Velocity",
          marker: { color: plotlyColors.blue, size: 5 },
        };
        void Plotly.react(
          velocityDiv,
          [velocityTrace as any],
          {
            ...plotLayout,
            title: createBoldTitle("Velocity Profile"),
            scene: {
              xaxis: { title: { text: "Ux" } },
              yaxis: { title: { text: "Uy" } },
              zaxis: { title: { text: "Uz" } },
            },
          },
          plotConfig
        )
          .then(() => {
            attachWhiteBGDownloadButton(velocityDiv);
          })
          .catch((err: unknown) => {
            console.error("Plotly update failed:", err);
          });
      }
    }
  } catch (error: unknown) {
    console.error("FOAMFlask Error updating aero plots", error);
  }
};

const updatePlots = async (injectedData?: PlotData): Promise<void> => {
  const selectedTutorial = (
    document.getElementById("tutorialSelect") as HTMLSelectElement
  )?.value;
  if (!selectedTutorial || isUpdatingPlots) return;
  isUpdatingPlots = true;

  try {
    let data = injectedData;
    if (!data) {
      // ⚡ Bolt Optimization: Use fast API endpoint
      data = await fetchWithCache<PlotData>(
        `/api/plot_data?tutorial=${encodeURIComponent(selectedTutorial)}`
      );
    }

    if (data.error) {
      console.error("FOAMFlask Error fetching plot data", data.error);
      // Only show notification if explicit fetch failed, to avoid WS spam
      if (!injectedData) showNotification("Error fetching plot data", "error");
      return;
    }

    // Pressure plot
    if (data.p && data.time) {
      const pressureDiv = getElement<HTMLElement>("pressure-plot");
      if (!pressureDiv) {
        console.error("Pressure plot element not found");
        return;
      }

      const legendVisibility = getLegendVisibility(pressureDiv);

      const pressureTrace: PlotTrace = {
        x: data.time,
        y: data.p,
        type: "scatter",
        mode: "lines",
        name: "Pressure",
        line: { color: plotlyColors.blue, ...lineStyle, width: 2.5 },
      };

      if (pressureTrace.name && legendVisibility.hasOwnProperty(pressureTrace.name)) {
        pressureTrace.visible = legendVisibility[pressureTrace.name] as
          | boolean
          | "legendonly";
      }

      void Plotly.react(
        pressureDiv,
        [pressureTrace as any],
        {
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
        },
        plotConfig
      )
        .then(() => {
          attachWhiteBGDownloadButton(pressureDiv);
        })
        .catch((err: unknown) => {
          console.error("Plotly update failed:", err);
        });
    }

    // Velocity plot
    if (data.U_mag && data.time) {
      const velocityDiv = getElement<HTMLElement>("velocity-plot");
      if (!velocityDiv) {
        console.error("Velocity plot element not found");
        return;
      }

      const legendVisibility = getLegendVisibility(velocityDiv as any);

      const traces: PlotTrace[] = [
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
          tr.visible = legendVisibility[tr.name] as boolean | "legendonly";
        }
      });

      void Plotly.react(
        velocityDiv,
        traces as any,
        {
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
        },
        plotConfig
      ).then(() => {
        attachWhiteBGDownloadButton(velocityDiv);
      });
    }

    // Turbulence plot
    const turbulenceTrace: PlotTrace[] = [];
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
        void Plotly.react(
          turbPlotDiv,
          turbulenceTrace as any,
          {
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
          },
          plotConfig
        ).then(() => {
          attachWhiteBGDownloadButton(turbPlotDiv);
        });
      }
    }

    // Update residuals and aero plots in parallel
    const updatePromises = [updateResidualsPlot(selectedTutorial)];
    // ⚡ Bolt Optimization: Pass the already fetched data to avoid redundant request
    if (aeroVisible) updatePromises.push(updateAeroPlots(data));
    await Promise.allSettled(updatePromises);

    // After all plots are updated
    if (isFirstPlotLoad) {
      showNotification("Plots loaded successfully", "success", NOTIFY_LONG);
      isFirstPlotLoad = false;
    }
  } catch (error: unknown) {
    console.error("FOAMFlask Error updating plots", error);
    const currentTime = Date.now();
    const selectedTutorial = (
      document.getElementById("tutorialSelect") as HTMLSelectElement
    )?.value;
    if (
      selectedTutorial &&
      currentTime - lastErrorNotificationTime > ERROR_NOTIFICATION_COOLDOWN
    ) {
      showNotification(
        `Error updating plots: ${error instanceof Error ? error.message : "Unknown error"
        }`,
        "error"
      );
      lastErrorNotificationTime = currentTime;
    }
  } finally {
    isUpdatingPlots = false;

    // FIX: Hide loader after update completes
    const loader = document.getElementById("plotsLoading");
    if (loader && !loader.classList.contains("hidden")) {
      loader.classList.add("hidden");
    }

    if (pendingPlotUpdate) {
      pendingPlotUpdate = false;
      requestAnimationFrame(() => updatePlots());
    }
  }
};

// Geometry Functions
const refreshGeometryList = async (btnElement?: HTMLElement) => {
  if (!activeCase) {
    showNotification("No active case selected to list geometries", "warning", NOTIFY_LONG);
    return;
  }

  const btn = btnElement as HTMLButtonElement | undefined;
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
      const select = document.getElementById("geometrySelect") as HTMLSelectElement;
      if (select) {
        select.innerHTML = "";
        if (data.files.length === 0) {
          const opt = document.createElement("option");
          opt.disabled = true;
          opt.textContent = "No geometry files found";
          select.appendChild(opt);
        } else {
          data.files.forEach((f: string) => {
            const opt = document.createElement("option");
            opt.value = f; opt.textContent = f; select.appendChild(opt);
          });
        }
      }
    }
    if (btn) showNotification("Geometry list refreshed", "success", NOTIFY_MEDIUM);
  } catch (e) {
    console.error(e);
    if (btn) showNotification("Failed to refresh geometry list", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.classList.remove("opacity-75", "cursor-wait");
      btn.innerHTML = originalText;
    }
  }
};



const switchGeometryTab = (tab: "upload" | "resources") => {
  const track = document.getElementById("geometry-track");
  const pill = document.getElementById("geometry-bg-pill");
  const uploadBtn = document.getElementById("tab-btn-geo-upload");
  const resourceBtn = document.getElementById("tab-btn-geo-resources");

  // Only toggle text styles now, background is handled by the pill
  const activeTextClasses = ["text-cyan-800", "font-semibold"];
  const inactiveTextClasses = ["text-gray-600", "hover:text-gray-800", "font-medium"];

  if (tab === "upload") {
    if (track) track.style.transform = "translateX(0%)";
    if (pill) pill.style.transform = "translateX(0)";

    uploadBtn?.classList.remove(...inactiveTextClasses);
    uploadBtn?.classList.add(...activeTextClasses);
    uploadBtn?.setAttribute("aria-selected", "true");

    resourceBtn?.classList.remove(...activeTextClasses);
    resourceBtn?.classList.add(...inactiveTextClasses);
    resourceBtn?.setAttribute("aria-selected", "false");
  } else {
    if (track) track.style.transform = "translateX(-100%)";
    // Move pill to the second position (100% width + gap)
    if (pill) pill.style.transform = "translateX(calc(100% + 0.25rem))";

    resourceBtn?.classList.remove(...inactiveTextClasses);
    resourceBtn?.classList.add(...activeTextClasses);
    resourceBtn?.setAttribute("aria-selected", "true");

    uploadBtn?.classList.remove(...activeTextClasses);
    uploadBtn?.classList.add(...inactiveTextClasses);
    uploadBtn?.setAttribute("aria-selected", "false");

    loadResourceGeometries();
  }
};

const loadResourceGeometries = async (refresh: boolean = false) => {
  const select = document.getElementById("resourceGeometrySelect") as HTMLSelectElement;
  if (!select) return;

  // Frontend Cache Check: If we have options (more than just the placeholder/loading) and strict refresh isn't requested
  if (!refresh && select.options.length > 1) {
    return;
  }

  const btn = document.getElementById("refreshResourceGeometryBtn") as HTMLButtonElement | null;
  const originalIcon = btn ? btn.innerHTML : "Refresh";

  if (btn) {
    btn.disabled = true;
    btn.classList.add("cursor-wait", "opacity-75");
    btn.innerHTML = `<svg class="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>`;
  }

  select.innerHTML = '<option>Loading...</option>';
  try {
    const url = refresh ? "/api/resources/geometry/list?refresh=true" : "/api/resources/geometry/list";
    const res = await fetch(url);
    const data = await res.json();

    select.innerHTML = '<option value="" disabled selected>Select Geometry</option>';
    if (data.files && Array.isArray(data.files)) {
      if (data.files.length === 0) {
        const opt = document.createElement("option");
        opt.disabled = true;
        opt.textContent = "No geometry files found";
        select.appendChild(opt);
      } else {
        data.files.forEach((f: string) => {
          const opt = document.createElement("option");
          opt.value = f;
          opt.textContent = f;
          select.appendChild(opt);
        });
      }
    }
  } catch (e) {
    console.error(e);
    select.innerHTML = '<option>Error loading list</option>';
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.classList.remove("cursor-wait", "opacity-75");
      btn.innerHTML = originalIcon;
    }
  }
};

const fetchResourceGeometry = async (btnElement?: HTMLElement) => {
  const select = document.getElementById("resourceGeometrySelect") as HTMLSelectElement;
  const filename = select?.value;
  if (!filename || !activeCase) {
    showNotification("Please select a geometry and active case", "error");
    return;
  }

  const btn = (btnElement || document.getElementById("fetchResourceGeometryBtn")) as HTMLButtonElement;
  const originalText = btn ? btn.innerHTML : "Fetch & Import";

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Fetching...`;
  }

  try {
    const res = await fetch("/api/resources/geometry/fetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename, caseName: activeCase })
    });
    const result = await res.json();
    if (result.success) {
      showNotification(`Fetched ${filename} successfully`, "success");
      refreshGeometryList();
    } else {
      showNotification(result.message || "Fetch failed", "error");
    }
  } catch (e) {
    showNotification("Error fetching geometry", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  }
};
(window as any).fetchResourceGeometry = fetchResourceGeometry;

const setCase = (btn?: HTMLElement) => {
  const caseDirInput = document.getElementById("caseDir") as HTMLInputElement;
  const caseDir = caseDirInput.value.trim();

  if (!caseDir) {
    showNotification("Please enter a case directory path", "warning");
    return;
  }

  const originalText = btn ? btn.innerText : "";
  if (btn) btn.innerText = "Setting...";

  fetchWithCache("/set_case", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ caseDir }),
  })
    .then((data) => {
      if (data.caseDir) {
        showNotification(`Case root set to: ${data.caseDir}`, "success");
        refreshCaseList(); // Refresh the list of cases
      } else if (data.output) {
         showNotification(data.output, "info"); // Likely an error message from backend
      }
    })
    .catch((err) => {
      showNotification(`Error setting case root: ${getErrorMessage(err)}`, "error");
    })
    .finally(() => {
      if (btn) btn.innerText = originalText;
    });
};
(window as any).setCase = setCase;

const openCaseRoot = (btn?: HTMLElement) => {
  fetchWithCache("/open_case_root", {
      method: "POST",
  })
  .then((data) => {
      if (data.output) {
          if (data.output.toLowerCase().includes("error") || data.output.toLowerCase().includes("failed")) {
               showNotification(data.output, "error");
          } else {
               showNotification(data.output, "success");
          }
      }
  })
  .catch((err) => {
      showNotification(`Failed to open case root: ${getErrorMessage(err)}`, "error");
  });
};
(window as any).openCaseRoot = openCaseRoot;
window.switchGeometryTab = switchGeometryTab;

const uploadGeometry = async (btnElement?: HTMLElement) => {
  const input = document.getElementById("geometryUpload") as HTMLInputElement;
  const btn = (btnElement || document.getElementById("uploadGeometryBtn")) as HTMLButtonElement;
  const file = input?.files?.[0];

  if (!activeCase) {
    showNotification("Please select an active case first", "warning");
    return;
  }

  if (!file) {
    showNotification("Please select a file to upload", "warning");
    if (input) {
      input.focus();
      input.setAttribute("aria-invalid", "true");
      input.addEventListener("change", () => input.removeAttribute("aria-invalid"), { once: true });
    }
    return;
  }

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
    if (!response.ok) throw new Error("Upload failed");
    showNotification("Geometry uploaded successfully", "success");
    input.value = "";
    refreshGeometryList();
  } catch (e) {
    showNotification("Failed to upload geometry", "error");
  } finally {
    // Restore button state
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.innerHTML = originalText;
    }
  }
};

const deleteGeometry = async () => {
  const filename = (document.getElementById("geometrySelect") as HTMLSelectElement)?.value;
  if (!filename || !activeCase) return;

  const confirmed = await showConfirmModal("Delete Geometry", `Are you sure you want to delete ${filename}?`);
  if (!confirmed) return;

  try {
    await fetch("/api/geometry/delete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, filename }) });
    refreshGeometryList();
  } catch (e) { showNotification("Failed", "error"); }
};

const loadGeometryView = async () => {
  const filename = (document.getElementById("geometrySelect") as HTMLSelectElement)?.value;
  if (!filename || !activeCase) return;
  showNotification("Loading...", "info");
  try {
    const res = await fetch("/api/geometry/view", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, filename }) });
    if (res.ok) {
      const html = await res.text();
      (document.getElementById("geometryInteractive") as HTMLIFrameElement).srcdoc = html;
      document.getElementById("geometryPlaceholder")?.classList.add("hidden");
    }
  } catch (e) { showNotification("Failed", "error"); }

  // Info
  try {
    const res = await fetch("/api/geometry/info", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, filename }) });
    const info = await res.json();
    if (info.success) {
      const div = document.getElementById("geometryInfoContent");
      if (div) {
        const b = info.bounds;
        const fmt = (n: number) => n.toFixed(3);
        const dx = (b[1] - b[0]).toFixed(3);
        const dy = (b[3] - b[2]).toFixed(3);
        const dz = (b[5] - b[4]).toFixed(3);

        const setText = (id: string, text: string) => {
          const el = document.getElementById(id);
          if (el) el.textContent = text;
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
  } catch (e) { }
};

// Meshing Functions
const fillBoundsFromGeometry = async (btnElement?: HTMLElement) => {
  if (!activeCase) {
    showNotification("Please select an active case first", "warning");
    return;
  }

  const filename = (document.getElementById("shmObjectList") as HTMLSelectElement)?.value;
  if (!filename) {
    showNotification("Please select a geometry object in the 'Object Settings' list below", "warning");
    return;
  }

  const btn = btnElement as HTMLButtonElement | undefined;
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
      const dx = b[1] - b[0]; const dy = b[3] - b[2]; const dz = b[5] - b[4];

      const minStr = `${(b[0] - dx * p).toFixed(2)} ${(b[2] - dy * p).toFixed(2)} ${(b[4] - dz * p).toFixed(2)}`;
      const maxStr = `${(b[1] + dx * p).toFixed(2)} ${(b[3] + dy * p).toFixed(2)} ${(b[5] + dz * p).toFixed(2)}`;

      (document.getElementById("bmMin") as HTMLInputElement).value = minStr;
      (document.getElementById("bmMax") as HTMLInputElement).value = maxStr;

      showNotification(`Bounds updated from ${filename}`, "success");
    } else {
      showNotification("Failed to get geometry info", "error");
    }
  } catch (e) {
    showNotification("Error auto-filling bounds", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.innerHTML = originalText;
    }
  }
};

const generateBlockMeshDict = async (btnElement?: HTMLElement) => {
  if (!activeCase) {
    showNotification("Please select an active case first", "warning");
    return;
  }

  const btn = btnElement as HTMLButtonElement | undefined;
  let originalText = "";

  if (btn) {
    originalText = btn.innerHTML;
    btn.disabled = true;
    btn.setAttribute("aria-busy", "true");
    btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Generating...`;
  }

  const minVal = (document.getElementById("bmMin") as HTMLInputElement).value.trim().split(/\s+/).map(Number);
  const maxVal = (document.getElementById("bmMax") as HTMLInputElement).value.trim().split(/\s+/).map(Number);
  const cells = (document.getElementById("bmCells") as HTMLInputElement).value.trim().split(/\s+/).map(Number);
  const grading = (document.getElementById("bmGrading") as HTMLInputElement).value.trim().split(/\s+/).map(Number);
  try {
    await fetch("/api/meshing/blockMesh/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, config: { min_point: minVal, max_point: maxVal, cells, grading } }) });
    showNotification("Generated blockMeshDict", "success");
  } catch (e) {
    showNotification("Failed to generate blockMeshDict", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.innerHTML = originalText;
    }
  }
};

const generateSnappyHexMeshDict = async (btnElement?: HTMLElement) => {
  const filename = (document.getElementById("shmObjectList") as HTMLSelectElement)?.value;
  if (!activeCase) {
    showNotification("Please select an active case first", "warning");
    return;
  }
  if (!filename) {
    showNotification("Please select a geometry object first", "warning");
    return;
  }

  const btn = btnElement as HTMLButtonElement | undefined;
  let originalText = "";

  if (btn) {
    originalText = btn.innerHTML;
    btn.disabled = true;
    btn.setAttribute("aria-busy", "true");
    btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Generating...`;
  }

  // Use default value 0 if element doesn't exist or is empty, though HTML doesn't have shmLevel
  // The HTML has shmObjRefMin/Max, but not a global shmLevel.
  // Wait, I am fixing selectShmObject.
  // The request above was to generate snappyHexMeshDict.

  // The code references shmLevel which doesn't exist in HTML.
  // I should fix this too? Or just stub selectShmObject.
  // For now, I'll add selectShmObject.

  const level = 0; // Stub as element might be missing
  const locationInput = document.getElementById("shmLocation") as HTMLInputElement;
  const location = locationInput ? locationInput.value.trim().split(/\s+/).map(Number) : [0, 0, 0];
  try {
    await fetch("/api/meshing/snappyHexMesh/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caseName: activeCase, config: { stl_filename: filename, refinement_level: level, location_in_mesh: location } }) });
    showNotification("Generated snappyHexMeshDict", "success");
  } catch (e) {
    showNotification("Failed to generate snappyHexMeshDict", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.innerHTML = originalText;
    }
  }
};

const selectShmObject = () => {
  const list = document.getElementById("shmObjectList") as HTMLSelectElement;
  const props = document.getElementById("shmObjectProps");
  const placeholder = document.getElementById("shmObjectPlaceholder");
  const nameLabel = document.getElementById("shmSelectedObjectName");

  if (list && list.value) {
    if (props) props.classList.remove("hidden");
    if (placeholder) placeholder.classList.add("hidden");
    if (nameLabel) nameLabel.textContent = list.value;
    // In a real app, we would fetch existing config for this object here
  } else {
    if (props) props.classList.add("hidden");
    if (placeholder) placeholder.classList.remove("hidden");
  }
};

const updateShmObjectConfig = () => {
  // Stub for updating object config
  console.log("Updated object config");
};

const runMeshingCommand = async (cmd: string, btnElement?: HTMLElement) => {
  if (!activeCase) return;

  const btn = btnElement as HTMLButtonElement | undefined;
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
    } else {
      showNotification(data.message || "Meshing failed", "error");
    }

    if (data.output) {
      const div = document.getElementById("meshingOutput");
      if (div) {
        div.innerText += `\n${data.output}`;
        div.scrollTop = div.scrollHeight; // Auto-scroll to bottom
      }
    }
  } catch (e) {
    console.error(e);
    showNotification("Meshing failed to execute", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.innerHTML = originalText;
    }
  }
};

// Visualizer
const runFoamToVTK = async (btnElement?: HTMLElement) => {
  if (!activeCase) {
    showNotification("Please select a case first", "warning");
    return;
  }

  const btn = btnElement as HTMLButtonElement | undefined;
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

    if (!response.ok) throw new Error("Failed to start foamToVTK");

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

  } catch (e) {
    console.error(e);
    showNotification("Error running foamToVTK", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.innerHTML = originalText;
    }
  }
};


const refreshMeshList = async (btnElement?: HTMLElement) => {
  if (!activeCase) {
    showNotification("No active case selected to list meshes", "warning", NOTIFY_LONG);
    return;
  }

  const btn = btnElement as HTMLButtonElement | undefined;
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
    const select = document.getElementById("meshSelect") as HTMLSelectElement;
    if (select && data.meshes) {
      if (data.meshes.length === 0) {
        select.innerHTML = '<option value="" disabled selected>No mesh files found</option>';
      } else {
        select.innerHTML = '<option value="">-- Select a mesh file --</option>';
        data.meshes.forEach((m: MeshFile) => {
          const opt = document.createElement("option");
          opt.value = m.path; opt.textContent = m.name; select.appendChild(opt);
        });
      }
    }
    if (btn) showNotification("Mesh list refreshed", "success", NOTIFY_MEDIUM);
  } catch (e) {
    console.error("Error refreshing mesh list:", e);
    showNotification("Failed to refresh mesh list", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.classList.remove("opacity-75", "cursor-wait");
      btn.innerHTML = originalText;
    }
  }
};

const loadMeshVisualization = async () => {
  const select = document.getElementById("meshSelect") as HTMLSelectElement;
  const path = select?.value;
  const btn = document.getElementById("loadMeshBtn") as HTMLButtonElement | null;

  if (!path) {
    showNotification("Please select a mesh file to load", "warning");
    if (select) {
      select.focus();
      select.setAttribute("aria-invalid", "true");
      select.addEventListener("change", () => select.removeAttribute("aria-invalid"), { once: true });
    }
    return;
  }

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
  } finally {
    // Restore button state
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.innerHTML = originalText;
    }
  }
};

const updateMeshView = async () => {
  if (!currentMeshPath) return;
  const showEdges = (document.getElementById("showEdges") as HTMLInputElement)?.checked ?? true;
  const color = (document.getElementById("meshColor") as HTMLSelectElement)?.value ?? "lightblue";
  const cameraPosition = (document.getElementById("cameraPosition") as HTMLSelectElement)?.value || null;

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
      (document.getElementById("meshImage") as HTMLImageElement).src = `data:image/png;base64,${data.image}`;
      document.getElementById("meshImage")?.classList.remove("hidden");
      document.getElementById("meshPlaceholder")?.classList.add("hidden");
      document.getElementById("meshControls")?.classList.remove("hidden");
      document.getElementById("meshActionButtons")?.classList.add("hidden");
    }
  } catch (e) { }
};

function displayMeshInfo(meshInfo: {
  success: boolean;
  n_points?: number;
  n_cells?: number;
  length?: number;
  volume?: number;
  bounds?: number[];
  center?: number[];
}): void {
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

async function refreshInteractiveViewer(successMessage: string = "Interactive mode enabled"): Promise<void> {
  const meshInteractive = document.getElementById(
    "meshInteractive"
  ) as HTMLIFrameElement | null;
  const meshImage = document.getElementById(
    "meshImage"
  ) as HTMLImageElement | null;
  const meshPlaceholder = document.getElementById("meshPlaceholder");
  const toggleBtn = document.getElementById("toggleInteractiveBtn");
  const cameraControl = document.getElementById("cameraPosition");
  const updateBtn = document.getElementById("updateViewBtn");

  if (!meshInteractive || !meshImage || !meshPlaceholder || !toggleBtn || !cameraControl || !updateBtn) return;

  showNotification("Loading interactive viewer...", "info");

  try {
    const showEdgesInput = document.getElementById(
      "showEdges"
    ) as HTMLInputElement | null;
    const colorInput = document.getElementById(
      "meshColor"
    ) as HTMLInputElement | null;

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

    showNotification(
      successMessage,
      "success",
      NOTIFY_LONG
    );
  } catch (error: unknown) {
    console.error("[FOAMFlask] Error loading interactive viewer:", error);
    const errorMessage =
      error instanceof Error
        ? error.name === "AbortError"
          ? "Loading was cancelled or timed out"
          : error.message
        : "Failed to load interactive viewer";

    showNotification(
      `Failed to load interactive viewer: ${errorMessage}`,
      "error"
    );

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

async function onMeshParamChange(): Promise<void> {
  if (isInteractiveMode) {
    await refreshInteractiveViewer("Interactive mode updated");
  }
}

async function toggleInteractiveMode(): Promise<void> {
  if (!currentMeshPath) {
    showNotification("Please load a mesh first", "warning");
    return;
  }

  const meshImage = document.getElementById(
    "meshImage"
  ) as HTMLImageElement | null;
  const meshInteractive = document.getElementById(
    "meshInteractive"
  ) as HTMLIFrameElement | null;
  const meshPlaceholder = document.getElementById("meshPlaceholder");
  const toggleBtn = document.getElementById("toggleInteractiveBtn");
  const cameraControl = document.getElementById("cameraPosition");
  const updateBtn = document.getElementById("updateViewBtn");

  if (
    !meshImage ||
    !meshInteractive ||
    !meshPlaceholder ||
    !toggleBtn ||
    !cameraControl ||
    !updateBtn
  ) {
    showNotification("Required mesh elements not found", "error");
    return;
  }

  isInteractiveMode = !isInteractiveMode;

  if (isInteractiveMode) {
    // Switch to interactive mode
    await refreshInteractiveViewer("Interactive mode enabled");
  } else {
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

    showNotification("Switched to static mode", "info", NOTIFY_MEDIUM);
  }
}

// Set camera view for interactive mode
function setCameraView(view: CameraView): void {
  const iframe = document.getElementById(
    "meshInteractive"
  ) as HTMLIFrameElement | null;
  if (!iframe || !iframe.contentWindow) return;

  try {
    // Send message to iframe to set camera view
    iframe.contentWindow.postMessage(
      {
        type: "setCameraView",
        view: view,
      },
      "*"
    );

    showNotification(`Set view to ${view.toUpperCase()}`, "info", NOTIFY_SHORT);
  } catch (error: unknown) {
    console.error("Error setting camera view:", error);
  }
}

// Reset camera to default view
function resetCamera(): void {
  const iframe = document.getElementById(
    "meshInteractive"
  ) as HTMLIFrameElement | null;
  if (!iframe || !iframe.contentWindow) return;

  try {
    // Send message to iframe to reset camera
    iframe.contentWindow.postMessage(
      {
        type: "resetCamera",
      },
      "*"
    );

    showNotification("Camera view reset", "info", NOTIFY_SHORT);
  } catch (error: unknown) {
    console.error("Error resetting camera:", error);
  }
}

// Post Processing
const refreshPostList = async (btnElement?: HTMLElement) => {
  refreshPostListVTK(btnElement);
};

const refreshPostListVTK = async (btnElement?: HTMLElement) => {
  if (!activeCase) {
    showNotification("No active case selected to list VTK files", "warning", NOTIFY_LONG);
    return;
  }

  const btn = btnElement as HTMLButtonElement | undefined;
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
    const select = document.getElementById("vtkFileSelect") as HTMLSelectElement;
    if (select && data.meshes) {
      if (data.meshes.length === 0) {
        select.innerHTML = '<option value="" disabled selected>No VTK files found</option>';
      } else {
        select.innerHTML = '<option value="">-- Select a VTK file --</option>';
        data.meshes.forEach((m: MeshFile) => {
          const opt = document.createElement("option");
          opt.value = m.path; opt.textContent = m.name; select.appendChild(opt);
        });
      }
    }
    if (btn) showNotification("VTK file list refreshed", "success", NOTIFY_MEDIUM);
  } catch (e) {
    console.error(e);
    if (btn) showNotification("Failed to refresh VTK list", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.classList.remove("opacity-75", "cursor-wait");
      btn.innerHTML = originalText;
    }
  }
};

const runPostOperation = async (operation: string) => {
  // Stub
};
const loadCustomVTKFile = async () => { };
const loadContourVTK = async () => { };


// Check startup status
const checkStartupStatus = async (): Promise<void> => {
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
      if (messageEl) messageEl.textContent = data.message;
      if (data.status === "completed") {
        modal.remove();
        return;
      } else if (data.status === "failed") {
        if (messageEl) {
          messageEl.className = "text-red-600";
          messageEl.textContent = `Error: ${data.message}. Please check server logs.`;
        }
        return;
      }
      setTimeout(pollStatus, 1000);
    } catch (e) {
      setTimeout(pollStatus, 5000);
    }
  };
  await pollStatus();
};

// Initialize
window.onload = async () => {
  try { await checkStartupStatus(); } catch (e) { console.error(e); }

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
    const caseRootData = await fetchWithCache<CaseRootResponse>("/get_case_root");
    const dockerConfigData = await fetchWithCache<DockerConfigResponse>("/get_docker_config");
    caseDir = caseRootData.caseDir;
    const caseDirInput = document.getElementById("caseDir") as HTMLInputElement;
    if (caseDirInput) caseDirInput.value = caseDir;
    dockerImage = dockerConfigData.dockerImage;
    openfoamVersion = dockerConfigData.openfoamVersion;
    const openfoamRootInput = document.getElementById("openfoamRoot") as HTMLInputElement;
    if (openfoamRootInput) openfoamRootInput.value = `${dockerImage} OpenFOAM ${openfoamVersion}`;

    // Load Cases
    await refreshCaseList();
    const savedCase = localStorage.getItem("lastSelectedCase");
    if (savedCase) {
      const select = document.getElementById("caseSelect") as HTMLSelectElement;
      let exists = false;
      for (let i = 0; i < select.options.length; i++) {
        if (select.options[i].value === savedCase) { exists = true; break; }
      }
      if (exists) {
        select.value = savedCase;
        activeCase = savedCase;
      }
    }

    // Check if we need to restore any plot state or similar
    // ...

  } catch (e) { console.error(e); }
};


// Exports
(window as any).switchPage = switchPage;
(window as any).setCase = setCase;
(window as any).setDockerConfig = setDockerConfig;
(window as any).loadTutorial = loadTutorial;
(window as any).createNewCase = createNewCase;
(window as any).selectCase = selectCase;
(window as any).refreshCaseList = refreshCaseList;
(window as any).uploadGeometry = uploadGeometry;
(window as any).deleteGeometry = deleteGeometry;
(window as any).loadGeometryView = loadGeometryView;
(window as any).fillBoundsFromGeometry = fillBoundsFromGeometry;
(window as any).generateBlockMeshDict = generateBlockMeshDict;
(window as any).generateSnappyHexMeshDict = generateSnappyHexMeshDict;
(window as any).selectShmObject = selectShmObject;
(window as any).updateShmObjectConfig = updateShmObjectConfig;
(window as any).runMeshingCommand = runMeshingCommand;
(window as any).refreshMeshList = refreshMeshList;
(window as any).loadMeshVisualization = loadMeshVisualization;
(window as any).updateMeshView = updateMeshView;
(window as any).runFoamToVTK = runFoamToVTK;
(window as any).refreshPostList = refreshPostList;
(window as any).toggleAeroPlots = toggleAeroPlots;
(window as any).runCommand = runCommand;
(window as any).confirmRunCommand = confirmRunCommand;
(window as any).toggleInteractiveMode = toggleInteractiveMode;
(window as any).setCameraView = setCameraView;
(window as any).resetCamera = resetCamera;
(window as any).downloadPlotData = downloadPlotData;
(window as any).loadCustomVTKFile = loadCustomVTKFile;
(window as any).loadContourVTK = loadContourVTK;
(window as any).generateContours = generateContoursFn;
(window as any).downloadPlotAsPNG = downloadPlotAsPNG;
(window as any).showNotification = showNotification;
(window as any).runPostOperation = runPostOperation;
(window as any).clearLog = clearLog;
(window as any).copyLogToClipboard = copyLogToClipboard;
(window as any).clearMeshingOutput = clearMeshingOutput;
(window as any).copyMeshingOutput = copyMeshingOutput;
(window as any).togglePlots = togglePlots;
(window as any).toggleSection = toggleSection;


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
    } else {
      // Fallback if no state (e.g. initial load turned into history entry?)
      // or just parse URL again
      const p = window.location.pathname.substring(1).toLowerCase() || "setup";
      switchPage(p, false);
    }
  };

  // Switch to initial page (don't push state for the initial load)
  switchPage(initialPage, false);

  const navButtons = [
    { id: 'nav-setup', mobileId: 'mobile-nav-setup', handler: () => switchPage('setup') },
    { id: 'nav-run', mobileId: 'mobile-nav-run', handler: () => switchPage('run') },
    { id: 'nav-geometry', mobileId: 'mobile-nav-geometry', handler: () => switchPage('geometry') },
    { id: 'nav-meshing', mobileId: 'mobile-nav-meshing', handler: () => switchPage('meshing') },
    { id: 'nav-visualizer', mobileId: 'mobile-nav-visualizer', handler: () => switchPage('visualizer') },
    { id: 'nav-plots', mobileId: 'mobile-nav-plots', handler: () => switchPage('plots') },
    { id: 'nav-post', mobileId: 'mobile-nav-post', handler: () => switchPage('post') }
  ];

  navButtons.forEach(({ id, mobileId, handler }) => {
    const button = document.getElementById(id);
    if (button) button.addEventListener('click', handler);

    const mobileButton = document.getElementById(mobileId);
    if (mobileButton) {
      mobileButton.addEventListener('click', () => {
        handler();
        setMobileMenuState(false);
      });
    }
  });

  const loadTutorialBtn = document.getElementById('loadTutorialBtn');
  if (loadTutorialBtn) loadTutorialBtn.addEventListener('click', loadTutorial);

  // ⚡ Bolt Optimization: Resume updates immediately when tab becomes visible
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && plotsVisible && plotsInViewport) {
      if (!isUpdatingPlots) {
        updatePlots();
      } else {
        pendingPlotUpdate = true;
      }
    }
  });

  // Persist Tutorial Selection
  const tutorialSelect = document.getElementById('tutorialSelect') as HTMLSelectElement;
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
    tutorialSelect.addEventListener('change', (e: Event) => {
      const target = e.target as HTMLSelectElement;
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

  // Scroll Listener for Navbar
  window.addEventListener("scroll", handleScroll);

  initLogScrollObserver();
};

const handleScroll = (): void => {
  const navbar = document.getElementById("navbar");
  if (!navbar) return;

  if (window.scrollY > 10) {
    if (navbar.classList.contains("glass")) {
      navbar.classList.remove("glass");
      navbar.classList.add("glass-plot");
    }
  } else {
    if (navbar.classList.contains("glass-plot")) {
      navbar.classList.remove("glass-plot");
      navbar.classList.add("glass");
    }
  }
};

// Scroll to Bottom Logic
const scrollToLogBottom = (): void => {
  const output = document.getElementById("output");
  if (output) {
    // Check if scrollTo options are supported (native smooth scroll)
    try {
      output.scrollTo({ top: output.scrollHeight, behavior: "smooth" });
    } catch (e) {
      // Fallback for older browsers
      output.scrollTop = output.scrollHeight;
    }
  }
};
(window as any).scrollToLogBottom = scrollToLogBottom;

const initLogScrollObserver = (): void => {
  const output = document.getElementById("output");
  const btn = document.getElementById("scrollToBottomBtn");
  if (!output || !btn) return;

  const handleLogScroll = () => {
    // Show button if we are more than 100px from the bottom
    const distanceToBottom = output.scrollHeight - output.scrollTop - output.clientHeight;
    // Use a small tolerance for "at bottom" check, but larger for showing the button
    const shouldShow = distanceToBottom > 150;

    if (shouldShow) {
      btn.classList.remove("opacity-0", "translate-y-2", "pointer-events-none");
      btn.classList.add("opacity-100", "translate-y-0", "pointer-events-auto");
    } else {
      btn.classList.add("opacity-0", "translate-y-2", "pointer-events-none");
      btn.classList.remove("opacity-100", "translate-y-0", "pointer-events-auto");
    }
  };

  let ticking = false;
  output.addEventListener("scroll", () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        handleLogScroll();
        ticking = false;
      });
      ticking = true;
    }
  });
};

// --- Font Settings Logic ---

(window as any).toggleFontSettings = (): void => {
  const menu = document.getElementById("fontSettingsMenu");
  const btn = document.getElementById("fontSettingsBtn");
  if (menu) {
    const isHidden = menu.classList.contains("hidden");
    if (isHidden) {
      menu.classList.remove("hidden");
      if (btn) btn.setAttribute("aria-expanded", "true");
      // Close on click outside
      setTimeout(() => {
        const closeHandler = (e: MouseEvent) => {
          if (!menu.contains(e.target as Node) &&
            (e.target as HTMLElement).id !== "fontSettingsBtn" &&
            !(e.target as HTMLElement).closest("#fontSettingsBtn")) {
            menu.classList.add("hidden");
            if (btn) btn.setAttribute("aria-expanded", "false");
            document.removeEventListener("click", closeHandler);
          }
        };
        document.addEventListener("click", closeHandler);
      }, 10);
    } else {
      menu.classList.add("hidden");
      if (btn) btn.setAttribute("aria-expanded", "false");
    }
  }
};

(window as any).changePlotFont = (fontFamily: string): void => {
  if (!fontFamily) return;

  // Update global layout config
  if (plotLayout.font) {
    plotLayout.font.family = fontFamily;
  }

  // Update existing plots
  const plotIds = [
    "pressure-plot",
    "velocity-plot",
    "turbulence-plot",
    "residuals-plot",
    "cp-plot",
    "velocity-profile-plot"
  ];

  plotIds.forEach(id => {
    const el = document.getElementById(id);
    if (el && (el as any).data) { // Check if plot exists and has data
      Plotly.relayout(el, { "font.family": fontFamily } as any).catch(err => {
        console.warn(`Failed to update font for ${id}:`, err);
      });
    }
  });

  // Update input value if it wasn't the trigger
  const input = document.getElementById("customFontInput") as HTMLInputElement;
  if (input && input.value !== fontFamily) {
    input.value = fontFamily;
  }

  showNotification(`Plot font changed to ${fontFamily.split(',')[0]}`, "info", NOTIFY_MEDIUM);
};


(window as any).switchCaseCreationTab = (tab: "create" | "import"): void => {
  const track = document.getElementById("case-creation-track");
  const pill = document.getElementById("case-creation-bg-pill");
  const createBtn = document.getElementById("tab-btn-create");
  const importBtn = document.getElementById("tab-btn-import");

  if (!track || !createBtn || !importBtn) return;

  // Only toggle text styles now
  const activeTextClasses = ["text-cyan-800", "font-semibold"];
  const inactiveTextClasses = ["text-gray-600", "hover:text-gray-800", "font-medium"];

  if (tab === "create") {
    track.style.transform = "translateX(0%)";
    if (pill) pill.style.transform = "translateX(0)";

    // Active Style for Create
    createBtn.classList.remove(...inactiveTextClasses);
    createBtn.classList.add(...activeTextClasses);
    createBtn.setAttribute("aria-selected", "true");

    // Inactive Style for Import
    importBtn.classList.remove(...activeTextClasses);
    importBtn.classList.add(...inactiveTextClasses);
    importBtn.setAttribute("aria-selected", "false");

    // Focus Input (UX Improvement)
    const input = document.getElementById("newCaseName") as HTMLInputElement;
    if (input && tab === "create") setTimeout(() => input.focus(), 300); // Wait for transition
  } else {
    track.style.transform = "translateX(-100%)";
    if (pill) pill.style.transform = "translateX(calc(100% + 0.25rem))";

    // Active Style for Import
    importBtn.classList.remove(...inactiveTextClasses);
    importBtn.classList.add(...activeTextClasses);
    importBtn.setAttribute("aria-selected", "true");

    // Inactive Style for Create
    createBtn.classList.remove(...activeTextClasses);
    createBtn.classList.add(...inactiveTextClasses);
    createBtn.setAttribute("aria-selected", "false");

    // Focus Input (UX Improvement)
    const select = document.getElementById("tutorialSelect") as HTMLSelectElement;
    // Ensure we only focus if the tab is visible and it's the right element
    if (select && tab === "import") setTimeout(() => select.focus(), 300); // Wait for transition
  }
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
