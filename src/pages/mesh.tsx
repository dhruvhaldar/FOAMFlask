import { useState, useEffect } from 'react';
import { useToast } from '@/components/ui/use-toast';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@radix-ui/react-select';
import { Label } from '@radix-ui/react-label';
import { Input } from '@/components/ui/input';

// Types
interface MeshInfo {
  n_points?: number;
  n_cells?: number;
  length?: number;
  volume?: number;
  center?: number[];
  bounds?: number[];
}

interface MeshFile {
  id?: string;
  path: string;
  name?: string;
}

interface ViewOptions {
  showEdges: boolean;
  color: string;
  cameraPosition: string;
}

// Styled components for consistent UI elements
const MeshPlaceholder = ({ message }: { message: string }) => (
  <div className="flex flex-col items-center justify-center h-96 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-6 text-center">
    <div className="text-gray-400 mb-4">
      <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
      </svg>
    </div>
    <p className="text-gray-500">{message}</p>
  </div>
);

const CameraControlButton = ({ 
  onClick, 
  title, 
  iconPath 
}: { 
  onClick: () => void; 
  title: string; 
  iconPath: string;
}) => (
  <button
    onClick={onClick}
    title={title}
    className="p-2 bg-white rounded-lg shadow-md hover:bg-gray-100 transition-colors"
  >
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={iconPath} />
    </svg>
  </button>
);

