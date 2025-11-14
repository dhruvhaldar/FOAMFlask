import { useState, useEffect } from 'react';
import { useDocker } from '@/contexts/DockerContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/components/ui/use-toast';
import { CaseSettings } from '@/components/CaseSettings';
import { OpenFOAMSettings } from '@/components/OpenFOAMSettings';
import { CaseStatus } from '@/components/CaseStatus';
import { Label } from '@radix-ui/react-label';


export default function SetupPage() {
  const { 
    caseConfig, 
    loadTutorial,
    isLoading
  } = useDocker();
  
  const { toast } = useToast();
  const [selectedTutorial, setSelectedTutorial] = useState<string>('');
  const [isLoadingTutorial, setIsLoadingTutorial] = useState(false);

  // Update local state when config changes
  useEffect(() => {
    if (caseConfig?.caseDirectory) {
      console.log('Setting case directory to:', caseConfig.caseDirectory);
    }
  }, [caseConfig]);

  const handleLoadTutorial = async (): Promise<void> => {
    if (!selectedTutorial) {
      toast({
        title: 'Error',
        description: 'Please select a tutorial',
        variant: 'destructive',
      });
      return;
    }

    if (!caseConfig?.caseDirectory) {
      toast({
        title: 'Error',
        description: 'Please set a case directory first',
        variant: 'destructive',
      });
      return;
    }

    try {
      setIsLoadingTutorial(true);
      await loadTutorial(selectedTutorial, caseConfig.caseDirectory);
      toast({
        title: 'Success',
        description: `Tutorial '${selectedTutorial}' loaded successfully`,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load tutorial';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsLoadingTutorial(false);
    }
  };

  // Tutorial options
  const tutorialOptions = [
    { value: 'cavity', label: 'Cavity' },
    { value: 'airfoil2D', label: '2D Airfoil' },
    { value: 'pitzDaily', label: 'Pitz Daily' },
    { value: 'motorBike', label: 'Motor Bike' },
  ];

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="grid gap-6 md:grid-cols-2">
        {/* Left column - Configuration */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>[setup.tsx] Case Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <CaseSettings />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>[setup.tsx] Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <OpenFOAMSettings />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Load Tutorial</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="tutorial">Select Tutorial</Label>
                <select
                  id="tutorial"
                  value={selectedTutorial}
                  onChange={(e) => setSelectedTutorial(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={isLoading || isLoadingTutorial}
                >
                  <option value="">-- Select a tutorial --</option>
                  {tutorialOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <Button 
                onClick={handleLoadTutorial}
                disabled={!selectedTutorial || isLoading || isLoadingTutorial}
                className="w-full"
              >
                {isLoadingTutorial ? 'Loading...' : 'Load Tutorial'}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Right column - Status */}
        <div className="space-y-6">
          <CaseStatus />
          
          {/* <Card>
            <CardHeader>
              <CardTitle>Next Steps</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>1. Set your case directory</p>
              <p>2. Configure Docker settings (optional)</p>
              <p>3. Select and load a tutorial</p>
              <p>4. Proceed to the Run tab to start the simulation</p>
            </CardContent>
          </Card> */}
        </div>
      </div>
    </div>
  );
}
