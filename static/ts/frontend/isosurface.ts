/**
 * Contour Visualization Module
 * Handles isosurface generation and 3D visualization using PyVista
 */

// Type definitions
interface ContourOptions {
    tutorial?: string | null;
    caseDir?: string | { value: string } | null;
    scalarField?: string;
    numIsosurfaces?: number;
    range?: [number, number];
}

interface ContourData {
    tutorial: string;
    caseDir: string;
    scalarField: string;
    numIsosurfaces: number;
    timestamp: string;
}

// Extend HTMLElement for custom properties
interface MyHTMLElement extends HTMLElement {
    value: string;
}

// Assume global functions are declared elsewhere
declare function showNotification(message: string, type?: string, duration?: number): void;

// Global state
let currentContourData: ContourData | null = null;

/**
 * Generate isosurface contours for the loaded mesh
 * @param options - Configuration options
 * @returns Promise that resolves when contours are generated
 */
export async function generateContours(options: ContourOptions = {}): Promise<void> {
    const contourPlaceholder = document.getElementById('contourPlaceholder');
    const contourViewer = document.getElementById('contourViewer');

    // Default options
    const {
        tutorial = null,
        caseDir = null,
        scalarField = 'U_Magnitude',
        numIsosurfaces = 10
    } = options;

    try {
        // Show loading state
        showLoadingState(contourViewer, 'Generating contours...');
        contourPlaceholder?.classList.add('hidden');
        contourViewer?.classList.remove('hidden');

        // Get tutorial from select if not provided
        const selectedTutorial: string = tutorial ?? getTutorialFromSelect() ?? '';
        if (!selectedTutorial) {
            throw new Error('Please select a tutorial first');
        }

        // Get case directory - handle both object and string cases
        let selectedCaseDir = '';
        if (caseDir && typeof caseDir === 'object' && 'value' in caseDir) {
            selectedCaseDir = (caseDir as { value: string }).value || '';
        } else if (typeof caseDir === 'string') {
            selectedCaseDir = caseDir;
        }

        // Try to get from the input field if still not available
        if (!selectedCaseDir) {
            const caseDirInput = document.getElementById('caseDir') as MyHTMLElement | null;
            if (caseDirInput) {
                selectedCaseDir = caseDirInput.value || '';
            }
        }

        if (!selectedCaseDir) {
            throw new Error('Case directory not set. Please set it in the Setup page.');
        }

        selectedCaseDir = String(selectedCaseDir).trim();

        // Log for debugging
        console.log('[FOAMFlask] [generateContours] Using case directory:', selectedCaseDir);

        // Get range from input fields if not provided in options
        let range = options.range;
        if (!range) {
            const rangeMinInput = document.getElementById('rangeMin') as MyHTMLElement | null;
            const rangeMaxInput = document.getElementById('rangeMax') as MyHTMLElement | null;
            const rangeMin = rangeMinInput?.value ? parseFloat(rangeMinInput.value) : null;
            const rangeMax = rangeMaxInput?.value ? parseFloat(rangeMaxInput.value) : null;

            if (
                rangeMin !== null &&
                rangeMax !== null &&
                !isNaN(rangeMin) &&
                !isNaN(rangeMax) &&
                rangeMin < rangeMax
            ) {
                range = [rangeMin, rangeMax];
                console.log('[FOAMFlask] [generateContours] Using range from input fields:', range);
            }
        }

        console.log('[FOAMFlask] [generateContours] Request parameters:', {
            tutorial: selectedTutorial,
            caseDir: selectedCaseDir,
            scalarField,
            numIsosurfaces,
            range
        });

        // Prepare request data
        const requestData: ContourOptions = {
            tutorial: selectedTutorial,
            caseDir: selectedCaseDir,
            scalarField,
            numIsosurfaces
        };

        if (range && Array.isArray(range) && range.length === 2) {
            requestData.range = range;
            console.log('[FOAMFlask] [generateContours] Using range:', range);
        }

        console.log('[FOAMFlask] [generateContours] Request data with range:', requestData);

        // API request (send as POST body)
        console.log('[FOAMFlask] [generateContours] Calling fetchContours...');
        const response = await fetchContours(requestData);

        // Await the response text
        console.log('[FOAMFlask] [generateContours] Reading response content...');
        const htmlContent = await response.text();
        console.log('[FOAMFlask] [generateContours] Received HTML length:', htmlContent.length);

        // Display the visualization
        displayContourVisualization(contourViewer, htmlContent);

        // Store current data for export
        currentContourData = {
            tutorial: selectedTutorial,
            caseDir: selectedCaseDir,
            scalarField,
            numIsosurfaces,
            timestamp: new Date().toISOString()
        };

        console.log('[FOAMFlask] [generateContours] Contours generated successfully!');

        if (typeof showNotification === 'function') {
            showNotification('Contours generated successfully!', 'success');
        }

    } catch (error: unknown) {
        console.error('[FOAMFlask] [generateContours] Error:', error);
        handleContourError(contourPlaceholder, contourViewer, error);
    }
}

