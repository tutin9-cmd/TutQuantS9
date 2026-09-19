import { ViewMode } from '../App';

interface HeaderProps {
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
}

export function Header({ viewMode, setViewMode }: HeaderProps) {
  return (
    <header className="h-14 border-b border-gray-800 bg-[#161b22] flex items-center px-4 flex-shrink-0">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">Q</span>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-white leading-tight">Robinhood Breakout Bot</h1>
            <p className="text-[10px] text-gray-500 leading-tight">Volatility Breakout Strategy • v1.0.0</p>
          </div>
        </div>
      </div>

      <nav className="ml-8 flex gap-1">
        <button
          onClick={() => setViewMode('overview')}
          className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
            viewMode === 'overview'
              ? 'bg-gray-700 text-white'
              : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
          }`}
        >
          📋 Overview
        </button>
        <button
          onClick={() => setViewMode('architecture')}
          className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
            viewMode === 'architecture'
              ? 'bg-gray-700 text-white'
              : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
          }`}
        >
          🏗️ Architecture
        </button>
        <button
          onClick={() => setViewMode('code')}
          className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
            viewMode === 'code'
              ? 'bg-gray-700 text-white'
              : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
          }`}
        >
          💻 Source Code
        </button>
      </nav>

      <div className="ml-auto flex items-center gap-3">
        <span className="px-2 py-0.5 rounded-full bg-green-900/50 text-green-400 text-[10px] font-medium border border-green-800">
          ● PRODUCTION READY
        </span>
        <span className="px-2 py-0.5 rounded-full bg-blue-900/50 text-blue-400 text-[10px] font-medium border border-blue-800">
          Python 3.11+
        </span>
      </div>
    </header>
  );
}
