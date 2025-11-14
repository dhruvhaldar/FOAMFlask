import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000';

export interface Tutorial {
  name: string;
  path: string;
}

export interface DockerConfig {
  dockerImage: string;
  openfoamVersion: string;
}

export interface CaseConfig {
  caseRoot: string;
  dockerConfig: DockerConfig;
}

export interface MeshInfo {
  n_points: number;
  n_cells: number;
  point_arrays: string[];
  cell_arrays: string[];
  bounds: number[];
  success: boolean;
  error?: string;
}

export interface IsosurfaceInfo {
  n_points: number;
  n_cells: number;
  success: boolean;
  error?: string;
}

export interface PlotData {
  time: number[];
  fields: {
    [key: string]: {
      values: number[];
      min: number;
      max: number;
      mean: number;
      std: number;
    };
  };
}

export interface ResidualsData {
  time: number[];
  residuals: {
    [key: string]: number[];
  };
}

export interface MeshVisualization {
  success: boolean;
  image?: string;
  html?: string;
  error?: string;
}

export interface ContourOptions {
  scalarField?: string;
  numIsosurfaces?: number;
  range?: [number, number];
  showBaseMesh?: boolean;
  baseMeshOpacity?: number;
  contourOpacity?: number;
  contourColor?: string;
  colormap?: string;
}

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, config.params || '');
    return config;
  },
  (error) => {
    console.error('[API] Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`[API] Response ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('[API] Response Error:', {
      url: error.config?.url,
      status: error.response?.status,
      message: error.message,
      data: error.response?.data,
    });
    return Promise.reject(error);
  }
);

export const openfoamService = {
  // Get available OpenFOAM tutorials
  async getTutorials(): Promise<Tutorial[]> {
    try {
      const response = await api.get<Tutorial[]>('/tutorials');
      return response.data;
    } catch (error) {
      console.error('Error fetching tutorials:', error);
      throw error;
    }
  },

  // Set case directory
  async setCaseDirectory(caseDir: string): Promise<{ output: string; caseDir: string }> {
    try {
      const response = await api.post<{ output: string; caseDir: string }>('/set_case', { caseDir });
      return response.data;
    } catch (error) {
      console.error('Error setting case directory:', error);
      throw error;
    }
  },

  // Get current case directory
  async getCaseDirectory(): Promise<{ caseDir: string }> {
    try {
      const response = await api.get<{ caseDir: string }>('/get_case_root');
      return response.data;
    } catch (error) {
      console.error('Error getting case directory:', error);
      throw error;
    }
  },

  // Get Docker configuration
  async getDockerConfig(): Promise<DockerConfig> {
    try {
      const response = await api.get<DockerConfig>('/get_docker_config');
      return response.data;
    } catch (error) {
      console.error('Error getting Docker config:', error);
      throw error;
    }
  },

  // Set Docker configuration
  async setDockerConfig(config: Partial<DockerConfig>): Promise<DockerConfig> {
    try {
      const response = await api.post<DockerConfig>('/set_docker_config', config);
      return response.data;
    } catch (error) {
      console.error('Error setting Docker config:', error);
      throw error;
    }
  },

  // Load a tutorial
  async loadTutorial(tutorial: string): Promise<{ output: string }> {
    try {
      const response = await api.post<{ output: string }>('/load_tutorial', { tutorial });
      return response.data;
    } catch (error) {
      console.error('Error loading tutorial:', error);
      throw error;
    }
  },

  // Run a case
  async runCase(tutorial: string, command: string, caseDir: string): Promise<{ output: string }> {
    try {
      const response = await api.post<{ output: string }>('/run', {
        tutorial,
        command,
        caseDir
      });
      return response.data;
    } catch (error) {
      console.error('Error running case:', error);
      throw error;
    }
  },

  // Get available fields for plotting
  async getAvailableFields(tutorial: string): Promise<{ fields: string[] }> {
    try {
      const response = await api.get<{ fields: string[] }>('/api/available_fields', {
        params: { tutorial }
      });
      return response.data;
    } catch (error) {
      console.error('Error getting available fields:', error);
      throw error;
    }
  },

  // Get plot data
  async getPlotData(tutorial: string): Promise<PlotData> {
    try {
      const response = await api.get<PlotData>('/api/plot_data', {
        params: { tutorial }
      });
      return response.data;
    } catch (error) {
      console.error('Error getting plot data:', error);
      throw error;
    }
  },

  // Get mesh visualization
  async getMeshVisualization(tutorial: string): Promise<MeshVisualization> {
    try {
      // First, get available meshes
      const meshes = await this.getAvailableMeshes(tutorial);
      if (!meshes.meshes || meshes.meshes.length === 0) {
        throw new Error('No mesh files found');
      }

      // Use the first available mesh
      const meshPath = meshes.meshes[0];
      
      // Get mesh screenshot
      const response = await api.post<MeshVisualization>('/api/mesh_screenshot', {
        file_path: meshPath,
        width: 800,
        height: 600,
        show_edges: true,
        color: 'lightblue'
      });

      return response.data;
    } catch (error) {
      console.error('Error getting mesh visualization:', error);
      throw error;
    }
  },

  // Get available meshes
  async getAvailableMeshes(tutorial: string): Promise<{ meshes: string[] }> {
    try {
      const response = await api.get<{ meshes: string[] }>('/api/available_meshes', {
        params: { tutorial }
      });
      return response.data;
    } catch (error) {
      console.error('Error getting available meshes:', error);
      throw error;
    }
  },

  // Get residuals
  async getResiduals(tutorial: string): Promise<ResidualsData> {
    try {
      const response = await api.get<ResidualsData>('/api/residuals', {
        params: { tutorial }
      });
      return response.data;
    } catch (error) {
      console.error('Error getting residuals:', error);
      throw error;
    }
  },

  // Create contour
  async createContour(
    tutorial: string,
    options: ContourOptions = {}
  ): Promise<MeshVisualization> {
    try {
      const response = await api.post<MeshVisualization>('/api/contours/create', {
        tutorial,
        scalar_field: options.scalarField || 'U_Magnitude',
        num_isosurfaces: options.numIsosurfaces || 5,
        range: options.range,
        show_base_mesh: options.showBaseMesh !== false,
        base_mesh_opacity: options.baseMeshOpacity ?? 0.25,
        contour_opacity: options.contourOpacity ?? 0.8,
        contour_color: options.contourColor || 'red',
        colormap: options.colormap || 'viridis'
      });

      return response.data;
    } catch (error) {
      console.error('Error creating contour:', error);
      throw error;
    }
  },

  // Get latest simulation data
  async getLatestData(tutorial: string): Promise<Record<string, unknown>> {
    try {
      const response = await api.get<Record<string, unknown>>('/api/latest_data', {
        params: { tutorial }
      });
      return response.data;
    } catch (error) {
      console.error('Error getting latest data:', error);
      throw error;
    }
  },

  // Stream simulation output
  streamSimulationOutput(tutorial: string, command: string, caseDir: string): EventSource {
    const params = new URLSearchParams({
      tutorial,
      command,
      caseDir
    });
    
    return new EventSource(`${API_BASE_URL}/stream?${params.toString()}`);
  }
};
