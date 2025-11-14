import axios from 'axios';
import * as fs from 'fs/promises';
import * as path from 'path';

const API_BASE_URL = 'http://127.0.0.1:8000';
const CONFIG_FILE = 'case_config.json';

export interface DockerConfig {
  dockerImage: string;
  openfoamVersion: string;
}

export interface CaseConfig {
  caseDirectory: string;
  openfoamVersion: string;
}

export interface Tutorial {
  name: string;
  path: string;
}

export interface ApiResponse<T> {
  data: T;
  status: number;
  statusText: string;
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
    console.log(`[Docker API] ${config.method?.toUpperCase()} ${config.url}`, config.params || '');
    return config;
  },
  (error) => {
    console.error('[Docker API] Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`[Docker API] Response ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('[Docker API] Response Error:', {
      url: error.config?.url,
      status: error.response?.status,
      message: error.message,
      data: error.response?.data,
    });
    return Promise.reject(error);
  }
);

// Helper function to handle API errors
const handleApiError = (error: unknown, defaultMessage: string): never => {
  if (axios.isAxiosError(error)) {
    const message = error.response?.data?.detail || error.message;
    throw new Error(message || defaultMessage);
  }
  throw error instanceof Error ? error : new Error(defaultMessage);
};

// In dockerService.ts

const CONFIG_KEY = 'openfoam_config';

const readConfigFile = async (): Promise<DockerConfig | null> => {
  try {
    const config = localStorage.getItem(CONFIG_KEY);
    return config ? JSON.parse(config) : null;
  } catch (error) {
    console.error('Error reading config from localStorage:', error);
    return null;
  }
};

const writeConfigFile = async (config: DockerConfig): Promise<void> => {
  try {
    localStorage.setItem(CONFIG_KEY, JSON.stringify(config, null, 2));
  } catch (error) {
    console.error('Error writing config to localStorage:', error);
    throw new Error('Failed to save configuration');
  }
};

export const dockerService = {
  // Get current Docker configuration
  getDockerConfig: async (): Promise<DockerConfig> => {
    try {
      // First try to read from the local config file
      const localConfig = await readConfigFile();
      if (localConfig) {
        return localConfig;
      }
      
      // If no local config, try the API
      try {
        const response = await api.get<DockerConfig>('/api/case/config');
        // Save the API config to local file for future use
        await writeConfigFile(response.data);
        return response.data;
      } catch (error: any) {
        // If API fails, return default config
        return {
          dockerImage: 'haldardhruv/ubuntu_noble_openfoam:v12',
          openfoamVersion: '12'
        };
      }
    } catch (error) {
      console.error('Error in getDockerConfig:', error);
      return {
        dockerImage: 'haldardhruv/ubuntu_noble_openfoam:v12',
        openfoamVersion: '12'
      };
    }
  },

  // Get current case configuration
  getCaseConfig: async (): Promise<CaseConfig> => {
    try {
      const response = await api.get<CaseConfig>('/api/case/config');
      return response.data;
    } catch (error) {
      return handleApiError(error, 'Failed to fetch case configuration');
    }
  },

  // Update case configuration
  updateCaseConfig: async (config: Partial<CaseConfig>): Promise<CaseConfig> => {
    try {
      const response = await api.post<CaseConfig>('/api/case/config', config);
      return response.data;
    } catch (error) {
      return handleApiError(error, 'Failed to update case configuration');
    }
  },

  // List available tutorials
  listTutorials: async (): Promise<string[]> => {
    try {
      const response = await api.get<string[]>('/api/tutorials');
      return response.data;
    } catch (error) {
      return handleApiError(error, 'Failed to list tutorials');
    }
  },

  // Set case directory
  setCaseDirectory: async (directory: string): Promise<void> => {
    try {
      await api.post('/api/case/set_directory', { directory });
    } catch (error) {
      return handleApiError(error, 'Failed to set case directory');
    }
  },

  // Update Docker configuration
  updateDockerConfig: async (config: Partial<DockerConfig>): Promise<DockerConfig> => {
    try {
      // Get current config
      const currentConfig = await dockerService.getDockerConfig();
      // Merge with new config
      const newConfig = { ...currentConfig, ...config };
      
      // Save to file
      await writeConfigFile(newConfig);
      
      // Try to update via API if available
      try {
        const response = await api.post<DockerConfig>('/api/case/config', config);
        return response.data;
      } catch (apiError) {
        console.warn('API update failed, using local config only:', apiError);
        return newConfig;
      }
    } catch (error) {
      console.error('Error updating Docker config:', error);
      throw error;
    }
  },

  // Get available tutorials
  getTutorials: async (): Promise<Tutorial[]> => {
    try {
      const response = await api.get<Tutorial[]>('/tutorials');
      return response.data;
    } catch (error) {
      console.error('Error fetching tutorials:', error);
      throw error;
    }
  },

  // Load a tutorial
  loadTutorial: async (tutorial: string, caseDir: string): Promise<{ output: string }> => {
    try {
      const response = await api.post<{ output: string }>('/api/tutorials/load', {
        tutorial,
        caseDir
      });
      return response.data;
    } catch (error) {
      return handleApiError(error, 'Failed to load tutorial');
    }
  },

  // Run a case
  runCase: async (tutorial: string, command: string, caseDir: string): Promise<{ output: string }> => {
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

  // Get available fields for a case
  getAvailableFields: async (tutorial: string, caseDir: string): Promise<string[]> => {
    try {
      const response = await api.get<{ fields: string[] }>('/api/available_fields', {
        params: { tutorial, caseDir }
      });
      return response.data.fields;
    } catch (error) {
      console.error('Error getting available fields:', error);
      throw error;
    }
  },

  // Get plot data
  getPlotData: async (tutorial: string, caseDir: string): Promise<Record<string, any>> => {
    try {
      const response = await api.get<Record<string, any>>('/api/plot_data', {
        params: { tutorial, caseDir }
      });
      return response.data;
    } catch (error) {
      console.error('Error getting plot data:', error);
      throw error;
    }
  },

  // Get residuals
  getResiduals: async (tutorial: string, caseDir: string): Promise<Record<string, any>> => {
    try {
      const response = await api.get<Record<string, any>>('/api/residuals', {
        params: { tutorial, caseDir }
      });
      return response.data;
    } catch (error) {
      console.error('Error getting residuals:', error);
      throw error;
    }
  },

  // Create contour
  createContour: async (
    tutorial: string, 
    caseDir: string, 
    options: {
      scalarField?: string;
      numIsosurfaces?: number;
      range?: [number, number];
    } = {}
  ): Promise<string> => {
    try {
      const response = await api.post<string>('/api/contours/create', {
        tutorial,
        caseDir,
        scalar_field: options.scalarField || 'U_Magnitude',
        num_isosurfaces: options.numIsosurfaces || 5,
        range: options.range
      });
      return response.data;
    } catch (error) {
      return handleApiError(error, 'Failed to create contour');
    }
  },

  // Stream simulation output
  streamSimulationOutput: (tutorial: string, command: string, caseDir: string): EventSource => {
    const params = new URLSearchParams({
      tutorial,
      command,
      caseDir
    });
    return new EventSource(`${API_BASE_URL}/stream?${params.toString()}`);
  }
};

export default dockerService;
