/**
 * ECharts-based metrics visualisation for the Dashboard.
 */

import ReactECharts from 'echarts-for-react';
import type { MetricValue } from '../types/api';

interface MetricsChartProps {
  metrics: MetricValue[];
}

export default function MetricsChart({ metrics }: MetricsChartProps) {
  if (metrics.length === 0) return null;

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#f1f5f9', fontSize: 12 },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category' as const,
      data: metrics.map((m) => m.metric_name_cn),
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        rotate: 30,
      },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    },
    yAxis: {
      type: 'value' as const,
      axisLabel: { color: '#94a3b8', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
    },
    series: [
      {
        name: '数值',
        type: 'bar',
        data: metrics.map((m) => m.value ?? 0),
        itemStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: '#3b82f6' },
              { offset: 1, color: '#1a3a5c' },
            ],
          },
          borderRadius: [4, 4, 0, 0],
        },
        barWidth: '40%',
      },
    ],
  };

  return (
    <div className="glass-card p-4">
      <h3 className="text-text-secondary text-xs mb-3 font-medium">核心指标概览</h3>
      <ReactECharts option={option} style={{ height: 240 }} />
    </div>
  );
}
