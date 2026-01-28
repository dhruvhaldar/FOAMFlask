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
        `; // Add tutorialSelect to avoid null check errors in runCommand

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

    it('runCommand should limit log size to 2500 lines', async () => {
        const { runCommand } = window as any;
        const output = document.getElementById('output') as HTMLElement;

        // Create a mock stream that yields 3000 chunks
        const stream = new ReadableStream({
            start(controller) {
                for (let i = 0; i < 3000; i++) {
                    const chunk = new TextEncoder().encode(`<div>Line ${i}</div>\n`);
                    controller.enqueue(chunk);
                }
                controller.close();
            }
        });

        // Mock fetch to return this stream
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            body: stream
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
        // Currently it should be 3000 (failing test)
        expect(output.childElementCount).toBeLessThanOrEqual(2500);

        // Also check that we kept the *latest* lines
        expect(output.lastElementChild?.textContent).toContain('Line 2999');
    });
});
