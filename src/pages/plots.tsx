// src/pages/plots.tsx
import { useState, useEffect, useCallback, useRef } from 'react';
import Plot from 'react-plotly.js';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/use-toast';
import { useNotifications } from '@/hooks/useNotifications';

// Plotly colors for consistency
const PLOTLY_COLORS = {
  blue: '#1f77b4',
  orange: '#ff7f0e',
  green: '#2ca02c',
  red: '#d62728',
  purple: '#9467bd',
  brown: '#8c564b',
  pink: '#e377c2',
  gray: '#7f7f7f',
  yellow: '#bcbd22',
  teal: '#17becf',
  cyan: '#17becf',
  magenta: '#e377c2',
};

// Common plot layout
const plotLayout = {
  font: { family: '"Computer Modern Serif", serif', size: 12 },
  plot_bgcolor: 'white',
  paper_bgcolor: '#ffffff',
  margin: { l: 50, r: 20, t: 40, b: 40, pad: 0 },
  height: 400,
  autosize: true,
  showlegend: true,
  xaxis: {
    showgrid: false,
    linewidth: 1,
  },
  yaxis: {
    showgrid: false,
    linewidth: 1,
  },
};

export default function PlotsPage() {
  const { showNotification } = useNotifications();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [plotData, setPlotData] = useState<any[]>([]);
  const [plotLayoutState, setPlotLayout] = useState(plotLayout);
  const plotContainerRef = useRef<HTMLDivElement>(null);

  // Example data - in a real app, this would come from your API
  const [availablePlots] = useState([
    { id: 'residuals', name: 'Residuals' },
    { id: 'forces', name: 'Forces' },
    { id: 'probes', name: 'Probes' },
  ]);

  const [selectedPlot, setSelectedPlot] = useState<string>('');

  // Load plot data when selected plot changes
  useEffect(() => {
    if (!selectedPlot) return;

    const loadPlotData = async () => {
      setIsLoading(true);
      try {
        // In a real app, you would fetch this from your API
        // const data = await fetchPlotData(selectedPlot);
        
        // Mock data for demonstration
        await new Promise(resolve => setTimeout(resolve, 500));
        
        let newData: any[] = [];
        
        switch (selectedPlot) {
          case 'residuals':
            newData = generateResidualsData();
            break;
          case 'forces':
            newData = generateForcesData();
            break;
          case 'probes':
            newData = generateProbesData();
            break;
          default:
            newData = [];
        }
        
        setPlotData(newData);
        
        // Update layout with plot-specific settings
        setPlotLayout(prev => ({
          ...prev,
          title: `Plot: ${selectedPlot.charAt(0).toUpperCase() + selectedPlot.slice(1)}`,
          xaxis: { ...prev.xaxis, title: 'Iteration' },
          yaxis: { ...prev.yaxis, title: 'Value', type: 'log' },
        }));
        
      } catch (error) {
        console.error('Error loading plot data:', error);
        showNotification('Failed to load plot data', 'error');
      } finally {
        setIsLoading(false);
      }
    };

    loadPlotData();
  }, [selectedPlot, showNotification]);

  // Generate mock residuals data
  const generateResidualsData = () => {
    const iterations = Array.from({ length: 100 }, (_, i) => i + 1);
    const p = iterations.map(i => 1 / (i * 0.5 + Math.random()));
    const Ux = iterations.map(i => 1 / (i * 0.4 + Math.random() * 0.5));
    const k = iterations.map(i => 1 / (i * 0.3 + Math.random() * 0.3));
    const omega = iterations.map(i => 1 / (i * 0.2 + Math.random() * 0.2));

    return [
      {
        x: iterations,
        y: p,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'p',
        line: { color: PLOTLY_COLORS.blue, width: 2 },
        marker: { size: 4 },
      },
      {
        x: iterations,
        y: Ux,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Ux',
        line: { color: PLOTLY_COLORS.orange, width: 2 },
        marker: { size: 4 },
      },
      {
        x: iterations,
        y: k,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'k',
        line: { color: PLOTLY_COLORS.green, width: 2 },
        marker: { size: 4 },
      },
      {
        x: iterations,
        y: omega,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'omega',
        line: { color: PLOTLY_COLORS.red, width: 2 },
        marker: { size: 4 },
      },
    ];
  };

  // Generate mock forces data
  const generateForcesData = () => {
    const time = Array.from({ length: 50 }, (_, i) => i * 0.1);
    const drag = time.map(t => Math.sin(t) * (1 + Math.random() * 0.1));
    const lift = time.map(t => Math.cos(t) * (1 + Math.random() * 0.1));

    return [
      {
        x: time,
        y: drag,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Drag',
        line: { color: PLOTLY_COLORS.purple, width: 2 },
        marker: { size: 4 },
      },
      {
        x: time,
        y: lift,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Lift',
        line: { color: PLOTLY_COLORS.teal, width: 2 },
        marker: { size: 4 },
      },
    ];
  };

  // Generate mock probes data
  const generateProbesData = () => {
    const time = Array.from({ length: 100 }, (_, i) => i * 0.05);
    const probe1 = time.map(t => Math.sin(t) * (1 + Math.random() * 0.1));
    const probe2 = time.map(t => Math.cos(t) * (1 + Math.random() * 0.1));
    const probe3 = time.map(t => Math.sin(t + 1) * (1 + Math.random() * 0.1));

    return [
      {
        x: time,
        y: probe1,
        type: 'scatter',
        mode: 'lines',
        name: 'Probe 1',
        line: { color: PLOTLY_COLORS.blue, width: 2 },
      },
      {
        x: time,
        y: probe2,
        type: 'scatter',
        mode: 'lines',
        name: 'Probe 2',
        line: { color: PLOTLY_COLORS.orange, width: 2 },
      },
      {
        x: time,
        y: probe3,
        type: 'scatter',
        mode: 'lines',
        name: 'Probe 3',
        line: { color: PLOTLY_COLORS.green, width: 2 },
      },
    ];
  };

  const handleDownloadPlot = (format: 'png' | 'svg' | 'jpeg' = 'png') => {
    if (!plotContainerRef.current) return;

    const plotDiv = plotContainerRef.current.querySelector('.js-plotly-plot');
    if (!plotDiv) return;

    // @ts-ignore
    const gd = plotDiv._fullLayout._paperdiv._fullLayout._plots['xy']._fullData[0]._fullInput._context.document;
    
    // @ts-ignore
    Plotly.downloadImage(gd, {
      format,
      filename: `plot_${selectedPlot}`,
      width: plotContainerRef.current.offsetWidth,
      height: 400,
      scale: 2,
    });

    showNotification(`Plot downloaded as ${format.toUpperCase()}`, 'success');
  };

  const handleDownloadData = () => {
    if (plotData.length === 0) return;

    let csvContent = 'x,' + plotData.map(series => series.name).join(',') + '\\n';
    
    // Find max length of all series
    const maxLength = Math.max(...plotData.map(series => series.x.length));
    
    for (let i = 0; i < maxLength; i++) {
      const row = [i];
      plotData.forEach(series => {
        row.push(series.y[i] !== undefined ? series.y[i] : '');
      });
      csvContent += row.join(',') + '\\n';
    }

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `plot_data_${selectedPlot}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    showNotification('Data downloaded as CSV', 'success');
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex flex-col space-y-2">
        <h1 className="text-3xl font-bold">Plots</h1>
        <p className="text-muted-foreground">
          Visualize simulation results and monitoring data
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <CardTitle>Plot Viewer</CardTitle>
              <p className="text-sm text-muted-foreground">
                {selectedPlot
                  ? `Showing: ${selectedPlot.charAt(0).toUpperCase() + selectedPlot.slice(1)}`
                  : 'Select a plot type to begin'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Select
                value={selectedPlot}
                onValueChange={setSelectedPlot}
                disabled={isLoading}
              >
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Select a plot type" />
                </SelectTrigger>
                <SelectContent>
                  {availablePlots.map(plot => (
                    <SelectItem key={plot.id} value={plot.id}>
                      {plot.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                onClick={() => selectedPlot && handleDownloadData()}
                disabled={!selectedPlot || isLoading || plotData.length === 0}
              >
                Download Data (CSV)
              </Button>
              <div className="relative">
                <Button
                  variant="outline"
                  onClick={() => handleDownloadPlot('png')}
                  disabled={!selectedPlot || isLoading || plotData.length === 0}
                >
                  Export Plot
                </Button>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div
            ref={plotContainerRef}
            className="w-full min-h-[500px] flex items-center justify-center bg-white rounded-lg border"
          >
            {isLoading ? (
              <div className="flex flex-col items-center justify-center space-y-2">
                <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                <p className="text-muted-foreground">Loading plot data...</p>
              </div>
            ) : selectedPlot ? (
              <Plot
                data={plotData}
                layout={plotLayoutState}
                config={{
                  displayModeBar: true,
                  displaylogo: false,
                  responsive: true,
                  modeBarButtonsToRemove: [
                    'sendDataToCloud',
                    'select2d',
                    'lasso2d',
                    'zoomIn2d',
                    'zoomOut2d',
                    'autoScale2d',
                    'resetScale2d',
                  ],
                }}
                className="w-full h-full"
              />
            ) : (
              <div className="text-center p-8 text-muted-foreground">
                <p>Select a plot type from the dropdown to view data</p>
              </div>
            )}
          </div>

          {selectedPlot && (
            <div className="mt-6 space-y-4">
              <div className="space-y-2">
                <Label>Plot Controls</Label>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setPlotLayout(prev => ({
                        ...prev,
                        yaxis: {
                          ...prev.yaxis,
                          type: prev.yaxis?.type === 'log' ? 'linear' : 'log',
                        },
                      }));
                    }}
                  >
                    {plotLayoutState.yaxis?.type === 'log' ? 'Linear Scale' : 'Log Scale'}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setPlotLayout(prev => ({
                        ...prev,
                        showlegend: !prev.showlegend,
                      }));
                    }}
                  >
                    {plotLayoutState.showlegend ? 'Hide Legend' : 'Show Legend'}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}