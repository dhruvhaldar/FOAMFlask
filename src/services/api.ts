import type { MeshInfo, MeshFile } from '@/types';

const API_BASE_URL = '/api';

// Helper function to handle API responses
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message || 'An error occurred');
  }
  return response.json();
}

// Mesh related API calls
export const meshApi = {
  getAvailableMeshes: async (tutorial: string): Promise<{ meshes: MeshFile[] }> => {
    const response = await fetch(`${API_BASE_URL}/available_meshes?tutorial=${encodeURIComponent(tutorial)}`);
    return handleResponse(response);
  },
  
  loadMesh: async (filePath: string): Promise<MeshInfo> => {
    const response = await fetch(`${API_BASE_URL}/load_mesh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: filePath })
    });
    return handleResponse(response);
  },
  
  getMeshScreenshot: async (
    filePath: string, 
    options: {
      width: number;
      height: number;
      show_edges: boolean;
      color: string;
      camera_position?: string;
    }
  ): Promise<{ image: string; success: boolean }> => {
    const response = await fetch(`${API_BASE_URL}/mesh_screenshot`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        file_path: filePath,
        ...options
      })
    });
    return handleResponse(response);
  }
};

// Tutorial related API calls
export const tutorialApi = {
  loadTutorial: async (tutorial: string) => {
    const response = await fetch(`${API_BASE_URL}/load_tutorial`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tutorial })
    });
    return handleResponse(response);
  },
  
  getTutorials: async (): Promise<string[]> => {
    const response = await fetch(`${API_BASE_URL}/tutorials`);
    return handleResponse(response);
  }
};

// Case related API calls
export const caseApi = {
  setCase: async (caseDir: string) => {
    const response = await fetch(`${API_BASE_URL}/set_case`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ caseDir })
    });
    return handleResponse(response);
  },
  
  getCaseRoot: async (): Promise<{ caseDir: string }> => {
    const response = await fetch(`${API_BASE_URL}/get_case_root`);
    return handleResponse(response);
  }
};

// Docker/OpenFOAM configuration
export const configApi = {
  setDockerConfig: async (dockerImage: string, openfoamVersion: string) => {
    const response = await fetch(`${API_BASE_URL}/set_docker_config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dockerImage, openfoamVersion })
    });
    return handleResponse(response);
  },
  
  getDockerConfig: async (): Promise<{ dockerImage: string; openfoamVersion: string }> => {
    const response = await fetch(`${API_BASE_URL}/get_docker_config`);
    return handleResponse(response);
  }
};
