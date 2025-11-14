// src/components/OpenFOAMSettings.tsx
import React from 'react';
import { useDocker } from '../contexts/DockerContext';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from '@radix-ui/react-label';

export const OpenFOAMSettings: React.FC = () => {
  const { 
    dockerConfig, 
    updateDockerConfig,
    isLoading,
    error
  } = useDocker();
  
  const [localConfig, setLocalConfig] = React.useState(() => ({
  dockerImage: dockerConfig.dockerImage || 'haldardhruv/ubuntu_noble_openfoam:v12',
  openfoamVersion: dockerConfig.openfoamVersion || '12'
}));

React.useEffect(() => {
  setLocalConfig({
    dockerImage: dockerConfig.dockerImage || 'haldardhruv/ubuntu_noble_openfoam:v12',
    openfoamVersion: dockerConfig.openfoamVersion || '12'
  });
}, [dockerConfig]);

  const handleSave = async () => {
    try {
      await updateDockerConfig(localConfig);
    } catch (err) {
      console.error('Failed to save Docker config:', err);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>[OpenFOAMSettings.tsx] Docker Configuration</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="text-red-500 text-sm mb-4">{error}</div>
        )}
        
        <div className="space-y-2">
          <Label htmlFor="dockerImage">Docker Image</Label>
          <Input
            id="dockerImage"
            value={localConfig.dockerImage}
            onChange={(e) => 
              setLocalConfig({...localConfig, dockerImage: e.target.value})
            }
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="openfoamVersion">OpenFOAM Version</Label>
          <Input
            id="openfoamVersion"
            value={localConfig.openfoamVersion}
            onChange={(e) => 
              setLocalConfig({...localConfig, openfoamVersion: e.target.value})
            }
            disabled={isLoading}
          />
        </div>

        <Button 
          onClick={handleSave} 
          disabled={isLoading}
        >
          {isLoading ? 'Saving...' : 'Save Configuration'}
        </Button>
      </CardContent>
    </Card>
  );
};