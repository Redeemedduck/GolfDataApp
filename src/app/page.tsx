'use client';

import { useState } from 'react';
import ChatInterface from '@/components/ChatInterface';
import ClubStatsChart from '@/components/ClubStatsChart';
import { Activity, TrendingUp, Target } from 'lucide-react';
import type { ClubStats } from '@/types/golf';

// Mock data for demonstration
const mockClubStats: ClubStats[] = [
  { club: 'Driver', shots: 42, avgCarry: 235, avgSmash: 1.42, avgBallSpeed: 152, consistency: 12.5 },
  { club: '3-Wood', shots: 28, avgCarry: 218, avgSmash: 1.38, avgBallSpeed: 145, consistency: 15.2 },
  { club: '5-Iron', shots: 35, avgCarry: 185, avgSmash: 1.35, avgBallSpeed: 128, consistency: 10.8 },
  { club: '7-Iron', shots: 48, avgCarry: 165, avgSmash: 1.33, avgBallSpeed: 118, consistency: 9.2 },
  { club: '9-Iron', shots: 52, avgCarry: 142, avgSmash: 1.30, avgBallSpeed: 105, consistency: 8.5 },
  { club: 'PW', shots: 45, avgCarry: 128, avgSmash: 1.28, avgBallSpeed: 98, consistency: 7.8 },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState<'chat' | 'data'>('chat');

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-950 dark:to-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <div className="bg-gradient-to-br from-blue-600 to-blue-700 p-3 rounded-lg">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Golf Data Platform
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  AI-Powered Performance Analysis
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-6">
              <div className="flex items-center space-x-2 bg-green-50 dark:bg-green-900/20 px-4 py-2 rounded-lg">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-sm font-medium text-green-700 dark:text-green-400">
                  BigQuery Connected
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Stats Cards */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Total Shots
              </h3>
              <Target className="w-5 h-5 text-blue-600" />
            </div>
            <p className="text-3xl font-bold text-gray-900 dark:text-white">
              555
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              Across 45 sessions
            </p>
          </div>

          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Avg Smash Factor
              </h3>
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
            <p className="text-3xl font-bold text-gray-900 dark:text-white">
              1.35
            </p>
            <p className="text-sm text-green-600 dark:text-green-400 mt-2">
              +2.3% this week
            </p>
          </div>

          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Most Used Club
              </h3>
              <Activity className="w-5 h-5 text-purple-600" />
            </div>
            <p className="text-3xl font-bold text-gray-900 dark:text-white">
              9-Iron
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              52 shots recorded
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('chat')}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'chat'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                AI Coach Chat
              </button>
              <button
                onClick={() => setActiveTab('data')}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'data'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                Performance Data
              </button>
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="min-h-[600px]">
          {activeTab === 'chat' && <ChatInterface />}
          {activeTab === 'data' && <ClubStatsChart data={mockClubStats} />}
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-500 dark:text-gray-400">
            Powered by Vertex AI Agent Builder + BigQuery
          </p>
        </div>
      </footer>
    </div>
  );
}
