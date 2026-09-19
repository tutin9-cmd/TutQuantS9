export function ArchitectureDiagram() {
  return (
    <div className="h-full overflow-auto p-6 bg-[#0d1117]">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-xl font-bold text-white mb-6">System Architecture</h2>
        
        {/* Main Pipeline */}
        <div className="bg-[#161b22] rounded-xl border border-gray-800 p-6 mb-6">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
            Scan Cycle Pipeline (5-minute interval)
          </h3>
          
          <div className="grid grid-cols-5 gap-3 items-center">
            {/* Step 1 */}
            <div className="bg-[#1c2333] rounded-lg p-4 border border-blue-900/50">
              <div className="text-2xl mb-2">📊</div>
              <h4 className="text-sm font-semibold text-blue-300 mb-1">Data Fetcher</h4>
              <p className="text-[11px] text-gray-400">Polygon.io, LunarCrush, Arkham</p>
              <div className="mt-2 text-[10px] text-gray-500">
                OHLCV • Quotes • Sentiment • On-chain
              </div>
            </div>

            <div className="text-gray-600 text-center text-xl">→</div>

            {/* Step 2 */}
            <div className="bg-[#1c2333] rounded-lg p-4 border border-purple-900/50">
              <div className="text-2xl mb-2">📈</div>
              <h4 className="text-sm font-semibold text-purple-300 mb-1">Technical Engine</h4>
              <p className="text-[11px] text-gray-400">BB, ATR, Donchian, Volume</p>
              <div className="mt-2 text-[10px] text-gray-500">
                Squeeze detection • Breakout signals
              </div>
            </div>

            <div className="text-gray-600 text-center text-xl">→</div>

            {/* Step 3 */}
            <div className="bg-[#1c2333] rounded-lg p-4 border border-amber-900/50">
              <div className="text-2xl mb-2">🤖</div>
              <h4 className="text-sm font-semibold text-amber-300 mb-1">LLM Regime Guard</h4>
              <p className="text-[11px] text-gray-400">GPT-4o-mini Veto Only</p>
              <div className="mt-2 text-[10px] text-gray-500">
                Strict JSON • Fail-closed parsing
              </div>
            </div>
          </div>

          <div className="flex justify-center my-3">
            <div className="text-gray-600 text-xl">↓</div>
          </div>

          <div className="grid grid-cols-3 gap-3 items-center max-w-3xl mx-auto">
            {/* Step 4 */}
            <div className="bg-[#1c2333] rounded-lg p-4 border border-red-900/50">
              <div className="text-2xl mb-2">🛡️</div>
              <h4 className="text-sm font-semibold text-red-300 mb-1">Risk Engine</h4>
              <p className="text-[11px] text-gray-400">Deterministic Hard Limits</p>
              <div className="mt-2 text-[10px] text-gray-500">
                Position sizing • Velocity • Blackout
              </div>
            </div>

            <div className="text-gray-600 text-center text-xl">→</div>

            {/* Step 5 */}
            <div className="bg-[#1c2333] rounded-lg p-4 border border-green-900/50">
              <div className="text-2xl mb-2">⚡</div>
              <h4 className="text-sm font-semibold text-green-300 mb-1">Execution Manager</h4>
              <p className="text-[11px] text-gray-400">Robinhood MCP</p>
              <div className="mt-2 text-[10px] text-gray-500">
                Idempotency • Order tracking • Audit
              </div>
            </div>
          </div>
        </div>

        {/* Risk Controls */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-[#161b22] rounded-xl border border-gray-800 p-5">
            <h3 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
              <span>🛡️</span> Deterministic Risk Controls
            </h3>
            <div className="space-y-2 text-xs">
              {[
                ['Max Position Size', '$50.00 (20% of account)'],
                ['Max Concurrent', '3 positions ($150 deployed)'],
                ['Cash Reserve', '$100 (40% of account)'],
                ['Trade Velocity', '2 per asset per 24h rolling'],
                ['Weekend Blackout', 'Fri 8PM - Sun 8PM EST'],
                ['Max Spread', '0.75% bid-ask'],
                ['Min Risk/Reward', '1.5:1'],
                ['Stop-Loss', '2x ATR(14) below entry'],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between items-center py-1 border-b border-gray-800/50">
                  <span className="text-gray-400">{label}</span>
                  <span className="text-gray-200 font-mono">{value}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-[#161b22] rounded-xl border border-gray-800 p-5">
            <h3 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
              <span>🚪</span> Exit Logic
            </h3>
            <div className="space-y-3">
              <div className="bg-[#1c2333] rounded-lg p-3 border border-gray-800">
                <div className="text-xs font-semibold text-red-300 mb-1">Stop-Loss</div>
                <p className="text-[11px] text-gray-400">2x ATR(14) below entry price. Full position liquidation.</p>
              </div>
              <div className="bg-[#1c2333] rounded-lg p-3 border border-gray-800">
                <div className="text-xs font-semibold text-green-300 mb-1">Take-Profit (Partial)</div>
                <p className="text-[11px] text-gray-400">Sell 50% at +8% profit. Remaining 50% trails.</p>
              </div>
              <div className="bg-[#1c2333] rounded-lg p-3 border border-gray-800">
                <div className="text-xs font-semibold text-blue-300 mb-1">Trailing Stop</div>
                <p className="text-[11px] text-gray-400">Remaining 50% trails behind 20-period SMA.</p>
              </div>
              <div className="bg-[#1c2333] rounded-lg p-3 border border-gray-800">
                <div className="text-xs font-semibold text-yellow-300 mb-1">Time Stop</div>
                <p className="text-[11px] text-gray-400">Liquidate at market if flat/negative after 48 hours.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Fail-Closed Design */}
        <div className="bg-[#161b22] rounded-xl border border-gray-800 p-5">
          <h3 className="text-sm font-semibold text-orange-400 mb-3 flex items-center gap-2">
            <span>⚠️</span> Fail-Closed Design Principles
          </h3>
          <div className="grid grid-cols-2 gap-3 text-xs">
            {[
              { trigger: 'API timeout/error', action: 'Skip asset, continue scan' },
              { trigger: 'LLM parse failure', action: 'Veto trade immediately' },
              { trigger: 'MCP connection error', action: 'Abort execution' },
              { trigger: 'Missing market data', action: 'Skip entire scan cycle' },
              { trigger: 'Ambiguous state', action: 'Never trade blind' },
              { trigger: 'Config missing', action: 'Refuse to start' },
            ].map(({ trigger, action }) => (
              <div key={trigger} className="flex items-center gap-2 bg-[#1c2333] rounded p-2 border border-gray-800">
                <span className="text-red-400">✗</span>
                <span className="text-gray-400">{trigger}</span>
                <span className="text-gray-600">→</span>
                <span className="text-green-400">{action}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
