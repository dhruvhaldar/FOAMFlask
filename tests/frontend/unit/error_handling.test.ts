
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

describe('Error Swallowing Reproduction', () => {
  beforeEach(async () => {
    // Reset DOM
    document.body.innerHTML = `
      <div id="notificationContainer"></div>
      <template id="notification-template">
        <div class="notification">
          <div class="message-slot"></div>
          <button class="close-btn"></button>
        </div>
      </template>
      <input id="dockerImage" value="test/image" />
      <input id="openfoamVersion" value="v1" />
      <input id="openfoamRoot" />
      <button id="loadTutorialBtn"></button>
      <select id="tutorialSelect"><option value="tut1">Tut 1</option></select>
      <input id="caseDir" value="/tmp/test" />
      <button id="setRootBtn"></button>
    `;

    // Mock LocalStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      },
      writable: true
    });

    await import('../../../static/ts/foamflask_frontend.ts');

    // Mock fetch
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('setDockerConfig should show specific error message', async () => {
    const { setDockerConfig } = window as any;
    const errorMsg = "Specific Docker Error";

    // Mock fetch to return 400 with specific error
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 400,
      json: () => Promise.resolve({ output: errorMsg }),
    });

    await setDockerConfig('bad/image', 'v1');

    // Check notification
    const container = document.getElementById('notificationContainer');
    const notification = container?.querySelector('.notification');
    expect(notification).toBeTruthy();
    expect(notification?.querySelector('.message-slot')?.textContent).toContain(errorMsg);
  });

  it('loadTutorial should show specific error message', async () => {
    const { loadTutorial } = window as any;
    const errorMsg = "Specific Tutorial Error";

    // Mock fetch to return 400 with specific error
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 400,
      json: () => Promise.resolve({ output: errorMsg }),
    });

    await loadTutorial();

    const container = document.getElementById('notificationContainer');
    const notifications = container?.querySelectorAll('.notification');
    let foundError = false;
    notifications?.forEach(n => {
        if (n.querySelector('.message-slot')?.textContent?.includes(errorMsg)) {
            foundError = true;
        }
    });
    expect(foundError).toBe(true);
  });

  it('setCase should show specific error message via fetchWithCache', async () => {
    const { setCase } = window as any;
    const errorMsg = "Specific Case Error";

    // Mock fetch to return 400 with specific error
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 400,
      json: () => Promise.resolve({ output: errorMsg }),
    });

    // setCase is not async, so we need to wait for the promise to settle
    setCase();
    await new Promise(resolve => setTimeout(resolve, 50));

    const container = document.getElementById('notificationContainer');
    let foundError = false;

    container?.querySelectorAll('.notification').forEach(n => {
        const text = n.querySelector('.message-slot')?.textContent || "";
        if (text.includes(errorMsg)) foundError = true;
    });

    expect(foundError).toBe(true);
  });
});
