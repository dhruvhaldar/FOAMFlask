"use strict";
/**
 * Contour Visualization Module
 * Handles isosurface generation and 3D visualization using PyVista
 */
// Global state
let currentContourData = null;
/**
 * Generate isosurface contours for the loaded mesh
 * @param options - Configuration options
 * @returns Promise that resolves when contours are generated
 */
async function generateContours(options = {}) {
    const contourPlaceholder = document.getElementById('contourPlaceholder');
    const contourViewer = document.getElementById('contourViewer');
    // Default options
    const { tutorial = null, caseDir = null, scalarField = 'U_Magnitude', numIsosurfaces = 10 } = options;
    try {
        // Show loading state
        showLoadingState(contourViewer, 'Generating contours...');
        contourPlaceholder?.classList.add('hidden');
        contourViewer?.classList.remove('hidden');
        // Get tutorial from select if not provided
        const selectedTutorial = tutorial || getTutorialFromSelect();
        if (!selectedTutorial) {
            throw new Error('Please select a tutorial first');
        }
        // Get case directory - handle both object and string cases
        let selectedCaseDir = '';
        // If caseDir is provided as an object with a 'value' property, use that
        if (caseDir && typeof caseDir === 'object' && 'value' in caseDir) {
            selectedCaseDir = caseDir.value || '';
        }
        // If it's already a string, use it directly
        else if (typeof caseDir === 'string') {
            selectedCaseDir = caseDir;
        }
        // If we still don't have a directory, try to get it from the input field
        if (!selectedCaseDir) {
            const caseDirInput = document.getElementById('caseDir');
            if (caseDirInput) {
                selectedCaseDir = caseDirInput.value || '';
            }
        }
        // If we still don't have a valid directory, throw an error
        if (!selectedCaseDir) {
            throw new Error('Case directory not set. Please set it in the Setup page.');
        }
        // Ensure it's a string (in case it was a number or something else)
        selectedCaseDir = String(selectedCaseDir).trim();
        // Log the value we're using for debugging
        console.log('[FOAMFlask] [generateContours] Using case directory:', selectedCaseDir);
        // Get range from input fields if not provided in options
        let range = options.range;
        if (!range) {
            const rangeMinInput = document.getElementById('rangeMin');
            const rangeMaxInput = document.getElementById('rangeMax');
            const rangeMin = rangeMinInput?.value ? parseFloat(rangeMinInput.value) : null;
            const rangeMax = rangeMaxInput?.value ? parseFloat(rangeMaxInput.value) : null;
            if (rangeMin !== null && rangeMax !== null && !isNaN(rangeMin) && !isNaN(rangeMax) && rangeMin < rangeMax) {
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
        // Prepare request data with all parameters
        const requestData = {
            tutorial: selectedTutorial,
            caseDir: selectedCaseDir,
            scalarField: scalarField,
            numIsosurfaces: numIsosurfaces
        };
        // Add range to request if available
        if (range && Array.isArray(range) && range.length === 2) {
            requestData.range = range;
            console.log('[FOAMFlask] [generateContours] Using range:', range);
        }
        console.log('[FOAMFlask] [generateContours] Request data with range:', requestData);
        // Make the API request directly (send data in body, not URL params)
        console.log('[FOAMFlask] [generateContours] Calling fetchContours...');
        const response = await fetchContours(requestData);
        // Handle response - IMPORTANT: await the text() call
        console.log('[FOAMFlask] [generateContours] Reading response content...');
        const htmlContent = await response.text();
        console.log('[FOAMFlask] [generateContours] Received HTML length:', htmlContent.length);
        // Display the visualization
        console.log('[FOAMFlask] [generateContours] Displaying visualization...');
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
    }
    catch (error) {
        console.error('[FOAMFlask] [generateContours] Error:', error);
        handleContourError(contourPlaceholder, contourViewer, error);
    }
}
/**
 * Show loading state in the viewer
 */
function showLoadingState(container, message = 'Loading...') {
    if (!container)
        return;
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
function getTutorialFromSelect() {
    const tutorialSelect = document.getElementById('tutorialSelect');
    return tutorialSelect ? tutorialSelect.value : null;
}
/**
 * Fetch contours from the server
 * Send all data in the request body to avoid URL encoding issues with Windows paths
 */
async function fetchContours(requestData) {
    const url = new URL('/api/contours/create', window.location.origin);
    console.log('[FOAMFlask] [fetchContours] URL:', url.toString());
    console.log('[FOAMFlask] [fetchContours] Origin:', window.location.origin);
    console.log('[FOAMFlask] [fetchContours] Request data:', requestData);
    // Prepare the request body with all parameters
    const requestBody = {
        tutorial: requestData.tutorial,
        caseDir: requestData.caseDir,
        scalar_field: requestData.scalarField,
        num_isosurfaces: requestData.numIsosurfaces
    };
    // Add range to the request body if provided
    if (requestData.range && Array.isArray(requestData.range) && requestData.range.length === 2) {
        requestBody.range = requestData.range;
        console.log('[FOAMFlask] [fetchContours] Including range in request:', requestData.range);
    }
    const body = JSON.stringify(requestBody);
    console.log('[FOAMFlask] [fetchContours] Request body:', body);
    try {
        console.log('[FOAMFlask] [fetchContours] Sending fetch request...');
        const response = await fetch(url.toString(), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/html, application/xhtml+xml'
            },
            body: body,
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
        console.log('[FOAMFlask] [fetchContours] Response OK, returning response object');
        return response;
    }
    catch (error) {
        console.error('[FOAMFlask] [fetchContours] Fetch failed:', error);
        // Provide detailed error info
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
function displayContourVisualization(container, htmlContent) {
    if (!container) {
        console.error('[FOAMFlask] [displayContourVisualization] Container not found');
        return;
    }
    try {
        console.log('[FOAMFlask] [displayContourVisualization] Displaying content...');
        console.log('[FOAMFlask] [displayContourVisualization] HTML content length:', htmlContent.length);
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
        // Add the iframe to the container
        container.appendChild(iframe);
        console.log('[FOAMFlask] [displayContourVisualization] iframe created and added');
        // Write the content to the iframe
        const iframeDoc = iframe.contentDocument || (iframe.contentWindow && iframe.contentWindow.document);
        if (!iframeDoc) {
            console.error('[FOAMFlask] [displayContourVisualization] iframe document not available');
            return;
        }
        iframeDoc.open();
        iframeDoc.write(htmlContent);
        iframeDoc.close();
        console.log('[FOAMFlask] [displayContourVisualization] Content written to iframe');
        // Wait for iframe to stabilize
        iframe.onload = function () {
            console.log('[FOAMFlask] [displayContourVisualization] iframe loaded');
            try {
                // Trigger resize event to ensure proper rendering
                if (iframe.contentWindow) {
                    iframe.contentWindow.dispatchEvent(new Event('resize'));
                    console.log('[FOAMFlask] [displayContourVisualization] Resize event triggered in iframe');
                }
            }
            catch (e) {
                console.error('[FOAMFlask] [displayContourVisualization] Error triggering resize:', e);
            }
        };
        // Also trigger resize after a delay to ensure content is ready
        setTimeout(() => {
            console.log('[FOAMFlask] [displayContourVisualization] Delayed resize trigger');
            window.dispatchEvent(new Event('resize'));
            try {
                if (iframe.contentWindow) {
                    iframe.contentWindow.dispatchEvent(new Event('resize'));
                }
            }
            catch (e) {
                console.warn('[FOAMFlask] [displayContourVisualization] Could not trigger iframe resize:', e);
            }
        }, 500);
        console.log('[FOAMFlask] [displayContourVisualization] Display setup complete');
    }
    catch (error) {
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
function handleContourError(placeholder, viewer, error) {
    // Show error message
    if (placeholder)
        placeholder.classList.remove('hidden');
    if (viewer)
        viewer.classList.add('hidden');
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    console.error('[FOAMFlask] [handleContourError] Error details:', {
        message: errorMessage,
        stack: error instanceof Error ? error.stack : undefined
    });
    // Show notification
    if (typeof showNotification === 'function') {
        showNotification(`Error generating contours: ${errorMessage}`, 'error');
    }
    // Update the viewer with error details
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
async function generateContoursWithParams() {
    try {
        const scalarFieldSelect = document.getElementById('scalarField');
        const numIsosurfacesInput = document.getElementById('numIsosurfaces');
        const scalarField = scalarFieldSelect?.value || 'U_Magnitude';
        const numIsosurfaces = numIsosurfacesInput?.value ? parseInt(numIsosurfacesInput.value, 10) : 5;
        console.log('[FOAMFlask] [generateContoursWithParams] Generating contours with parameters:', {
            scalarField,
            numIsosurfaces
        });
        // Let generateContours handle the range from input fields
        await generateContours({
            scalarField,
            numIsosurfaces
        });
    }
    catch (error) {
        console.error('[FOAMFlask] [generateContoursWithParams] Error:', error);
        if (typeof showNotification === 'function') {
            const message = error instanceof Error ? error.message : String(error);
            showNotification(`Error: ${message}`, 'error');
        }
    }
}
/**
 * Download contour visualization as image
 */
function downloadContourImage() {
    if (!currentContourData) {
        if (typeof showNotification === 'function') {
            showNotification('No contour visualization available to download', 'warning');
        }
        return;
    }
    // Get the contour viewer element
    const contourViewer = document.getElementById('contourViewer');
    if (!contourViewer)
        return;
    // Try to find canvas element in the viewer
    const canvas = contourViewer.querySelector('canvas');
    if (!canvas) {
        if (typeof showNotification === 'function') {
            showNotification('Cannot download: visualization not rendered as canvas', 'error');
        }
        return;
    }
    try {
        // Convert canvas to blob and download
        canvas.toBlob((blob) => {
            if (!blob) {
                if (typeof showNotification === 'function') {
                    showNotification('Failed to create image blob', 'error');
                }
                return;
            }
            if (!currentContourData) {
                return;
            }
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `contour_${currentContourData.scalarField}_${Date.now()}.png`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            if (typeof showNotification === 'function') {
                showNotification('Contour image downloaded successfully', 'success');
            }
        });
    }
    catch (error) {
        console.error('[FOAMFlask] Error downloading contour image:', error);
        if (typeof showNotification === 'function') {
            showNotification('Failed to download contour image', 'error');
        }
    }
}
/**
 * Export contour data as JSON
 */
function exportContourData() {
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
function resetContourViewer() {
    const contourPlaceholder = document.getElementById('contourPlaceholder');
    const contourViewer = document.getElementById('contourViewer');
    if (contourPlaceholder)
        contourPlaceholder.classList.remove('hidden');
    if (contourViewer) {
        contourViewer.classList.add('hidden');
        contourViewer.innerHTML = '';
    }
    currentContourData = null;
}
// Add event listener for the RangeBtn when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    const rangeBtn = document.getElementById('RangeBtn');
    const rangeMinInput = document.getElementById('rangeMin');
    const rangeMaxInput = document.getElementById('rangeMax');
    if (rangeBtn && rangeMinInput && rangeMaxInput) {
        rangeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const rangeMin = rangeMinInput.value ? parseFloat(rangeMinInput.value) : null;
            const rangeMax = rangeMaxInput.value ? parseFloat(rangeMaxInput.value) : null;
            if (rangeMin === null || rangeMax === null || isNaN(rangeMin) || isNaN(rangeMax)) {
                console.log('[FOAMFlask] Invalid range values');
                if (typeof showNotification === 'function') {
                    showNotification('Please enter valid range values', 'warning');
                }
                return;
            }
            if (rangeMin >= rangeMax) {
                console.log('[FOAMFlask] Range min must be less than max');
                if (typeof showNotification === 'function') {
                    showNotification('Range min must be less than max', 'warning');
                }
                return;
            }
            console.log(`[FOAMFlask] Range set to [${rangeMin}, ${rangeMax}]`);
            if (typeof showNotification === 'function') {
                showNotification(`Range set to [${rangeMin.toFixed(4)}, ${rangeMax.toFixed(4)}]`, 'success');
            }
            // The range values will be used the next time Generate Contours is clicked
        });
    }
});
// Export functions for use in other modules (if using ES6 modules)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        generateContours,
        generateContoursWithParams,
        downloadContourImage,
        exportContourData,
        resetContourViewer
    };
}
//# sourceMappingURL=isosurface.js.map