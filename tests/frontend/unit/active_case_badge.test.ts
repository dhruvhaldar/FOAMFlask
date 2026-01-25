
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
  loadContourMesh: vi.fn(),
}));

describe('Active Case Badge', () => {
  beforeEach(async () => {
    vi.resetModules();
    // Reset DOM with just what we need
    document.body.innerHTML = `
      <div id="activeCaseBadge" class="hidden opacity-0">
        <span id="activeCaseName"></span>
      </div>
      <select id="caseSelect"><option value="">-- Select --</option></select>

      <!-- Mock other required elements to avoid null errors during init -->
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

      <div id="output"></div>
      <div id="notificationContainer"></div>
      <template id="notification-template"><div class="notification"></div></template>

      <!-- Needed for init -->
      <input id="caseDir" />
      <input id="dockerImage" />
      <input id="openfoamRoot" />
      <input id="newCaseName" />
      <select id="tutorialSelect"><option value="tut1">Tut 1</option></select>
      <select id="geometrySelect"><option value="">-- Select Geometry --</option></select>
      <input id="bmCells" />
      <input id="bmGrading" />
      <input id="bmMin" />
      <input id="bmMax" />
      <input id="shmLocation" />
    `;

    // Mock LocalStorage
    const localStorageMock = (function() {
      let store: any = {};
      return {
        getItem: function(key: string) { return store[key] || null; },
        setItem: function(key: string, value: string) { store[key] = value.toString(); },
        removeItem: function(key: string) { delete store[key]; },
        clear: function() { store = {}; }
      };
    })();
    Object.defineProperty(window, 'localStorage', { value: localStorageMock });

    // Mock fetch
    global.fetch = vi.fn((url) => {
        if (url && url.toString().includes('/api/cases/list')) {
             return Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ cases: ['Restored Case'] })
             });
        }
        return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ cases: [], caseDir: '/tmp', dockerImage: 'img', openfoamVersion: 'v1' })
        });
    }) as any;

    await import('../../../static/ts/foamflask_frontend.ts');
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('updateActiveCaseBadge should update text and visibility', () => {
    const { updateActiveCaseBadge } = window as any;
    const badge = document.getElementById('activeCaseBadge');
    const nameSpan = document.getElementById('activeCaseName');

    // Initially hidden
    expect(badge?.classList.contains('opacity-0')).toBe(true);

    // Update with a case name
    updateActiveCaseBadge('Test Case 1');

    expect(nameSpan?.textContent).toBe('Test Case 1');
    expect(badge?.classList.contains('opacity-0')).toBe(false);

    // Clear case name (should hide)
    updateActiveCaseBadge('');
    expect(badge?.classList.contains('opacity-0')).toBe(true);
  });

  it('selectCase should trigger badge update', () => {
    const { selectCase } = window as any;
    const badge = document.getElementById('activeCaseBadge');
    const nameSpan = document.getElementById('activeCaseName');

    selectCase('Selected Case');

    expect(nameSpan?.textContent).toBe('Selected Case');
    expect(badge?.classList.contains('opacity-0')).toBe(false);
    expect(localStorage.getItem('lastSelectedCase')).toBe('Selected Case');
  });

  it('should restore badge from localStorage on load', async () => {
    // Setup localStorage BEFORE triggering load
    localStorage.setItem('lastSelectedCase', 'Restored Case');

    // We need to manually populate the select options so the restoration logic works
    const select = document.getElementById('caseSelect') as HTMLSelectElement;
    const option = document.createElement('option');
    option.value = 'Restored Case';
    select.appendChild(option);

    // Trigger onload manually since jsdom doesn't do it automatically for us after test setup
    if (window.onload) {
       await (window.onload as any)();
    }

    const badge = document.getElementById('activeCaseBadge');
    const nameSpan = document.getElementById('activeCaseName');

    expect(nameSpan?.textContent).toBe('Restored Case');
    expect(badge?.classList.contains('opacity-0')).toBe(false);
  });
});
