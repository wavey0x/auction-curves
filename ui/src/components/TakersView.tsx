import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../lib/api';
import TakersTable from './TakersTable';
import TakersPieChart from './TakersPieChart';
import LoadingSpinner from './LoadingSpinner';
import { AlertCircle } from 'lucide-react';

interface TakersViewProps {
  chainFilter?: number;
  limit?: number;
}

const TakersView: React.FC<TakersViewProps> = ({ chainFilter, limit = 50 }) => {
  // Fetch all takers data for the chart (use a higher limit to get more comprehensive data)
  const { data: takersData, isLoading, error } = useQuery({
    queryKey: ['takers-full', chainFilter],
    queryFn: () => apiClient.getTakers({
      sort_by: 'volume',
      page: 1,
      limit: 100, // Get top 100 takers for the chart
      chain_id: chainFilter
    }),
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12 text-red-400">
        <AlertCircle className="h-5 w-5 mr-2" />
        <span>Failed to load takers data</span>
      </div>
    );
  }

  const takers = takersData?.takers || [];

  return (
    <div className="space-y-6">
      {/* Takers Table */}
      <TakersTable limit={limit} chainFilter={chainFilter} />
      
      {/* Pie Chart */}
      {takers.length > 0 && (
        <TakersPieChart takers={takers} />
      )}
    </div>
  );
};

export default TakersView;