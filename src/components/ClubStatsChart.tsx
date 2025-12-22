'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { ClubStats } from '@/types/golf';

interface ClubStatsChartProps {
  data: ClubStats[];
}

export default function ClubStatsChart({ data }: ClubStatsChartProps) {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Club Performance Overview
      </h3>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="club"
              tick={{ fill: '#6b7280' }}
              label={{ value: 'Club', position: 'insideBottom', offset: -5 }}
            />
            <YAxis
              tick={{ fill: '#6b7280' }}
              label={{ value: 'Average Carry (yards)', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1f2937',
                border: 'none',
                borderRadius: '8px',
                color: '#fff',
              }}
            />
            <Legend />
            <Bar dataKey="avgCarry" fill="#3b82f6" name="Avg Carry" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
        {data.map((club) => (
          <div
            key={club.club}
            className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
          >
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              {club.club}
            </p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {club.avgCarry.toFixed(0)}
              <span className="text-sm font-normal text-gray-500 ml-1">yds</span>
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {club.shots} shots
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
