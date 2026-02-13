import Plot from 'react-plotly.js';

interface PlotlyChartProps {
  spec: { data: Plotly.Data[]; layout?: Partial<Plotly.Layout> };
  height?: number;
  className?: string;
}

export function PlotlyChart({ spec, height = 400, className }: PlotlyChartProps) {
  const layout: Partial<Plotly.Layout> = {
    ...spec.layout,
    paper_bgcolor: 'transparent',
    plot_bgcolor: '#1e293b',
    font: { color: '#94a3b8' },
    height,
    autosize: true,
    margin: { t: 40, r: 20, b: 40, l: 50 },
  };

  return (
    <div className={className}>
      <Plot
        data={spec.data}
        layout={layout}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%' }}
      />
    </div>
  );
}
