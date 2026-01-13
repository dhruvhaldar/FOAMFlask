
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Window } from 'hap-dom'; // or just rely on jsdom

// Mock dependencies
vi.mock('plotly.js', () => ({
  react: vi.fn(),
  newPlot: vi.fn(),
  extendTraces: vi.fn(),
  toImage: vi.fn().mockResolvedValue('data:image/png;base64,mock'),
}));

vi.mock('../../static/ts/frontend/isosurface.js', () => ({
  generateContours: vi.fn(),
}));

// We need to setup the DOM before importing the main file because it might access the DOM at top level or on window.onload
// However, the functions are exported to window.

describe('FoamFlask Frontend', () => {
  let frontend: any;

  beforeEach(async () => {
    // Reset DOM
    document.body.innerHTML = `
      <div id="page-setup" class="page"></div>
      <div id="nav-setup" class="nav-btn"></div>
      <div id="page-geometry" class="page hidden"></div>
      <div id="nav-geometry" class="nav-btn"></div>
      <div id="page-meshing" class="page hidden"></div>
      <div id="nav-meshing" class="nav-btn"></div>
      <div id="page-visualizer" class="page hidden"></div>
      <div id="nav-visualizer" class="nav-btn"></div>
      <div id="page-plots" class="page hidden"></div>
      <div id="nav-plots" class="nav-btn"></div>
      <div id="page-post" class="page hidden"></div>
      <div id="nav-post" class="nav-btn"></div>
      <div id="page-run" class="page hidden"></div>
      <div id="nav-run" class="nav-btn"></div>

      <div id="notificationContainer"></div>
      <template id="notification-template">
        <div class="notification">
          <div class="icon-slot"></div>
          <div class="message-slot"></div>
          <div class="progress-bar hidden"></div>
          <button class="close-btn"></button>
        </div>
      </template>

      <div id="output"></div>
      <input id="caseDir" />
      <input id="openfoamRoot" />
      <select id="caseSelect"><option value="">-- Select --</option></select>
      <input id="newCaseName" />
      <select id="tutorialSelect"><option value="tut1">Tut 1</option></select>

      <div id="plotsContainer" class="hidden"></div>
      <div id="plotsLoading" class="hidden"></div>
      <button id="togglePlotsBtn"></button>
      <button id="toggleAeroBtn"></button>

      <div id="mySection" class="hidden"></div>
      <button id="mySectionToggle">▶</button>
    `;

    // Mock fetch
    global.fetch = vi.fn();

    // Mock LocalStorage
    const localStorageMock = (function() {
      let store: any = {};
      return {
        getItem: function(key: string) {
          return store[key] || null;
        },
        setItem: function(key: string, value: string) {
          store[key] = value.toString();
        },
        removeItem: function(key: string) {
          delete store[key];
        },
        clear: function() {
          store = {};
        }
      };
    })();
    Object.defineProperty(window, 'localStorage', { value: localStorageMock });

    // We import the file here to ensure it runs in the configured environment
    // Since it executes side effects, we might want to reset modules between tests if possible,
    // but for now let's just import it.
    // Note: In a real scenario, we might need to use `vi.resetModules()` and dynamic import.
    await import('../../../static/ts/foamflask_frontend.ts');
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('switchPage should toggle classes correctly', () => {
    const { switchPage } = window as any;

    // Initial state: setup is visible
    const setupPage = document.getElementById('page-setup');
    const geometryPage = document.getElementById('page-geometry');
    const setupNav = document.getElementById('nav-setup');

    // Switch to geometry
    switchPage('geometry');

    expect(setupPage?.classList.contains('hidden')).toBe(true);
    expect(geometryPage?.classList.contains('hidden')).toBe(false);
    expect(document.getElementById('nav-geometry')?.getAttribute('aria-current')).toBe('page');
    expect(document.getElementById('nav-setup')?.getAttribute('aria-current')).toBeNull();
  });

  it('showNotification should add element to container', () => {
    const { showNotification } = window as any;

    showNotification('Test Message', 'success');

    const container = document.getElementById('notificationContainer');
    expect(container?.children.length).toBe(1);
    const notification = container?.querySelector('.notification');
    expect(notification).toBeTruthy();
    expect(notification?.querySelector('.message-slot')?.textContent).toBe('Test Message');
    // Actual class is bg-green-500/80 which is a single class string if tailwind hasn't processed it into separate classes yet in jsdom environment?
    // The code sets className += ` ${colors[type]}`.
    // colors.success = "bg-green-500/80 text-white backdrop-blur-md border border-white/20 shadow-xl"
    // "bg-green-500/80" is the class name.
    expect(notification?.className).toContain('bg-green-500/80');
  });

  it('toggleSection should toggle visibility and rotate icon', () => {
    const { toggleSection } = window as any;

    const section = document.getElementById('mySection');
    const toggleBtn = document.getElementById('mySectionToggle');

    // Initially hidden
    expect(section?.classList.contains('hidden')).toBe(true);

    toggleSection('mySection');

    expect(section?.classList.contains('hidden')).toBe(false);
    expect(toggleBtn?.textContent).toBe('▼');
    expect(toggleBtn?.classList.contains('-rotate-90')).toBe(false);

    toggleSection('mySection');

    expect(section?.classList.contains('hidden')).toBe(true);
    expect(toggleBtn?.textContent).toBe('▶');
    expect(toggleBtn?.classList.contains('-rotate-90')).toBe(true);
  });

  it('clearLog should clear output div and storage', () => {
    const { clearLog } = window as any;
    const output = document.getElementById('output') as HTMLElement;
    output.innerHTML = '<div>Some log</div>';
    localStorage.setItem('foamflask_console_log', '<div>Some log</div>');

    clearLog();

    expect(output.innerHTML).toBe('');
    expect(localStorage.getItem('foamflask_console_log')).toBeNull();

    // Should show notification
    const container = document.getElementById('notificationContainer');
    expect(container?.textContent).toContain('Console log cleared');
  });

  it('scrollToLogBottom should scroll output to bottom', () => {
    const { scrollToLogBottom } = window as any;
    const output = document.getElementById('output') as HTMLElement;

    // Mock scrollHeight
    Object.defineProperty(output, 'scrollHeight', { value: 1000, configurable: true });
    Object.defineProperty(output, 'scrollTop', { value: 0, writable: true });
    // Mock scrollTo
    output.scrollTo = vi.fn((options: any) => {
        if (options && typeof options === 'object') {
            output.scrollTop = options.top;
        }
    });

    scrollToLogBottom();

    expect(output.scrollTo).toHaveBeenCalledWith({ top: 1000, behavior: 'smooth' });
    expect(output.scrollTop).toBe(1000);
  });
});
