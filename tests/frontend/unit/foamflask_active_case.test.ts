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

describe('FoamFlask Active Case Badge', () => {
  beforeEach(async () => {
    vi.resetModules();
    document.body.innerHTML = `
      <div id="nav-setup"></div>
      <div id="page-setup"></div>
      <div id="activeCaseBadge" class="hidden"></div>
      <select id="caseSelect"><option value="">-- Select --</option></select>
      <input id="caseDir" />
      <input id="dockerImage" />
      <input id="openfoamRoot" />
      <div id="notificationContainer"></div>
      <template id="notification-template">
        <div class="notification"></div>
      </template>
      <div id="output"></div>
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

    await import('../../../static/ts/foamflask_frontend.ts');
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('selectCase should update activeCaseBadge visibility and text', () => {
    const { selectCase } = window as any;
    const badge = document.getElementById('activeCaseBadge');

    // Initial state
    expect(badge?.classList.contains('hidden')).toBe(true);

    // Select a case
    selectCase('my_test_case');

    expect(badge?.classList.contains('hidden')).toBe(false);
    expect(badge?.textContent).toContain('📂 my_test_case');

    // Deselect (simulating empty string)
    selectCase('');
    expect(badge?.classList.contains('hidden')).toBe(true);
  });
});
