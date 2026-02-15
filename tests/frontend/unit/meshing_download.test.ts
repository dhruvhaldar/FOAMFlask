
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock Plotly and isosurface before importing main module
vi.mock('plotly.js', () => ({
  react: vi.fn(),
  newPlot: vi.fn(),
  extendTraces: vi.fn(),
  toImage: vi.fn().mockResolvedValue('data:image/png;base64,mock'),
}));

vi.mock('../../../static/ts/frontend/isosurface.js', () => ({
  generateContours: vi.fn(),
  loadContourMesh: vi.fn(),
}));

describe('downloadMeshingLog', () => {
  beforeEach(async () => {
    // Reset DOM
    document.body.innerHTML = `
      <div id="meshingOutput">Meshing Output Line 1\nLine 2</div>
      <div id="notificationContainer"></div>
      <template id="notification-template">
        <div class="notification">
          <div class="icon-slot"></div>
          <div class="message-slot"></div>
          <button class="close-btn"></button>
        </div>
      </template>
    `;

    // Mock URL.createObjectURL
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = vi.fn();

    // Reset module state to ensure window functions are re-attached
    const mod = await import('../../../static/ts/foamflask_frontend.ts');
    if (mod.resetState) mod.resetState();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should create a blob and trigger download for meshing log', async () => {
    // Import module
    await import('../../../static/ts/foamflask_frontend.ts');
    const { downloadMeshingLog } = window as any;

    expect(downloadMeshingLog).toBeDefined();

    // Mock anchor element
    const clickMock = vi.fn();
    const anchorMock = {
        href: '',
        download: '',
        click: clickMock,
        style: {},
    } as unknown as HTMLAnchorElement;

    const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation((tagName) => {
        if (tagName === 'a') return anchorMock;
        return document.createElement(tagName);
    });

    const appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation(() => anchorMock);
    const removeChildSpy = vi.spyOn(document.body, 'removeChild').mockImplementation(() => anchorMock);

    // Run function
    downloadMeshingLog();

    // Verify
    expect(global.URL.createObjectURL).toHaveBeenCalled();
    expect(createElementSpy).toHaveBeenCalledWith('a');
    expect(anchorMock.download).toMatch(/meshing_log_.*\.txt/);
    expect(anchorMock.href).toBe('blob:mock-url');
    expect(document.body.appendChild).toHaveBeenCalledWith(anchorMock);
    expect(clickMock).toHaveBeenCalled();

    // Verify cleanup
    await new Promise(resolve => setTimeout(resolve, 150));
    expect(document.body.removeChild).toHaveBeenCalledWith(anchorMock);
    expect(global.URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });

  it('should show warning if meshing log is "Ready..."', async () => {
    await import('../../../static/ts/foamflask_frontend.ts');
    const { downloadMeshingLog } = window as any;

    const output = document.getElementById('meshingOutput');
    if (output) {
        output.innerText = 'Ready...';
    }

    const createObjectUrlSpy = vi.spyOn(global.URL, 'createObjectURL');

    downloadMeshingLog();

    expect(createObjectUrlSpy).not.toHaveBeenCalled();

    // Check notification
    const notification = document.querySelector('.notification .message-slot');
    expect(notification?.textContent).toBe('Log is empty');
  });
});
