import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { useDocker } from '../contexts/DockerContext';

export const CaseStatus: React.FC = () => {
  const { caseConfig, dockerConfig } = useDocker();

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Case Status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">Case Directory</p>
            <p className="text-sm">
              {caseConfig?.caseDirectory || 'Not set'}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">Docker Image</p>
            <p className="text-sm">
              {dockerConfig?.dockerImage || 'Not set'}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">OpenFOAM Version</p>
            <p className="text-sm">
              {caseConfig?.openfoamVersion || dockerConfig?.openfoamVersion || 'Not set'}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
