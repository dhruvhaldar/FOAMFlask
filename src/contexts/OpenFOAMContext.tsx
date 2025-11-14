import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { openfoamService, Tutorial, DockerConfig } from '../services/openfoamService';

interface OpenFOAMContextType {
  tutorials: Tutorial[];
  currentTutorial: string | null;
  caseRoot: string;
  dockerConfig: DockerConfig;
  isLoading: boolean;
  error: string | null;
  setCaseRoot: (path: string) => void;
  setDockerConfig: (config: { dockerImage?: string; openfoamVersion?: string }) => Promise<void>;
  runSimulation: (tutorial: string, command: string, caseDir: string) => Promise<any>;
  loadTutorials: () => Promise<void>;
  runTutorial: (tutorial: string, command: string) => Promise<void>;
  getAvailableFields: (tutorial: string) => Promise<string[]>;
  getPlotData: (tutorial: string) => Promise<any>;
  getMeshVisualization: (tutorial: string) => Promise<any>;
}

const OpenFOAMContext = createContext<OpenFOAMContextType | undefined>(undefined);

export const OpenFOAMProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [tutorials, setTutorials] = useState<Tutorial[]>([]);
  const [currentTutorial, setCurrentTutorial] = useState<string | null>(null);
  const [caseRoot, setCaseRootState] = useState<string>('');
  const [dockerConfig, setDockerConfigState] = useState<DockerConfig>({
    dockerImage: 'haldardhruv/ubuntu_noble_openfoam:v12',
    openfoamVersion: '12'
  });
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load initial data
  useEffect(() => {
    const initialize = async () => {
      try {
        setIsLoading(true);
        const [config, root] = await Promise.all([
          openfoamService.getDockerConfig(),
          openfoamService.getCaseDirectory()
        ]);
        setDockerConfigState(config);
        setCaseRootState(root.caseDir);
        await loadTutorials();
      } catch (err) {
        setError('Failed to initialize OpenFOAM context');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    initialize();
  }, []);

  const loadTutorials = async () => {
    try {
      const tutorials = await openfoamService.getTutorials();
      setTutorials(tutorials);
    } catch (err) {
      setError('Failed to load tutorials');
      throw err;
    }
  };

  const setCaseRoot = async (path: string) => {
    try {
      const result = await openfoamService.setCaseDirectory(path);
      setCaseRootState(result.caseDir);
      await loadTutorials(); // Reload tutorials in case the directory changed
    } catch (err) {
      setError('Failed to set case directory');
      throw err;
    }
  };

  const setDockerConfig = async (config: DockerConfig) => {
    try {
      const result = await openfoamService.setDockerConfig(config);
      setDockerConfigState(result);
    } catch (err) {
      setError('Failed to update Docker configuration');
      throw err;
    }
  };

  const runTutorial = async (tutorial: string, command: string) => {
    try {
      setCurrentTutorial(tutorial);
      await openfoamService.runCase(tutorial, command, caseRoot);
    } catch (err) {
      setError(`Failed to run tutorial: ${tutorial}`);
      throw err;
    } finally {
      setCurrentTutorial(null);
    }
  };

  const getAvailableFields = async (tutorial: string) => {
    try {
      const { fields } = await openfoamService.getAvailableFields(tutorial);
      return fields;
    } catch (err) {
      setError('Failed to get available fields');
      throw err;
    }
  };

  const getPlotData = async (tutorial: string) => {
    try {
      return await openfoamService.getPlotData(tutorial);
    } catch (err) {
      setError('Failed to get plot data');
      throw err;
    }
  };

  const getMeshVisualization = async (tutorial: string) => {
    try {
      return await openfoamService.getMeshVisualization(tutorial);
    } catch (err) {
      setError('Failed to get mesh visualization');
      throw err;
    }
  };

  return (
    <OpenFOAMContext.Provider
      value={{
        tutorials,
        currentTutorial,
        caseRoot,
        dockerConfig,
        isLoading,
        error,
        loadTutorials,
        setCaseRoot,
        setDockerConfig,
        runTutorial,
        getAvailableFields,
        getPlotData,
        getMeshVisualization,
      }}
    >
      {children}
    </OpenFOAMContext.Provider>
  );
};

export const useOpenFOAM = () => {
  const context = useContext(OpenFOAMContext);
  if (context === undefined) {
    throw new Error('useOpenFOAM must be used within an OpenFOAMProvider');
  }
  return context;
};
