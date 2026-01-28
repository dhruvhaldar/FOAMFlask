import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
// import { Window } from 'hap-dom';

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

describe('FoamFlask Frontend Pipeline', () => {

  beforeEach(async () => {
    vi.resetModules();
    // Reset DOM
    document.body.innerHTML = `
      <div id="page-post" class="page"></div>
      <div id="post-pipeline-view"></div>
      <div id="post-landing-view"></div>
      <div id="post-contour-view" class="hidden"></div>
      <select id="vtkFileSelect"></select>

      <!-- Required by other parts of init -->
      <div id="notificationContainer"></div>
      <template id="notification-template"><div class="notification"></div></template>
      <div id="caseSelect"></div>
      <div id="tutorialSelect"></div>
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

    // Load module
    await import('../../../static/ts/foamflask_frontend.ts');
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('Pipeline should start with Root node', () => {
    // Manually trigger render if not auto-triggered (it is triggered by interaction)
    // Access internal state or trigger via interaction?
    // Since state is internal, let's verify via DOM side effects of `selectPipelineStep` logic which calls render.

    // By default, init doesn't call renderPipeline immediately unless we navigate.
    // Let's assume user navigates to Post page which might init it, or we trigger an update.

    // Triggering switchPostView('landing') is effectively "Back" or init logic
    // But `switchPostView` is now logic for adding/removing.

    // Let's rely on the fact that `postPipeline` has root by default.
    // If we call `switchPostView('contour')`, it adds a node.

    const { switchPostView } = window as any;
    const container = document.getElementById('post-pipeline-view') as HTMLElement;

    // Simulate adding a contour
    switchPostView('contour');

    // Should now have Root -> Contour
    // Check buttons in pipeline container
    const buttons = container.querySelectorAll('button');
    // Expected buttons: Root(Select), Contour(Select), Contour(Delete), Add(+)
    expect(buttons.length).toBe(4);

    // Verify specific buttons exist with correct ARIA labels (Accessibility Check)
    expect(container.querySelector('button[aria-label="Select Mesh"]')).not.toBeNull();
    expect(container.querySelector('button[aria-label="Select Contour"]')).not.toBeNull();
    expect(container.querySelector('button[aria-label="Delete Contour"]')).not.toBeNull();
    expect(container.querySelector('button[aria-label="Add new step"]')).not.toBeNull();

    // Contour view should be visible
    expect(document.getElementById('post-contour-view')?.classList.contains('hidden')).toBe(false);
    expect(document.getElementById('post-landing-view')?.classList.contains('hidden')).toBe(true);
  });

  it('Back navigation should return to Root and show Landing', () => {
    const { switchPostView } = window as any;
    const container = document.getElementById('post-pipeline-view') as HTMLElement;

    // Add contour
    switchPostView('contour');

    // Click Back
    switchPostView('landing');

    // Should still have nodes (we just moved active pointer)
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBe(4); // Root(Sel), Contour(Sel), Contour(Del), Add(+) (Root is active now)

    // Active styling check (Root should be active)
    // The styling is on the wrapper div, not the button itself in the new implementation.
    // We need to find the wrapper.
    const wrappers = container.querySelectorAll('.rounded-full.border.text-sm'); // Selector matching the wrapper class
    expect(wrappers.length).toBe(2);

    expect(wrappers[0].className).toContain('bg-cyan-600');
    expect(wrappers[1].className).not.toContain('bg-cyan-600');

    // Landing view should be visible
    expect(document.getElementById('post-contour-view')?.classList.contains('hidden')).toBe(true);
    expect(document.getElementById('post-landing-view')?.classList.contains('hidden')).toBe(false);
  });

});
