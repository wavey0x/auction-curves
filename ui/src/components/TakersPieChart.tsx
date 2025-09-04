import React, { useState, useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { BarChart3, Hash, DollarSign } from 'lucide-react';
import { TakerSummary } from '../types/taker';
import { formatUSD, formatNumber, cn } from '../lib/utils';
import { useAddressTag } from '../hooks/useAddressTag';

interface TakersPieChartProps {
  takers: TakerSummary[];
  className?: string;
}

type ChartMode = 'count' | 'volume';

// Custom color palette matching our theme
const COLORS = [
  '#60a5fa', // primary-400
  '#3b82f6', // primary-500
  '#2563eb', // primary-600
  '#1d4ed8', // primary-700
  '#1e40af', // primary-800
  '#1e3a8a', // primary-900
  '#86efac', // green-300
  '#4ade80', // green-400
  '#22c55e', // green-500
  '#16a34a', // green-600
  '#f59e0b', // amber-500
  '#d97706', // amber-600
  '#ea580c', // orange-600
  '#dc2626', // red-600
  '#c026d3', // fuchsia-600
  '#9333ea', // violet-600
];

const TakersPieChart: React.FC<TakersPieChartProps> = ({ takers, className }) => {
  const [mode, setMode] = useState<ChartMode>('count');
  const { getDisplayName } = useAddressTag();

  // Prepare data for the chart
  const chartData = useMemo(() => {
    // Filter out takers with no data for the selected mode
    const validTakers = takers.filter(taker => {
      if (mode === 'count') return taker.total_takes > 0;
      return taker.total_volume_usd && taker.total_volume_usd > 0;
    });

    // Sort by the selected metric 
    const sortedTakers = validTakers
      .sort((a, b) => {
        if (mode === 'count') {
          return b.total_takes - a.total_takes;
        }
        return (b.total_volume_usd || 0) - (a.total_volume_usd || 0);
      });

    // Take top 7 takers and group the rest as "OTHER"
    const top7Takers = sortedTakers.slice(0, 7);
    const otherTakers = sortedTakers.slice(7);

    // Calculate total for percentage calculations (including all takers)
    const total = validTakers.reduce((sum, taker) => {
      if (mode === 'count') return sum + taker.total_takes;
      return sum + (taker.total_volume_usd || 0);
    }, 0);

    // Prepare top 7 data
    const chartData = top7Takers.map((taker, index) => {
      const value = mode === 'count' ? taker.total_takes : (taker.total_volume_usd || 0);
      const percentage = total > 0 ? (value / total) * 100 : 0;
      
      return {
        name: getDisplayName(taker.taker, { addressLength: 6, maxTagLength: 12 }),
        address: taker.taker,
        value,
        percentage,
        color: COLORS[index % COLORS.length],
        takes: taker.total_takes,
        volumeUsd: taker.total_volume_usd,
      };
    });

    // Add "OTHER" group if there are remaining takers
    if (otherTakers.length > 0) {
      const otherValue = otherTakers.reduce((sum, taker) => {
        if (mode === 'count') return sum + taker.total_takes;
        return sum + (taker.total_volume_usd || 0);
      }, 0);
      
      const otherTakes = otherTakers.reduce((sum, taker) => sum + taker.total_takes, 0);
      const otherVolumeUsd = otherTakers.reduce((sum, taker) => sum + (taker.total_volume_usd || 0), 0);
      const otherPercentage = total > 0 ? (otherValue / total) * 100 : 0;
      
      chartData.push({
        name: `OTHER (${otherTakers.length})`,
        address: 'other',
        value: otherValue,
        percentage: otherPercentage,
        color: '#6b7280', // gray-500
        takes: otherTakes,
        volumeUsd: otherVolumeUsd,
      });
    }

    return chartData;
  }, [takers, mode, getDisplayName]);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) return null;
    
    const data = payload[0].payload;
    
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 shadow-lg">
        <div className="text-sm font-medium text-gray-200 mb-2">{data.name}</div>
        <div className="space-y-1 text-xs">
          <div className="flex items-center justify-between space-x-3">
            <span className="text-gray-400">Takes:</span>
            <span className="text-gray-200 font-mono">{formatNumber(data.takes)}</span>
          </div>
          {data.volumeUsd && (
            <div className="flex items-center justify-between space-x-3">
              <span className="text-gray-400">Volume:</span>
              <span className="text-gray-200 font-mono">{formatUSD(data.volumeUsd)}</span>
            </div>
          )}
          <div className="flex items-center justify-between space-x-3 border-t border-gray-700 pt-1">
            <span className="text-gray-400">Share:</span>
            <span className="text-primary-400 font-mono">{data.percentage.toFixed(1)}%</span>
          </div>
        </div>
      </div>
    );
  };

  // Custom legend
  const renderLegend = (props: any) => {
    const { payload } = props;
    
    return (
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mt-4">
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center space-x-2">
            <div 
              className="w-3 h-3 rounded-sm flex-shrink-0"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-gray-300 truncate font-mono">
              {entry.payload.name}
            </span>
            <span className="text-gray-500 text-xs">
              ({entry.payload.percentage.toFixed(1)}%)
            </span>
          </div>
        ))}
      </div>
    );
  };

  if (!chartData.length) {
    return (
      <div className={cn("bg-gray-900 border border-gray-800 rounded-lg p-6", className)}>
        <div className="text-center text-gray-500">
          <BarChart3 className="h-12 w-12 mx-auto mb-3 text-gray-600" />
          <p className="text-sm">No data available for chart</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("bg-gray-900 border border-gray-800 rounded-lg p-6", className)}>
      {/* Header with toggle */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <BarChart3 className="h-5 w-5 text-primary-400" />
          <h3 className="text-lg font-medium text-gray-200">
            Solver Distribution
          </h3>
        </div>
        
        {/* Mode toggle */}
        <div className="flex items-center bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setMode('count')}
            className={cn(
              "flex items-center space-x-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
              mode === 'count'
                ? "bg-primary-600 text-white"
                : "text-gray-400 hover:text-gray-200"
            )}
          >
            <Hash className="h-4 w-4" />
            <span>Count</span>
          </button>
          <button
            onClick={() => setMode('volume')}
            className={cn(
              "flex items-center space-x-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
              mode === 'volume'
                ? "bg-primary-600 text-white"
                : "text-gray-400 hover:text-gray-200"
            )}
          >
            <DollarSign className="h-4 w-4" />
            <span>Volume</span>
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              outerRadius={100}
              innerRadius={30}
              paddingAngle={2}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend content={renderLegend} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Summary stats */}
      <div className="mt-4 pt-4 border-t border-gray-800">
        <div className="grid grid-cols-2 gap-4 text-center">
          <div>
            <div className="text-xl font-semibold text-gray-200">
              {chartData.length}
            </div>
            <div className="text-xs text-gray-500">Top Solvers</div>
          </div>
          <div>
            <div className="text-xl font-semibold text-gray-200">
              {mode === 'count' 
                ? formatNumber(chartData.reduce((sum, d) => sum + d.takes, 0))
                : formatUSD(chartData.reduce((sum, d) => sum + (d.volumeUsd || 0), 0))
              }
            </div>
            <div className="text-xs text-gray-500">
              Total {mode === 'count' ? 'Takes' : 'Volume'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TakersPieChart;