/**
 * Show loading state in the viewer
 */
function showLoadingState(container: HTMLElement | null, message = 'Loading...') {
    if (!container) return;

    container.innerHTML = `
        <div class="flex items-center justify-center h-full">
            <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            <span class="ml-4 text-gray-600">${message}</span>
        </div>
    `;
}

/**
 * Get selected tutorial from dropdown
 */
function getTutorialFromSelect(): string | null {
    const tutorialSelect = document.getElementById('tutorialSelect') as MyHTMLElement | null;
    return tutorialSelect ? tutorialSelect.value : null;
}

/**
 * Fetch contours from the server
 * Send all data in the request body to avoid URL encoding issues with Windows paths
 */
async function fetchContours(requestData: ContourOptions) {
    const url = new URL('/api/contours/create', window.location.origin);

    console.log('[FOAMFlask] [fetchContours] URL:', url.toString());
    console.log('[FOAMFlask] [fetchContours] Origin:', window.location.origin);
    console.log('[FOAMFlask] [fetchContours] Request data:', requestData);

    // Prepare the request body
    const requestBody: {
        tutorial?: string | null;
        caseDir?: string | { value: string } | null;
        scalar_field?: string;
        num_isosurfaces?: number;
        range?: [number, number];
    } = {
        tutorial: requestData.tutorial,
        caseDir: requestData.caseDir,
        scalar_field: requestData.scalarField,
        num_isosurfaces: requestData.numIsosurfaces
    };

    if (requestData.range && Array.isArray(requestData.range) && requestData.range.length === 2) {
        requestBody.range = requestData.range;
        console.log('[FOAMFlask] [fetchContours] Including range in request:', requestData.range);
    }

    const body = JSON.stringify(requestBody);

    try {
        console.log('[FOAMFlask] [fetchContours] Sending fetch request...');

        const response = await fetch(url.toString(), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/html, application/xhtml+xml'
            },
            body,
            mode: 'cors',
            credentials: 'same-origin'
        });

        console.log('[FOAMFlask] [fetchContours] Response received');
        console.log('[FOAMFlask] [fetchContours] Status:', response.status);
        console.log('[FOAMFlask] [fetchContours] Status text:', response.statusText);
        console.log('[FOAMFlask] [fetchContours] Content-Type:', response.headers.get('Content-Type'));

        if (!response.ok) {
            const errorText = await response.text();
            console.error('[FOAMFlask] [fetchContours] Error response:', errorText);
            throw new Error(`Server returned ${response.status}: ${errorText}`);
        }

        return response;

    } catch (error: unknown) {
        console.error('[FOAMFlask] [fetchContours] Fetch failed:', error);

        if (error instanceof Error && error.message.includes('Failed to fetch')) {
            console.error('[FOAMFlask] [fetchContours] Network error details:');
            console.error('  - Server URL:', url.toString());
            console.error('  - Your page origin:', window.location.origin);
            console.error('  - Check if Flask server is running on that address');
        }

        throw error;
    }
}

/**
 * Display the contour visualization in the viewer
 */
function displayContourVisualization(container: HTMLElement | null, htmlContent: string) {
    if (!container) {
        console.error('[FOAMFlask] [displayContourVisualization] Container not found');
        return;
    }

    try {
        // Clear the container first
        container.innerHTML = '';

        // Create an iframe to contain the visualization
        const iframe = document.createElement('iframe');
        iframe.id = 'contourVisualizationFrame';
        iframe.style.cssText = `
            width: 100%;
            height: 600px;
            border: none;
            border-radius: 0.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            background: white;
        `;

        container.appendChild(iframe);

        // Write the content to the iframe
        const iframeDoc =
            iframe.contentDocument || (iframe.contentWindow && iframe.contentWindow.document);

        if (!iframeDoc) {
            console.error('[FOAMFlask] [displayContourVisualization] iframe document not available');
            return;
        }
        iframeDoc.open();
        iframeDoc.write(htmlContent);
        iframeDoc.close();

        iframe.onload = function () {
            try {
                if (iframe.contentWindow) {
                    iframe.contentWindow.dispatchEvent(new Event('resize'));
                }
            } catch (e) {
                console.error('[FOAMFlask] [displayContourVisualization] Error triggering resize:', e);
            }
        };

        setTimeout(() => {
            try {
                window.dispatchEvent(new Event('resize'));
                if (iframe.contentWindow) {
                    iframe.contentWindow.dispatchEvent(new Event('resize'));
                }
            } catch (e) {
                console.warn('[FOAMFlask] [displayContourVisualization] Could not trigger iframe resize:', e);
            }
        }, 500);

    } catch (error: unknown) {
        console.error('[FOAMFlask] [displayContourVisualization] Error:', error);
        if (container) {
            const message = error instanceof Error ? error.message : 'Unknown error occurred';
            container.innerHTML = `
                <div class="p-4 text-red-600 bg-red-50 rounded-lg">
                    <h3 class="font-semibold">Error displaying visualization</h3>
                    <p class="text-sm mt-1">${message}</p>
                    <p class="text-xs mt-2 text-gray-600">Check browser console for details</p>
                </div>
            `;
        }
    }
}

