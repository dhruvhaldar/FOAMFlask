import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

export function CaseView() {
  return (
    <div className="container mx-auto p-6">
      <Card>
        <CardHeader>
          <CardTitle>Case View</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Case details will be displayed here.</p>
        </CardContent>
      </Card>
    </div>
  );
}