export default function MeshPage() {
  const { toast } = useToast();
  
  // State for mesh data and controls
  const [selectedMesh, setSelectedMesh] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isInteractiveMode, setIsInteractiveMode] = useState(false);
  const [meshImage, setMeshImage] = useState<string | null>(null);
  const [meshInfo, setMeshInfo] = useState<MeshInfo | null>(null);
  const [availableMeshes, setAvailableMeshes] = useState<MeshFile[]>([]);
  const [viewOptions, setViewOptions] = useState<ViewOptions>({
    showEdges: true,
    color: '#1e90ff',
    cameraPosition: 'isometric',
  });

  // Load available meshes on component mount
  useEffect(() => {
    loadAvailableMeshes();
  }, []);

  // Load available meshes from API
  const loadAvailableMeshes = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/mesh/available');
      if (response.ok) {
        const data = await response.json();
        setAvailableMeshes(data.meshes || []);
      } else {
        toast({
          title: "Error",
          description: "Failed to load available meshes",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to fetch meshes: ${error}`,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Handle mesh selection
  const handleMeshSelect = async (value: string) => {
    setSelectedMesh(value);
    await updateMeshView(value);
  };

  // Update mesh view with current options
  const updateMeshView = async (meshPath: string) => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/mesh/load', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mesh_path: meshPath,
          camera_position: viewOptions.cameraPosition,
          show_edges: viewOptions.showEdges,
          color: viewOptions.color,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setMeshImage(data.image || null);
        setMeshInfo(data.mesh_info || null);
        toast({
          title: "Mesh Loaded",
          description: `Successfully loaded mesh: ${meshPath.split('/').pop()}`,
        });
      } else {
        toast({
          title: "Error",
          description: "Failed to load mesh",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to load mesh: ${error}`,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Toggle interactive mode
  const toggleInteractiveMode = () => {
    setIsInteractiveMode(!isInteractiveMode);
    toast({
      title: "Interactive Mode",
      description: !isInteractiveMode ? "Interactive 3D mode enabled" : "Interactive mode disabled",
    });
  };

  // Set camera view
  const setCameraView = async (position: string) => {
    setViewOptions(prev => ({ ...prev, cameraPosition: position }));
    if (selectedMesh && !isInteractiveMode) {
      await updateMeshView(selectedMesh);
    }
    toast({
      title: "Camera View Updated",
      description: `Changed to ${position} view`,
    });
  };

  // Download mesh image
  const handleDownloadImage = () => {
    if (meshImage) {
      const link = document.createElement('a');
      link.href = meshImage;
      link.download = `mesh-${Date.now()}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast({
        title: "Image Downloaded",
        description: "Mesh image saved successfully",
      });
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header Section */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col space-y-2">
            <h1 className="text-3xl font-bold text-gray-900">Mesh Visualization</h1>
            <p className="text-gray-600">
              Visualize and interact with your OpenFOAM mesh files
            </p>
          </div>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <Card className="shadow-lg">
          <CardHeader>
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
              <div>
                <CardTitle>Mesh Viewer</CardTitle>
                <CardDescription>Load and visualize your mesh files</CardDescription>
              </div>
              <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3 w-full sm:w-auto">
                <Button 
                  variant="outline" 
                  onClick={() => loadAvailableMeshes()}
                  disabled={isLoading}
                  className="w-full sm:w-auto"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Refresh
                </Button>
                <Select 
                  value={selectedMesh} 
                  onValueChange={handleMeshSelect}
                  disabled={isLoading || availableMeshes.length === 0}
                >
                  <SelectTrigger className="w-full sm:w-64">
                    <SelectValue placeholder="Select a mesh file" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableMeshes.map((mesh) => (
                      <SelectItem key={mesh.path} value={mesh.path}>
                        <div className="flex items-center">
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          {mesh.name || mesh.path.split('/').pop()}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardHeader>
        
          <CardContent className="p-6">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              {/* Main Viewer */}
              <div className="lg:col-span-3 space-y-4">
                <div 
                  id="mesh-container" 
                  className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 w-full aspect-video flex items-center justify-center relative overflow-hidden transition-all duration-300 hover:border-blue-400"
                >
                  {isLoading ? (
                    <div className="flex flex-col items-center justify-center space-y-3 p-6">
                      <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                      <p className="text-gray-600 font-medium">Loading mesh...</p>
                      <p className="text-sm text-gray-500">This may take a moment</p>
                    </div>
                  ) : meshImage && !isInteractiveMode ? (
                    <div className="relative w-full h-full">
                      <img 
                        src={meshImage} 
                        alt="Mesh visualization" 
                        className="w-full h-full object-contain p-2"
                      />
                      {/* Camera controls overlay */}
                      <div className="absolute bottom-4 right-4 flex flex-col space-y-2 opacity-0 hover:opacity-100 transition-opacity duration-300">
                        <CameraControlButton 
                          onClick={() => setCameraView('xy')}
                          title="Top View (XY)"
                          iconPath="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                        />
                        <CameraControlButton 
                          onClick={() => setCameraView('xz')}
                          title="Front View (XZ)"
                          iconPath="M4 6h16M4 12h16M4 18h7"
                        />
                        <CameraControlButton 
                          onClick={() => setCameraView('yz')}
                          title="Side View (YZ)"
                          iconPath="M12 4v16m8-8H4"
                        />
                        <CameraControlButton 
                          onClick={() => setCameraView('isometric')}
                          title="Isometric View"
                          iconPath="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
                        />
                      </div>
                    </div>
                  ) : isInteractiveMode ? (
                    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100">
                      <div className="text-center p-8 bg-white rounded-xl shadow-lg border border-gray-200 max-w-md mx-4">
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 mb-4">
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        </div>
                        <h3 className="text-xl font-semibold text-gray-900 mb-2">Interactive 3D Mode</h3>
                        <p className="text-gray-600 mb-6">
                          Use your mouse to rotate, scroll to zoom, and right-click to pan the 3D view.
                        </p>
                        <div className="grid grid-cols-2 gap-3">
                          <Button 
                            variant="outline" 
                            onClick={() => setIsInteractiveMode(false)}
                            className="flex items-center justify-center space-x-2"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                            <span>Exit 3D Mode</span>
                          </Button>
                          <Button 
                            onClick={handleDownloadImage}
                            className="bg-blue-600 hover:bg-blue-700 text-white"
                            disabled={!meshImage}
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                            Save Image
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <MeshPlaceholder 
                      message={availableMeshes.length === 0 
                        ? 'No mesh files found. Please load a tutorial first.'
                        : 'Select a mesh file to view it here'}
                    />
                  )}
                </div>
                
                <div className="flex flex-wrap items-center gap-2 bg-gray-50 p-3 rounded-lg border border-gray-200">
                  <div className="flex flex-wrap gap-2 flex-1">
                    <Button
                      variant={isInteractiveMode ? "default" : "outline"}
                      onClick={toggleInteractiveMode}
                      disabled={!selectedMesh || isLoading}
                      className={`flex items-center space-x-2 transition-all ${isInteractiveMode ? 'bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white shadow-md' : 'hover:bg-gray-100'}`}
                    >
                      {isInteractiveMode ? (
                        <>
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                          <span>Exit 3D Mode</span>
                        </>
                      ) : (
                        <>
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                          <span>3D Interactive Mode</span>
                        </>
                      )}
                    </Button>
                    
                    <Button
                      variant="outline"
                      onClick={() => selectedMesh && updateMeshView(selectedMesh)}
                      disabled={!selectedMesh || isLoading || isInteractiveMode}
                      className="flex items-center space-x-2"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      <span>Refresh View</span>
                    </Button>
                    
                    <Button
                      variant="outline"
                      onClick={handleDownloadImage}
                      disabled={!meshImage || isLoading || isInteractiveMode}
                      className="flex items-center space-x-2"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      <span>Save Image</span>
                    </Button>
                  </div>
                  
                  <div className="flex-1 flex justify-end space-x-2">
                    <span className="hidden sm:inline-flex items-center px-3 py-1.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      View:
                    </span>
                    <Button
                      variant={viewOptions.cameraPosition === 'xy' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setCameraView('xy')}
                      disabled={!selectedMesh || isLoading || isInteractiveMode}
                      className="px-3"
                    >
                      XY
                    </Button>
                    <Button
                      variant={viewOptions.cameraPosition === 'xz' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setCameraView('xz')}
                      disabled={!selectedMesh || isLoading || isInteractiveMode}
                      className="px-3"
                    >
                      XZ
                    </Button>
                    <Button
                      variant={viewOptions.cameraPosition === 'yz' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setCameraView('yz')}
                      disabled={!selectedMesh || isLoading || isInteractiveMode}
                      className="px-3"
                    >
                      YZ
                    </Button>
                    <Button
                      variant={viewOptions.cameraPosition === 'isometric' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setCameraView('isometric')}
                      disabled={!selectedMesh || isLoading || isInteractiveMode}
                      className="px-3"
                    >
                      ISO
                    </Button>
                  </div>
                </div>
              </div>
              
              {/* Side Panel */}
              <div className="space-y-4">
                {/* Mesh Properties Card */}
                <Card className="border border-gray-200 shadow-sm">
                  <CardHeader className="bg-gray-50 border-b">
                    <CardTitle className="text-lg font-semibold text-gray-800 flex items-center">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Mesh Properties
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {meshInfo ? (
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-blue-50 p-3 rounded-lg">
                            <dt className="text-sm font-medium text-blue-700">Points</dt>
                            <dd className="mt-1 text-2xl font-semibold text-gray-900">
                              {meshInfo.n_points?.toLocaleString() || 'N/A'}
                            </dd>
                          </div>
                          
                          <div className="bg-green-50 p-3 rounded-lg">
                            <dt className="text-sm font-medium text-green-700">Cells</dt>
                            <dd className="mt-1 text-2xl font-semibold text-gray-900">
                              {meshInfo.n_cells?.toLocaleString() || 'N/A'}
                            </dd>
                          </div>
                        </div>
                        
                        {(meshInfo.length || meshInfo.volume) && (
                          <div className="grid grid-cols-2 gap-4">
                            {meshInfo.length && (
                              <div className="bg-purple-50 p-3 rounded-lg">
                                <dt className="text-sm font-medium text-purple-700">Length</dt>
                                <dd className="mt-1 text-lg font-medium text-gray-900">
                                  {meshInfo.length.toFixed(3)} m
                                </dd>
                              </div>
                            )}
                            
                            {meshInfo.volume && (
                              <div className="bg-yellow-50 p-3 rounded-lg">
                                <dt className="text-sm font-medium text-yellow-700">Volume</dt>
                                <dd className="mt-1 text-lg font-medium text-gray-900">
                                  {meshInfo.volume.toFixed(3)} m³
                                </dd>
                              </div>
                            )}
                          </div>
                        )}
                        
                        {(meshInfo.center || meshInfo.bounds) && (
                          <div className="space-y-3">
                            {meshInfo.center && (
                              <div>
                                <h4 className="text-sm font-medium text-gray-700 mb-1">Center (x, y, z)</h4>
                                <div className="bg-gray-50 p-3 rounded-md font-mono text-sm">
                                  ({meshInfo.center.map(n => n.toFixed(2)).join(', ')})
                                </div>
                              </div>
                            )}
                            
                            {meshInfo.bounds && (
                              <div>
                                <h4 className="text-sm font-medium text-gray-700 mb-1">Bounds [min, max]</h4>
                                <div className="bg-gray-50 p-3 rounded-md font-mono text-sm">
                                  [{meshInfo.bounds.map(n => n.toFixed(2)).join(', ')}]
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-gray-100 mb-3">
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </div>
                        <h3 className="text-sm font-medium text-gray-900">No mesh loaded</h3>
                        <p className="mt-1 text-sm text-gray-500">
                          Select a mesh file to view its properties
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
                
                {/* View Options Card */}
                <Card className="border border-gray-200 shadow-sm">
                  <CardHeader className="bg-gray-50 border-b">
                    <CardTitle className="text-lg font-semibold text-gray-800 flex items-center">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      View Options
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6 space-y-6">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <Label htmlFor="showEdges" className="text-sm font-medium text-gray-700">Show Edges</Label>
                          <p className="text-xs text-gray-500">Display mesh edges for better visibility</p>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input 
                            type="checkbox" 
                            id="showEdges"
                            className="sr-only peer"
                            checked={viewOptions.showEdges}
                            onChange={(e) => {
                              setViewOptions(prev => ({
                                ...prev,
                                showEdges: e.target.checked,
                              }));
                            }}
                            disabled={!selectedMesh || isLoading || isInteractiveMode}
                          />
                          <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                        </label>
                      </div>
                      
                      <div className="space-y-2">
                        <Label htmlFor="meshColor" className="text-sm font-medium text-gray-700">Mesh Color</Label>
                        <div className="flex items-center space-x-3">
                          <div className="relative">
                            <input
                              type="color"
                              id="meshColor"
                              value={viewOptions.color}
                              onChange={(e) => {
                                setViewOptions(prev => ({
                                  ...prev,
                                  color: e.target.value,
                                }));
                              }}
                              disabled={!selectedMesh || isLoading || isInteractiveMode}
                              className="h-10 w-10 rounded-lg border-2 border-gray-300 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                            />
                            <div className="absolute inset-0 rounded-lg border-2 border-white shadow-sm pointer-events-none"></div>
                          </div>
                          
                          <div className="flex-1">
                            <Input
                              type="text"
                              value={viewOptions.color}
                              onChange={(e) => {
                                setViewOptions(prev => ({
                                  ...prev,
                                  color: e.target.value,
                                }));
                              }}
                              disabled={!selectedMesh || isLoading || isInteractiveMode}
                              className="font-mono text-sm"
                            />
                          </div>
                        </div>
                      </div>
                      
                      <div className="space-y-2">
                        <Label htmlFor="cameraPosition" className="text-sm font-medium text-gray-700">Default View</Label>
                        <Select
                          value={viewOptions.cameraPosition}
                          onValueChange={(value) => {
                            setViewOptions(prev => ({
                              ...prev,
                              cameraPosition: value,
                            }));
                          }}
                          disabled={!selectedMesh || isLoading || isInteractiveMode}
                        >
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select default view" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="isometric">Isometric</SelectItem>
                            <SelectItem value="xy">Top (XY)</SelectItem>
                            <SelectItem value="xz">Front (XZ)</SelectItem>
                            <SelectItem value="yz">Side (YZ)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    
                    <Button
                      onClick={() => selectedMesh && updateMeshView(selectedMesh)}
                      disabled={!selectedMesh || isLoading || isInteractiveMode}
                      className="w-full bg-blue-600 hover:bg-blue-700 transition-colors duration-200"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      Apply Changes
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <footer className="mt-12 border-t border-gray-200 py-6">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <p className="text-center text-sm text-gray-500">
              &copy; {new Date().getFullYear()} FOAMPilot. All rights reserved.
            </p>
          </div>
        </footer>
      </main>
    </div>
  );
}
