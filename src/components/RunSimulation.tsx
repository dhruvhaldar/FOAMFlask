// src/components/RunSimulation.tsx
import React, { useState } from 'react';
import { useDocker } from '../contexts/DockerContext';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from '@radix-ui/react-label';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

export const RunSimulation: React.FC = () => {
  const { 
    loadTutorial, 
    runCase,
    isLoading,
    error
  } = useDocker();
  
  const [tutorial, setTutorial] = useState('');
  const [caseDir, setCaseDir] = useState('');
  const [command, setCommand] = useState('Allrun');
  const [output, setOutput] = useState<string[]>([]);

  const handleLoadTutorial = async () => {
    try {
      const result = await loadTutorial(tutorial, caseDir);
      setOutput(prev => [...prev, `Tutorial loaded: ${JSON.stringify(result)}`]);
    } catch (err) {
      setOutput(prev => [...prev, `Error: ${err.message}`]);
    }
  };

  const handleRunCase = async () => {
    try {
      const result = await runCase(tutorial, command, caseDir);
      setOutput(prev => [...prev, `Case running: ${JSON.stringify(result)}`]);
    } catch (err) {
      setOutput(prev => [...prev, `Error: ${err.message}`]);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Run Simulation</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="text-red-500 text-sm mb-4">{error}</div>
        )}

        <div className="space-y-2">
          <Label htmlFor="tutorial">Tutorial</Label>
          <Input
            id="tutorial"
            value={tutorial}
            onChange={(e) => setTutorial(e.target.value)}
            placeholder="e.g., incompressible/simpleFoam/cavity"
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="caseDir">Case Directory</Label>
          <Input
            id="caseDir"
            value={caseDir}
            onChange={(e) => setCaseDir(e.target.value)}
            placeholder="e.g., /path/to/case"
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="command">Command</Label>
          <Input
            id="command"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder="e.g., Allrun"
            disabled={isLoading}
          />
        </div>

        <div className="flex space-x-2">
          <Button 
            onClick={handleLoadTutorial}
            disabled={isLoading || !tutorial || !caseDir}
          >
            {isLoading ? 'Loading...' : 'Load Tutorial'}
          </Button>
          
          <Button 
            onClick={handleRunCase}
            disabled={isLoading || !tutorial || !caseDir || !command}
            variant="outline"
          >
            Run Case
          </Button>
        </div>

        {output.length > 0 && (
          <div className="mt-4 p-4 bg-gray-100 rounded-md max-h-48 overflow-y-auto">
            {output.map((line, i) => (
              <div key={i} className="text-sm font-mono">{line}</div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};