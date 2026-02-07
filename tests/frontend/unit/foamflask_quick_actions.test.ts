
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock dependencies
vi.mock('plotly.js', () => ({}));
vi.mock('../../static/ts/frontend/isosurface.js', () => ({}));

describe('FoamFlask Quick Actions', () => {
  beforeEach(async () => {
    document.body.innerHTML = `
      <select id="tutorialSelect"><option value="tut1">Tut 1</option></select>
      <button id="loadTutorialBtn">Load Tutorial</button>

      <input id="caseDir" />
      <button id="setRootBtn">Set Root</button>

      <select id="geometrySelect" size="5"><option value="geo1">Geo 1</option></select>
      <button id="viewGeometryBtn">View</button>

      <select id="resourceGeometrySelect"><option value="res1">Res 1</option></select>
      <button id="fetchResourceGeometryBtn">Fetch</button>

      <select id="meshSelect"><option value="mesh1">Mesh 1</option></select>
      <button id="loadMeshBtn">Load Mesh</button>

      <select id="vtkFileSelect"><option value="vtk1">VTK 1</option></select>
      <button id="loadContourVTKBtn">Load Contour</button>
    `;

    // Import the main script to trigger init() and setupQuickActions()
    const module = await import('../../../static/ts/foamflask_frontend.ts');

    if (module.init) {
        module.init();
    }
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('Pressing Enter on tutorialSelect should click loadTutorialBtn', () => {
    const input = document.getElementById('tutorialSelect')!;
    const btn = document.getElementById('loadTutorialBtn')!;
    const clickSpy = vi.spyOn(btn, 'click');

    const event = new KeyboardEvent('keydown', { key: 'Enter' });
    input.dispatchEvent(event);

    expect(clickSpy).toHaveBeenCalled();
  });

  it('Pressing Enter on caseDir should click setRootBtn', () => {
    const input = document.getElementById('caseDir')!;
    const btn = document.getElementById('setRootBtn')!;
    const clickSpy = vi.spyOn(btn, 'click');

    const event = new KeyboardEvent('keydown', { key: 'Enter' });
    input.dispatchEvent(event);

    expect(clickSpy).toHaveBeenCalled();
  });

  it('Double clicking geometrySelect should click viewGeometryBtn', () => {
    const input = document.getElementById('geometrySelect')!;
    const btn = document.getElementById('viewGeometryBtn')!;
    const clickSpy = vi.spyOn(btn, 'click');

    const event = new MouseEvent('dblclick');
    input.dispatchEvent(event);

    expect(clickSpy).toHaveBeenCalled();
  });

  it('Pressing Enter on geometrySelect should click viewGeometryBtn', () => {
    const input = document.getElementById('geometrySelect')!;
    const btn = document.getElementById('viewGeometryBtn')!;
    const clickSpy = vi.spyOn(btn, 'click');

    const event = new KeyboardEvent('keydown', { key: 'Enter' });
    input.dispatchEvent(event);

    expect(clickSpy).toHaveBeenCalled();
  });

  it('Pressing Enter on meshSelect should click loadMeshBtn', () => {
    const input = document.getElementById('meshSelect')!;
    const btn = document.getElementById('loadMeshBtn')!;
    const clickSpy = vi.spyOn(btn, 'click');

    const event = new KeyboardEvent('keydown', { key: 'Enter' });
    input.dispatchEvent(event);

    expect(clickSpy).toHaveBeenCalled();
  });

  it('Pressing Enter on vtkFileSelect should click loadContourVTKBtn', () => {
    const input = document.getElementById('vtkFileSelect')!;
    const btn = document.getElementById('loadContourVTKBtn')!;
    const clickSpy = vi.spyOn(btn, 'click');

    const event = new KeyboardEvent('keydown', { key: 'Enter' });
    input.dispatchEvent(event);

    expect(clickSpy).toHaveBeenCalled();
  });
});
