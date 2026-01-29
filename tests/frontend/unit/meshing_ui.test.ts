
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

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

describe('Meshing UI UX', () => {
  beforeEach(async () => {
    vi.resetModules();
    document.body.innerHTML = `
      <input type="checkbox" id="shmLayers" />
      <input id="shmObjLayers" />
      <select id="tutorialSelect"><option value="">-- Select --</option></select>
    `;

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

    // Mock fetch
    global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ files: [], cases: [] })
    });

    // Import the frontend script to run initialization
    await import('../../../static/ts/foamflask_frontend.ts');
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('shmObjLayers should be disabled when shmLayers is unchecked', () => {
    const shmLayers = document.getElementById('shmLayers') as HTMLInputElement;
    const shmObjLayers = document.getElementById('shmObjLayers') as HTMLInputElement;

    // Trigger initialization (if any logic is added to init)
    // The import above runs top-level code and window.onload if configured.
    // We might need to manually trigger the logic or verify if init runs it.
    // For now, let's assume the init logic should run on load.

    // Force a change event to be sure, in case init doesn't catch it yet (since we haven't implemented it)
    // But testing "by default" requires init logic.

    // Let's assert state.
    // shmLayers is unchecked by default in HTML.

    expect(shmLayers.checked).toBe(false);
    expect(shmObjLayers.disabled).toBe(true); // Expect to be disabled
    expect(shmObjLayers.classList.contains('cursor-not-allowed')).toBe(true); // Visual feedback
  });

  it('shmObjLayers should toggle when shmLayers changes', () => {
    const shmLayers = document.getElementById('shmLayers') as HTMLInputElement;
    const shmObjLayers = document.getElementById('shmObjLayers') as HTMLInputElement;

    // Simulate checking the box
    shmLayers.checked = true;
    shmLayers.dispatchEvent(new Event('change'));

    expect(shmObjLayers.disabled).toBe(false);
    expect(shmObjLayers.classList.contains('cursor-not-allowed')).toBe(false);

    // Simulate unchecking
    shmLayers.checked = false;
    shmLayers.dispatchEvent(new Event('change'));

    expect(shmObjLayers.disabled).toBe(true);
    expect(shmObjLayers.classList.contains('cursor-not-allowed')).toBe(true);
  });
});