/**
 * Handle errors during contour generation
 */
function handleContourError(
    placeholder: HTMLElement | null,
    viewer: HTMLElement | null,
    error: unknown
) {
    if (placeholder) placeholder.classList.remove('hidden');
    if (viewer) viewer.classList.add('hidden');

    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

    if (typeof showNotification === 'function') {
        showNotification(`Error generating contours: ${errorMessage}`, 'error');
    }

    if (viewer) {
        viewer.innerHTML = `
            <div class="p-8 text-center">
                <div class="text-red-600 text-lg font-semibold mb-4">
                    ⚠️ Error Generating Contours
                </div>
                <div class="text-gray-600 mb-4">
                    ${errorMessage}
                </div>
                <div class="text-sm text-gray-500 mt-4 p-4 bg-gray-50 rounded">
                    <p><strong>Troubleshooting:</strong></p>
                    <ul class="text-left mt-2">
                        <li>✓ Ensure you've selected a tutorial in the Setup page</li>
                        <li>✓ Ensure the case directory is set correctly</li>
                        <li>✓ Ensure you've run 'foamToVTK' to generate VTK files</li>
                        <li>✓ Check the browser console for more details</li>
                        <li>✓ Check the Flask server logs for backend errors</li>
                    </ul>
                </div>
                <button 
                    onclick="generateContours()" 
                    class="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                    Try Again
                </button>
            </div>
        `;
    }
}

/**
 * Generate contours with custom parameters from UI controls
 */
export async function generateContoursWithParams() {
    try {
        const scalarFieldSelect = document.getElementById('scalarField') as MyHTMLElement | null;
        const numIsosurfacesInput = document.getElementById('numIsosurfaces') as MyHTMLElement | null;

        const scalarField = scalarFieldSelect?.value || 'U_Magnitude';
        const numIsosurfaces = numIsosurfacesInput?.value ? parseInt(numIsosurfacesInput.value, 10) : 5;

        console.log('[FOAMFlask] [generateContoursWithParams] Generating contours with parameters:', {
            scalarField,
            numIsosurfaces
        });

        // Pass all required properties
        await generateContours({
            tutorial: 'defaultTutorial', // Replace with actual value if available
            caseDir: 'defaultCaseDir',   // Replace with actual value if available
            scalarField,
            numIsosurfaces
        });
    } catch (error: unknown) {
        if (typeof showNotification === 'function') {
            const message = error instanceof Error ? error.message : String(error);
            showNotification(`Error: ${message}`, 'error');
        }
    }
}

/**
 * Download contour visualization as image
 */
export function downloadContourImage() {
    if (!currentContourData) {
        if (typeof showNotification === 'function') {
            showNotification('No contour visualization available to download', 'warning');
        }
        return;
    }

    const contourViewer = document.getElementById('contourViewer');
    if (!contourViewer) return;

    const canvas = contourViewer.querySelector('canvas');
    if (!canvas) {
        if (typeof showNotification === 'function') {
            showNotification('Cannot download: visualization not rendered as canvas', 'error');
        }
        return;
    }

    try {
        canvas.toBlob((blob: Blob | null) => {
            if (!blob) {
                if (typeof showNotification === 'function') {
                    showNotification('Failed to create image blob', 'error');
                }
                return;
            }

            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            // Null check before accessing scalarField
            link.download = `contour_${currentContourData?.scalarField || 'unknown'}_${Date.now()}.png`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            if (typeof showNotification === 'function') {
                showNotification('Contour image downloaded successfully', 'success');
            }
        });
    } catch (error: unknown) {
        if (typeof showNotification === 'function') {
            showNotification('Failed to download contour image', 'error');
        }
    }
}

/**
 * Export contour data as JSON
 */
export function exportContourData() {
    if (!currentContourData) {
        if (typeof showNotification === 'function') {
            showNotification('No contour data available to export', 'warning');
        }
        return;
    }

    const dataStr = JSON.stringify(currentContourData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `contour_data_${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    if (typeof showNotification === 'function') {
        showNotification('Contour data exported successfully', 'success');
    }
}

/**
 * Reset contour viewer to initial state
 */
export function resetContourViewer() {
    const contourPlaceholder = document.getElementById('contourPlaceholder');
    const contourViewer = document.getElementById('contourViewer');

    if (contourPlaceholder) contourPlaceholder.classList.remove('hidden');
    if (contourViewer) {
        contourViewer.classList.add('hidden');
        contourViewer.innerHTML = '';
    }

    currentContourData = null;
}
