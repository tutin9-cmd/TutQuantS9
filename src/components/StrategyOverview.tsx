import { ViewMode, FileData } from '../App';

interface StrategyOverviewProps {
  onNavigate: (mode: ViewMode) => void;
  onFileSelect: (path: string, language: string) => void;
}

export function StrategyOverview({ onNavigate, onFileSelect }: StrategyOverviewProps) {
  return (
    <div className="h-full overflow-auto bg-[#0d1117]">
      <div className="max-w-5xl mx-auto p-6">
        {/* Hero */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-green-500/20">
              <span className="text-2xl">📈</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Robinhood Breakout Bot</h1>
              <p className="text-sm text-gray-400">Volatility Breakout Strategy • Hybrid LLM + Deterministic Risk Engine</p>
            </div>
          </div>
          <p className="text-sm text-gray-300 max-w-3xl leading-relaxed">
            A production-ready, fail-closed crypto trading bot that executes a Volatility Breakout strategy 
            on Robinhood's Agentic Trading MCP. The architecture is strictly hybrid: a deterministic Python 
            risk engine handles all math, position sizing, and execution, while an LLM is used ONLY as a 
            "Regime Guard" to veto bad trades based on sentiment/on-chain data.
          </p>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-4 gap-3 mb-8">
          {[
            { label: 'Account Size', value: '$250', icon: '💰', color: 'green' },
            { label: 'Max Position', value: '$50', icon: '📊', color: 'blue' },
            { label: 'Max Concurrent', value: '3', icon: '🔄', color: 'purple' },
            { label: 'Scan Interval', value: '5min', icon: '⏱️', color: 'amber' },
          ].map(({ label, value, icon, color }) => (
            <div key={label} className={`bg-[#161b22] rounded-lg p-4 border border-${color}-900/30`}>
              <div className="text-lg mb-1">{icon}</div>
              <div className="text-lg font-bold text-white">{value}</div>
              <div className="text-[11px] text-gray-500">{label}</div>
            </div>
          ))}
        </div>

        {/* Strategy Description */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="bg-[#161b22] rounded-xl border border-gray-800 p-5">
            <h3 className="text-sm font-semibold text-green-400 mb-3">🎯 Entry Conditions (ALL required)</h3>
            <ol className="space-y-2 text-xs text-gray-300">
              <li className="flex gap-2">
                <span className="text-green-400 font-bold">1.</span>
                <span><strong className="text-white">BB Squeeze:</strong> 20-period Bollinger Band Width at 30-day low (bottom 20th percentile)</span>
              </li>
              <li className="flex gap-2">
                <span className="text-green-400 font-bold">2.</span>
                <span><strong className="text-white">Breakout:</strong> Price breaks above 20-period Donchian Channel OR Upper Bollinger Band</span>
              </li>
              <li className="flex gap-2">
                <span className="text-green-400 font-bold">3.</span>
                <span><strong className="text-white">Volume:</strong> Current volume &gt; 1.5x the 20-period SMA of volume</span>
              </li>
              <li className="flex gap-2">
                <span className="text-green-400 font-bold">4.</span>
                <span><strong className="text-white">LLM Approval:</strong> Regime guard confirms on-chain + social data supports breakout</span>
              </li>
            </ol>
          </div>

          <div className="bg-[#161b22] rounded-xl border border-gray-800 p-5">
            <h3 className="text-sm font-semibold text-red-400 mb-3">🚪 Exit Logic</h3>
            <div className="space-y-2 text-xs text-gray-300">
              <div className="flex items-start gap-2">
                <span className="text-red-400 mt-0.5">●</span>
                <span><strong className="text-white">Stop-Loss:</strong> 2x ATR(14) below entry price</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-green-400 mt-0.5">●</span>
                <span><strong className="text-white">Take-Profit:</strong> Sell 50% at +8% profit</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-blue-400 mt-0.5">●</span>
                <span><strong className="text-white">Trailing Stop:</strong> Trail remaining 50% behind 20-SMA</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-yellow-400 mt-0.5">●</span>
                <span><strong className="text-white">Time-Stop:</strong> Liquidate if flat/negative after 48h</span>
              </div>
            </div>
          </div>
        </div>

        {/* File Structure */}
        <div className="bg-[#161b22] rounded-xl border border-gray-800 p-5 mb-8">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">📁 Project Structure</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1 text-xs font-mono">
              <div className="text-gray-500">robinhood_breakout_bot/</div>
              {[
                { name: 'config.py', desc: 'Pydantic settings, fail-closed validation', file: 'config.py' },
                { name: 'main.py', desc: 'Entry point, scheduler, orchestration', file: 'main.py' },
                { name: 'src/data_fetcher.py', desc: 'Polygon, LunarCrush, Arkham APIs', file: 'src/data_fetcher.py' },
                { name: 'src/technical_engine.py', desc: 'BB, ATR, Donchian, Volume SMA', file: 'src/technical_engine.py' },
              ].map(({ name, desc, file }) => (
                <button
                  key={file}
                  onClick={() => onFileSelect(file, 'python')}
                  className="flex items-center gap-2 w-full text-left px-2 py-1 rounded hover:bg-gray-800/50 transition-colors group"
                >
                  <span className="text-blue-400">├─</span>
                  <span className="text-gray-300 group-hover:text-white">{name}</span>
                  <span className="text-gray-600 ml-auto text-[10px]">{desc}</span>
                </button>
              ))}
            </div>
            <div className="space-y-1 text-xs font-mono">
              <div className="text-gray-500 opacity-0">.</div>
              {[
                { name: 'src/llm_regime_guard.py', desc: 'LLM veto, strict JSON parsing', file: 'src/llm_regime_guard.py' },
                { name: 'src/risk_engine.py', desc: 'Hard limits, position sizing', file: 'src/risk_engine.py' },
                { name: 'src/execution_manager.py', desc: 'Robinhood MCP, idempotency', file: 'src/execution_manager.py' },
                { name: 'tests/', desc: 'Unit tests for core modules', file: 'tests/test_risk_engine.py' },
              ].map(({ name, desc, file }) => (
                <button
                  key={file}
                  onClick={() => onFileSelect(file, 'python')}
                  className="flex items-center gap-2 w-full text-left px-2 py-1 rounded hover:bg-gray-800/50 transition-colors group"
                >
                  <span className="text-blue-400">├─</span>
                  <span className="text-gray-300 group-hover:text-white">{name}</span>
                  <span className="text-gray-600 ml-auto text-[10px]">{desc}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* API Dependencies */}
        <div className="bg-[#161b22] rounded-xl border border-gray-800 p-5 mb-8">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">🔌 API Dependencies</h3>
          <div className="grid grid-cols-5 gap-3">
            {[
              { name: 'Polygon.io', purpose: 'OHLCV + Quotes', icon: '📊' },
              { name: 'LunarCrush', purpose: 'Social Sentiment', icon: '🌙' },
              { name: 'Arkham', purpose: 'On-chain Flows', icon: '⛓️' },
              { name: 'OpenAI', purpose: 'LLM Regime Guard', icon: '🤖' },
              { name: 'Robinhood', purpose: 'Order Execution', icon: '🏦' },
            ].map(({ name, purpose, icon }) => (
              <div key={name} className="bg-[#1c2333] rounded-lg p-3 border border-gray-800 text-center">
                <div className="text-xl mb-1">{icon}</div>
                <div className="text-xs font-semibold text-white">{name}</div>
                <div className="text-[10px] text-gray-500">{purpose}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Start */}
        <div className="bg-[#161b22] rounded-xl border border-gray-800 p-5 mb-8">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">🚀 Quick Start</h3>
          <div className="bg-[#0d1117] rounded-lg p-4 font-mono text-xs text-gray-300 space-y-1">
            <div><span className="text-gray-500"># Clone and configure</span></div>
            <div><span className="text-green-400">$</span> cp .env.example .env</div>
            <div><span className="text-gray-500"># Edit .env with your API keys</span></div>
            <div className="mt-2"><span className="text-gray-500"># Run with Docker</span></div>
            <div><span className="text-green-400">$</span> docker-compose up -d</div>
            <div className="mt-2"><span className="text-gray-500"># Check health</span></div>
            <div><span className="text-green-400">$</span> curl http://localhost:8080/health</div>
            <div className="mt-2"><span className="text-gray-500"># Run tests</span></div>
            <div><span className="text-green-400">$</span> pytest tests/ -v</div>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex gap-3">
          <button
            onClick={() => onNavigate('architecture')}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors"
          >
            🏗️ View Architecture Diagram
          </button>
          <button
            onClick={() => onFileSelect('main.py', 'python')}
            className="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium transition-colors"
          >
            💻 View Source Code
          </button>
        </div>
      </div>
    </div>
  );
}
