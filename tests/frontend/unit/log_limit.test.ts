import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock Plotly before import
vi.mock('plotly.js', () => ({}));

describe('Log Limiting', () => {
    beforeEach(async () => {
        vi.resetModules();
        // Reset DOM
        document.body.innerHTML = `
            <div id="output"></div>
            <div id="notificationContainer"></div>
            <template id="notification-template">
                <div class="notification">
                    <div class="icon-slot"></div>
                    <div class="message-slot"></div>
                    <div class="progress-bar hidden"></div>
                    <button class="close-btn"></button>
                </div>
            </template>
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

        // Import frontend
        await import('../../../static/ts/foamflask_frontend.ts');
    });

    afterEach(() => {
        vi.restoreAllMocks();
        document.body.innerHTML = '';
    });

    it('runCommand should handle log output', async () => {
        const { runCommand } = window as any;
        const output = document.getElementById('output') as HTMLElement;

        // Mock fetch to return stream for /run and empty json for others
        global.fetch = vi.fn().mockImplementation((url) => {
            if (url === '/run') {
                const stream = new ReadableStream({
                    start(controller) {
                        // Send data
                        let text = "";
                        for (let i = 0; i < 100; i++) {
                            text += `Line ${i}\n`;
                        }
                        controller.enqueue(new TextEncoder().encode(text));
                        controller.close();
                    }
                });
                return Promise.resolve({
                    ok: true,
                    body: stream
                });
            }
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve({})
            });
        });

        // Mock tutorial select value
        const select = document.getElementById('tutorialSelect') as HTMLSelectElement;
        if (select) {
             const opt = document.createElement('option');
             opt.value = 'tut1';
             select.appendChild(opt);
             select.value = 'tut1';
        }

        // Run command
        await runCommand('test_cmd');

        // Check size
        expect(output.childElementCount).toBe(100);

        // Also check that we kept the *latest* lines
        expect(output.lastElementChild?.textContent).toContain('Line 99');
    });
});
