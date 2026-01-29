
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('Fullscreen Toggle', () => {
  beforeEach(async () => {
    vi.resetModules();
    document.body.innerHTML = `
      <div id="geometryViewerContainer" class="w-full lg:w-2/3 rounded-lg overflow-hidden relative" style="min-height: 500px">
        <button id="fullscreenBtn"></button>
      </div>
    `;
    await import('../../../static/ts/foamflask_frontend.ts');
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.restoreAllMocks();
  });

  it('toggleFullscreen should switch to fullscreen mode and back', () => {
    const { toggleFullscreen } = window as any;
    const container = document.getElementById('geometryViewerContainer') as HTMLElement;
    const btn = document.getElementById('fullscreenBtn') as HTMLElement;

    // Initial State
    expect(container.classList.contains('fixed')).toBe(false);
    expect(container.classList.contains('w-full')).toBe(true);

    // Enter Fullscreen
    toggleFullscreen('geometryViewerContainer', btn);

    // Check classes
    expect(container.classList.contains('fixed')).toBe(true);
    expect(container.classList.contains('inset-0')).toBe(true);
    expect(container.classList.contains('z-[100]')).toBe(true);
    expect(container.classList.contains('w-screen')).toBe(true);
    expect(container.classList.contains('h-screen')).toBe(true);
    // Should NOT contain original layout classes if we replaced className
    // The implementation replaces className completely for fullscreen
    expect(container.classList.contains('relative')).toBe(false);

    // Check styles
    expect(container.style.minHeight).toMatch(/^0(px)?$/);

    // Check button update (icon changed)
    expect(btn.getAttribute('aria-label')).toBe('Exit Fullscreen');

    // Exit Fullscreen
    toggleFullscreen('geometryViewerContainer', btn);

    // Check restoration
    expect(container.classList.contains('fixed')).toBe(false);
    expect(container.classList.contains('relative')).toBe(true);
    expect(container.classList.contains('w-full')).toBe(true);

    // Check style restoration
    expect(container.style.minHeight).toBe('500px');

    // Check button update
    expect(btn.getAttribute('aria-label')).toBe('Enter Fullscreen');
  });

  it('toggleFullscreen should exit on Escape key', () => {
    const { toggleFullscreen } = window as any;
    const container = document.getElementById('geometryViewerContainer') as HTMLElement;
    const btn = document.getElementById('fullscreenBtn') as HTMLElement;

    // Enter Fullscreen
    toggleFullscreen('geometryViewerContainer', btn);
    expect(container.classList.contains('fixed')).toBe(true);

    // Simulate Escape key
    const escapeEvent = new KeyboardEvent('keydown', { key: 'Escape' });
    document.dispatchEvent(escapeEvent);

    // Should be back to normal
    expect(container.classList.contains('fixed')).toBe(false);
    expect(container.classList.contains('relative')).toBe(true);
  });
});
