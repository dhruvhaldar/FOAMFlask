
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

describe('downloadLog', () => {
  beforeEach(() => {
    // Reset DOM
    document.body.innerHTML = `
      <div id="output">Line 1\nLine 2</div>
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
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should create a blob and trigger download', async () => {
    // We need to import the module to get the function registered on window
    await import('../../../static/ts/foamflask_frontend.ts');

    const { downloadLog } = window as any;

    if (!downloadLog) {
        // If function not implemented yet, we can skip or fail.
        // For TDD, we expect this to fail or be undefined.
        throw new Error("downloadLog not implemented yet");
    }

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
        return document.createElement(tagName); // Fallback for other elements
    });

    const appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation(() => anchorMock);
    const removeChildSpy = vi.spyOn(document.body, 'removeChild').mockImplementation(() => anchorMock);

    // Run function
    downloadLog();

    // Verify
    expect(global.URL.createObjectURL).toHaveBeenCalled();
    expect(createElementSpy).toHaveBeenCalledWith('a');
    expect(anchorMock.download).toMatch(/foamflask_log_.*\.txt/);
    expect(anchorMock.href).toBe('blob:mock-url');
    expect(document.body.appendChild).toHaveBeenCalledWith(anchorMock);
    expect(clickMock).toHaveBeenCalled();

    // Verify cleanup (might need to wait for setTimeout)
    await new Promise(resolve => setTimeout(resolve, 150));
    expect(document.body.removeChild).toHaveBeenCalledWith(anchorMock);
    expect(global.URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });

  it('should show warning if log is empty', async () => {
    await import('../../../static/ts/foamflask_frontend.ts');
    const { downloadLog } = window as any;
    if (!downloadLog) throw new Error("downloadLog not implemented yet");

    const output = document.getElementById('output');
    if (output) {
        output.innerText = '';
        output.textContent = '';
    }

    const createObjectUrlSpy = vi.spyOn(global.URL, 'createObjectURL');

    downloadLog();

    expect(createObjectUrlSpy).not.toHaveBeenCalled();

    // Check notification
    const notification = document.querySelector('.notification .message-slot');
    expect(notification?.textContent).toBe('Log is empty');
  });
});
