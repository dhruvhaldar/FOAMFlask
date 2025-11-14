import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import dockerService from '../services/dockerService';

export interface CaseConfig {
  caseDirectory: string;
  openfoamVersion: string;
}

interface DockerContextType {
  // Docker configuration
  dockerConfig: {
    dockerImage: string;
    openfoamVersion: string;
  };
  
  // Case configuration
  caseConfig: CaseConfig | null;
  
  // Status
  isDockerRunning: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Docker config methods
  updateDockerConfig: (config: { dockerImage?: string; openfoamVersion?: string }) => Promise<void>;
  
  // Case config methods
  updateCaseConfig: (config: Partial<CaseConfig>) => Promise<void>;
  
  // Simulation methods
  loadTutorial: (tutorial: string, caseDir: string) => Promise<unknown>;
  runCase: (tutorial: string, command: string, caseDir: string) => Promise<unknown>;
  getAvailableFields: (tutorial: string, caseDir: string) => Promise<string[]>;
  getPlotData: (tutorial: string, caseDir: string) => Promise<Record<string, unknown>>;
  getResiduals: (tutorial: string, caseDir: string) => Promise<Record<string, unknown>>;
  createContour: (tutorial: string, caseDir: string, scalarField?: string, numIsosurfaces?: number) => Promise<unknown>;
}

const DockerContext = createContext<DockerContextType | undefined>(undefined);

export const DockerProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [dockerConfig, setDockerConfig] = useState({
    dockerImage: 'haldardhruv/ubuntu_noble_openfoam:v12',
    openfoamVersion: '12',
  });
  
  const [caseConfig, setCaseConfig] = useState<CaseConfig | null>(null);
  const [isDockerRunning, setIsDockerRunning] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load Docker config on mount
  useEffect(() => {
    const loadDockerConfig = async () => {
      try {
        const config = await dockerService.getDockerConfig();
        setDockerConfig(config);
        setIsDockerRunning(true);
      } catch (err) {
        console.error('Failed to load Docker config:', err);
        setError('Failed to connect to Docker service. Make sure the backend server is running.');
      } finally {
        setIsLoading(false);
      }
    };

    loadDockerConfig();
  }, []);

  const updateDockerConfig = async (config: { dockerImage?: string; openfoamVersion?: string }) => {
    try {
      setIsLoading(true);
      const updatedConfig = await dockerService.updateDockerConfig(config);
      setDockerConfig(updatedConfig);
      setError(null);
    } catch (err) {
      console.error('Failed to update Docker config:', err);
      setError('Failed to update Docker configuration');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const updateCaseConfig = async (config: Partial<CaseConfig>) => {
    try {
      setIsLoading(true);
      // In a real implementation, this would save to the backend
      setCaseConfig(prev => ({
        ...(prev || { caseDirectory: '', openfoamVersion: dockerConfig.openfoamVersion }),
        ...config
      }));
      setError(null);
    } catch (err) {
      console.error('Failed to update case config:', err);
      setError('Failed to update case configuration');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const loadTutorial = async (tutorial: string, caseDir: string) => {
    try {
      setIsLoading(true);
      const result = await dockerService.loadTutorial(tutorial, caseDir);
      setError(null);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error('Failed to load tutorial:', errorMessage);
      setError(`Failed to load tutorial: ${errorMessage}`);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const runCase = async (tutorial: string, command: string, caseDir: string) => {
    try {
      setIsLoading(true);
      const result = await dockerService.runCase(tutorial, command, caseDir);
      setError(null);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error('Failed to run case:', errorMessage);
      setError(`Failed to run case: ${errorMessage}`);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const getAvailableFields = async (tutorial: string, caseDir: string) => {
    try {
      const fields = await dockerService.getAvailableFields(tutorial, caseDir);
      setError(null);
      return fields;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error('Error getting available fields:', errorMessage);
      setError(`Failed to get available fields: ${errorMessage}`);
      throw err;
    }
  };

  const getPlotData = async (tutorial: string, caseDir: string) => {
    try {
      const data = await dockerService.getPlotData(tutorial, caseDir);
      setError(null);
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error('Error getting plot data:', errorMessage);
      setError(`Failed to get plot data: ${errorMessage}`);
      throw err;
    }
  };

  const getResiduals = async (tutorial: string, caseDir: string) => {
    try {
      const residuals = await dockerService.getResiduals(tutorial, caseDir);
      setError(null);
      return residuals;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error('Error getting residuals:', errorMessage);
      setError(`Failed to get residuals: ${errorMessage}`);
      throw err;
    }
  };

  const createContour = async (
    tutorial: string, 
    caseDir: string, 
    scalarField?: string, 
    numIsosurfaces?: number
  ) => {
    try {
      setIsLoading(true);
      const result = await dockerService.createContour(tutorial, caseDir, { 
        scalarField: scalarField || 'U_Magnitude', 
        numIsosurfaces: numIsosurfaces || 5 
      });
      setError(null);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error('Error creating contour:', errorMessage);
      setError(`Failed to create contour: ${errorMessage}`);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <DockerContext.Provider
      value={{
        dockerConfig,
        caseConfig,
        isDockerRunning,
        isLoading,
        error,
        updateDockerConfig,
        updateCaseConfig,
        loadTutorial,
        runCase,
        getAvailableFields,
        getPlotData,
        getResiduals,
        createContour,
      }}
    >
      {children}
    </DockerContext.Provider>
  );
};

export const useDocker = (): DockerContextType => {
  const context = useContext(DockerContext);
  if (context === undefined) {
    throw new Error('useDocker must be used within a DockerProvider');
  }
  return context;
};

// Export the context separately to avoid Fast Refresh issues
export { DockerContext };

export default DockerContext;
