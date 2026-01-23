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
export async function generateContours(options = {}) {
    const contourPlaceholder = document.getElementById('contourPlaceholder');
    const contourViewer = document.getElementById('contourViewer');
    // Default options
    const { tutorial = null, caseDir = null, scalarField = 'U_Magnitude', numIsosurfaces = 10, vtkFilePath = null } = options;
    try {
        // Show loading state
        showLoadingState(contourViewer, 'Generating contours...');
        contourPlaceholder?.classList.add('hidden');
        contourViewer?.classList.remove('hidden');
        // Get tutorial from select if not provided
        const selectedTutorial = tutorial ?? getTutorialFromSelect() ?? '';
        if (!selectedTutorial) {
            throw new Error('Please select a tutorial first');
        }
        // Get case directory - handle both object and string cases
        let selectedCaseDir = '';
        if (caseDir && typeof caseDir === 'object' && 'value' in caseDir) {
            selectedCaseDir = caseDir.value || '';
        }
        else if (typeof caseDir === 'string') {
            selectedCaseDir = caseDir;
        }
        // Try to get from the input field if still not available
        if (!selectedCaseDir) {
            const caseDirInput = document.getElementById('caseDir');
            if (caseDirInput) {
                selectedCaseDir = caseDirInput.value || '';
            }
        }
        if (!selectedCaseDir) {
            throw new Error('Case directory not set. Please set it in the Setup page.');
        }
        selectedCaseDir = String(selectedCaseDir).trim();
        // Get VTK file path if not provided
        let selectedVtkFilePath = vtkFilePath;
        if (!selectedVtkFilePath) {
            const vtkFileSelect = document.getElementById('vtkFileSelect');
            // Check custom input if select is empty or "custom"
            const vtkFileBrowser = document.getElementById('vtkFileBrowser');
            if (vtkFileBrowser && vtkFileBrowser.files && vtkFileBrowser.files.length > 0) {
                // For browser upload, we might handle it differently, but for now lets assume local path logic isn't used here 
                // actually standard vtkFileSelect is what we use for server-side files
            }
            if (vtkFileSelect && vtkFileSelect.value) {
                selectedVtkFilePath = vtkFileSelect.value;
            }
        }
        // Log for debugging
        console.log('[FOAMFlask] [generateContours] Using case directory:', selectedCaseDir);
        if (selectedVtkFilePath) {
            console.log('[FOAMFlask] [generateContours] Using VTK file:', selectedVtkFilePath);
        }
        // Get range from input fields if not provided in options
        let range = options.range;
        if (!range) {
            const rangeMinInput = document.getElementById('rangeMin');
            const rangeMaxInput = document.getElementById('rangeMax');
            const rangeMin = rangeMinInput?.value ? parseFloat(rangeMinInput.value) : null;
            const rangeMax = rangeMaxInput?.value ? parseFloat(rangeMaxInput.value) : null;
            if (rangeMin !== null &&
                rangeMax !== null &&
                !isNaN(rangeMin) &&
                !isNaN(rangeMax) &&
                rangeMin < rangeMax) {
                range = [rangeMin, rangeMax];
                console.log('[FOAMFlask] [generateContours] Using range from input fields:', range);
            }
        }
        console.log('[FOAMFlask] [generateContours] Request parameters:', {
            tutorial: selectedTutorial,
            caseDir: selectedCaseDir,
            scalarField,
            numIsosurfaces,
            range,
            vtkFilePath: selectedVtkFilePath
        });
        // Get showIsovalueWidget from checkbox
        const showIsovalueWidgetCheckbox = document.getElementById('showIsovalueWidget');
        const showIsovalueWidget = showIsovalueWidgetCheckbox ? showIsovalueWidgetCheckbox.checked : true;
        // Prepare request data
        const requestData = {
            tutorial: selectedTutorial,
            caseDir: selectedCaseDir,
            scalarField,
            numIsosurfaces,
            vtkFilePath: selectedVtkFilePath,
            showIsovalueWidget
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
            timestamp: new Date().toISOString(),
            vtkFilePath: selectedVtkFilePath || undefined
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
 * Load mesh metadata for contour configuration
 * @param vtkFilePath - Path to the VTK file
 */
export async function loadContourMesh(vtkFilePath) {
    if (!vtkFilePath) {
        if (typeof showNotification === 'function') {
            showNotification("Please select a VTK file first.", "warning");
        }
        return;
    }
    try {
        console.log("[FOAMFlask] [loadContourMesh] Loading mesh for contour:", vtkFilePath);
        // Show loading notification
        if (typeof showNotification === 'function') {
            showNotification("Loading mesh metadata...", "info", 1000);
        }
        const response = await fetch('/api/load_mesh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_path: vtkFilePath,
                for_contour: true
            })
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Server returned ${response.status}: ${errorText}`);
        }
        const meshInfo = await response.json();
        console.log("[FOAMFlask] [loadContourMesh] Mesh info loaded:", meshInfo);
        if (meshInfo.error) {
            throw new Error(meshInfo.error);
        }
        // Populate Scalar Fields
        const scalarFieldSelect = document.getElementById('scalarField');
        if (scalarFieldSelect && meshInfo.point_arrays) {
            scalarFieldSelect.innerHTML = ''; // Clear existing
            // Add options
            meshInfo.point_arrays.forEach((field) => {
                const option = document.createElement('option');
                option.value = field;
                option.textContent = field;
                option.classList.add('point-data-option'); // Add styling class
                scalarFieldSelect.appendChild(option);
            });
            // If U_Magnitude exists, select it by default, otherwise select first
            if (meshInfo.point_arrays.includes('U_Magnitude')) {
                scalarFieldSelect.value = 'U_Magnitude';
            }
            else if (meshInfo.point_arrays.length > 0) {
                scalarFieldSelect.value = meshInfo.point_arrays[0];
            }
        }
        // Populate Info Box
        const contourInfo = document.getElementById('contourInfo');
        const contourInfoContent = document.getElementById('contourInfoContent');
        if (contourInfo && contourInfoContent) {
            contourInfo.classList.remove('hidden');
            contourInfoContent.innerHTML = `
                <div><span class="font-semibold">Points:</span> ${meshInfo.n_points}</div>
                <div><span class="font-semibold">Cells:</span> ${meshInfo.n_cells}</div>
                <div class="col-span-2"><span class="font-semibold">Fields:</span> ${meshInfo.point_arrays ? meshInfo.point_arrays.length : 0}</div>
            `;
        }
        if (typeof showNotification === 'function') {
            showNotification("Mesh loaded for contour configuration!", "success");
        }
        // Optionally clear ranges to suggest "Auto" or just leave them
        // For now, let's not aggressively clear them unless requested
    }
    catch (error) {
        console.error('[FOAMFlask] [loadContourMesh] Error:', error);
        if (typeof showNotification === 'function') {
            const message = error instanceof Error ? error.message : String(error);
            showNotification(`Error loading mesh: ${message}`, 'error');
        }
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
            <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-600"></div>
            <span class="ml-4 text-gray-600"></span>
        </div>
    `;
    // Set message text safely
    const messageSpan = container.querySelector('span');
    if (messageSpan) {
        messageSpan.textContent = message;
    }
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
    // Prepare the request body
    const requestBody = {
        tutorial: requestData.tutorial,
        caseDir: requestData.caseDir,
        scalar_field: requestData.scalarField,
        num_isosurfaces: requestData.numIsosurfaces,
        vtkFilePath: requestData.vtkFilePath,
        showIsovalueWidget: requestData.showIsovalueWidget
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
    }
    catch (error) {
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
function displayContourVisualization(container, htmlContent) {
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
        const iframeDoc = iframe.contentDocument || (iframe.contentWindow && iframe.contentWindow.document);
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
            }
            catch (e) {
                console.error('[FOAMFlask] [displayContourVisualization] Error triggering resize:', e);
            }
        };
        setTimeout(() => {
            try {
                window.dispatchEvent(new Event('resize'));
                if (iframe.contentWindow) {
                    iframe.contentWindow.dispatchEvent(new Event('resize'));
                }
            }
            catch (e) {
                console.warn('[FOAMFlask] [displayContourVisualization] Could not trigger iframe resize:', e);
            }
        }, 500);
    }
    catch (error) {
        console.error('[FOAMFlask] [displayContourVisualization] Error:', error);
        if (container) {
            const message = error instanceof Error ? error.message : 'Unknown error occurred';
            container.innerHTML = `
                <div class="p-4 text-red-600 bg-red-50 rounded-lg">
                    <h3 class="font-semibold">Error displaying visualization</h3>
                    <p class="text-sm mt-1"></p>
                    <p class="text-xs mt-2 text-gray-600">Check browser console for details</p>
                </div>
            `;
            // Set error message safely
            const messageP = container.querySelector('p.text-sm');
            if (messageP) {
                messageP.textContent = message;
            }
        }
    }
}
/**
 * Handle errors during contour generation
 */
function handleContourError(placeholder, viewer, error) {
    if (placeholder)
        placeholder.classList.remove('hidden');
    if (viewer)
        viewer.classList.add('hidden');
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
                <div class="text-gray-600 mb-4"></div>
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
                    class="mt-4 px-4 py-2 bg-cyan-600 text-white rounded hover:bg-cyan-700">
                    Try Again
                </button>
            </div>
        `;
        // Set error message safely
        const errorDiv = viewer.querySelector('.text-gray-600.mb-4');
        if (errorDiv) {
            errorDiv.textContent = errorMessage;
        }
    }
}
/**
 * Generate contours with custom parameters from UI controls
 */
export async function generateContoursWithParams() {
    try {
        const scalarFieldSelect = document.getElementById('scalarField');
        const numIsosurfacesInput = document.getElementById('numIsosurfaces');
        const scalarField = scalarFieldSelect?.value || 'U_Magnitude';
        const numIsosurfaces = numIsosurfacesInput?.value ? parseInt(numIsosurfacesInput.value, 10) : 5;
        // Get tutorial from select (same logic as generateContours)
        const selectedTutorial = getTutorialFromSelect() ?? '';
        if (!selectedTutorial) {
            if (typeof showNotification === 'function') {
                showNotification('Please select a tutorial first', 'warning');
            }
            return;
        }
        // Get case directory from input field (same logic as generateContours)
        const caseDirInput = document.getElementById('caseDir');
        const selectedCaseDir = caseDirInput?.value || '';
        if (!selectedCaseDir) {
            if (typeof showNotification === 'function') {
                showNotification('Case directory not set. Please set it in the Setup page.', 'warning');
            }
            return;
        }
        console.log('[FOAMFlask] [generateContoursWithParams] Generating contours with parameters:', {
            tutorial: selectedTutorial,
            caseDir: selectedCaseDir,
            scalarField,
            numIsosurfaces
        });
        // Pass all required properties with real values
        await generateContours({
            tutorial: selectedTutorial,
            caseDir: selectedCaseDir,
            scalarField,
            numIsosurfaces
        });
    }
    catch (error) {
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
    const iframe = document.getElementById('contourVisualizationFrame');
    if (!contourViewer || !iframe || !iframe.contentDocument)
        return;
    const canvas = iframe.contentDocument.querySelector('canvas');
    if (!canvas) {
        if (typeof showNotification === 'function') {
            showNotification('Cannot download: visualization not rendered as canvas', 'error');
        }
        return;
    }
    try {
        canvas.toBlob((blob) => {
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
    }
    catch (error) {
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
    if (contourPlaceholder)
        contourPlaceholder.classList.remove('hidden');
    if (contourViewer) {
        contourViewer.classList.add('hidden');
        contourViewer.innerHTML = '';
    }
    currentContourData = null;
}
//# sourceMappingURL=isosurface.js.map