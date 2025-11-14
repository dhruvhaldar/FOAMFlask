import React from 'react';
import { useDocker } from '../contexts/DockerContext';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from '@radix-ui/react-label';

export const CaseSettings: React.FC = () => {
  const { 
    caseConfig,
    updateCaseConfig,
    isLoading,
    error
  } = useDocker();
  const [localConfig, setLocalConfig] = React.useState({
    caseDirectory: caseConfig?.caseDirectory || '',
    openfoamVersion: caseConfig?.openfoamVersion || ''
  });

  React.useEffect(() => {
    if (caseConfig) {
      setLocalConfig({
        caseDirectory: caseConfig.caseDirectory || '',
        openfoamVersion: caseConfig.openfoamVersion || ''
      });
    }
  }, [caseConfig]);

  const handleSave = async () => {
    try {
      await updateCaseConfig(localConfig);
    } catch (err) {
      console.error('Failed to save case config:', err);
    }
  };

  const handleBrowse = async () => {
    // This would open a file dialog in a real implementation
    // For now, we'll just log it
    console.log('Opening file dialog to select case directory');
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>[CaseSettings.tsx] Case Settings</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="text-red-500 text-sm mb-4">{error}</div>
        )}
        
        <div className="space-y-2">
          <Label htmlFor="caseDirectory">Case Directory</Label>
          <div className="flex space-x-2">
            <Input
              id="caseDirectory"
              value={localConfig.caseDirectory}
              onChange={(e) => 
                setLocalConfig({...localConfig, caseDirectory: e.target.value})
              }
              placeholder="Select or enter case directory"
              disabled={isLoading}
              className="flex-1"
            />
            <Button 
              variant="outline" 
              onClick={handleBrowse}
              disabled={isLoading}
            >
              Browse...
            </Button>
          </div>
        </div>

        {/* <div className="space-y-2">
          <Label htmlFor="openfoamVersion">OpenFOAM Version</Label>
          <Input
            id="openfoamVersion"
            value={localConfig.openfoamVersion}
            onChange={(e) => 
              setLocalConfig({...localConfig, openfoamVersion: e.target.value})
            }
            disabled={isLoading}
          />
        </div> */}

        {/* <div className="flex justify-end">
          <Button 
            onClick={handleSave} 
            disabled={isLoading}
          >
            {isLoading ? 'Saving...' : 'Save Configuration'}
          </Button>
        </div> */}
      </CardContent>
    </Card>
  );
};
