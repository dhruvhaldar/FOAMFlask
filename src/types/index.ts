export interface MeshInfo {
  n_points?: number;
  n_cells?: number;
  length?: number;
  volume?: number;
  bounds?: number[];
  center?: number[];
  point_arrays?: string[];
  success?: boolean;
  error?: string;
}

export interface MeshFile {
  name: string;
  path: string;
  relative_path: string;
}

export interface PlotData {
  x: number[];
  y: number[];
  name: string;
  type: string;
  mode: string;
  marker?: {
    color: string;
    size: number;
  };
  line?: {
    color: string;
    width: number;
  };
}

export interface PlotLayout {
  title: string;
  xaxis: {
    title: string;
  };
  yaxis: {
    title: string;
  };
  showlegend: boolean;
  legend: {
    orientation?: string;
    y?: number;
    x?: number;
    xanchor?: string;
    yanchor?: string;
  };
  font: {
    family: string;
    size: number;
  };
  plot_bgcolor: string;
  paper_bgcolor: string;
  margin: {
    l: number;
    r: number;
    t: number;
    b: number;
    pad: number;
  };
  height?: number;
  autosize?: boolean;
}

export interface Notification {
  id: string;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  timestamp: number;
  duration?: number;
}
