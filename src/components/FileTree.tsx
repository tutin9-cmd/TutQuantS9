import { useState } from 'react';

interface FileTreeProps {
  onFileSelect: (path: string, language: string) => void;
  selectedPath: string;
}

interface TreeNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  language?: string;
  children?: TreeNode[];
}

const fileTree: TreeNode[] = [
  {
    name: 'robinhood_breakout_bot',
    path: '',
    type: 'directory',
    children: [
      { name: '.env.example', path: '.env.example', type: 'file', language: 'bash' },
      { name: '.gitignore', path: '.gitignore', type: 'file', language: 'text' },
      { name: 'Dockerfile', path: 'Dockerfile', type: 'file', language: 'dockerfile' },
      { name: 'docker-compose.yml', path: 'docker-compose.yml', type: 'file', language: 'yaml' },
      { name: 'requirements.txt', path: 'requirements.txt', type: 'file', language: 'text' },
      { name: 'config.py', path: 'config.py', type: 'file', language: 'python' },
      { name: 'main.py', path: 'main.py', type: 'file', language: 'python' },
      {
        name: 'src',
        path: 'src',
        type: 'directory',
        children: [
          { name: '__init__.py', path: 'src/__init__.py', type: 'file', language: 'python' },
          { name: 'data_fetcher.py', path: 'src/data_fetcher.py', type: 'file', language: 'python' },
          { name: 'technical_engine.py', path: 'src/technical_engine.py', type: 'file', language: 'python' },
          { name: 'llm_regime_guard.py', path: 'src/llm_regime_guard.py', type: 'file', language: 'python' },
          { name: 'risk_engine.py', path: 'src/risk_engine.py', type: 'file', language: 'python' },
          { name: 'execution_manager.py', path: 'src/execution_manager.py', type: 'file', language: 'python' },
        ],
      },
      {
        name: 'tests',
        path: 'tests',
        type: 'directory',
        children: [
          { name: '__init__.py', path: 'tests/__init__.py', type: 'file', language: 'python' },
          { name: 'test_technical_engine.py', path: 'tests/test_technical_engine.py', type: 'file', language: 'python' },
          { name: 'test_risk_engine.py', path: 'tests/test_risk_engine.py', type: 'file', language: 'python' },
        ],
      },
    ],
  },
];

function getFileIcon(name: string): string {
  if (name.endsWith('.py')) return '🐍';
  if (name.endsWith('.yml') || name.endsWith('.yaml')) return '⚙️';
  if (name === 'Dockerfile') return '🐳';
  if (name === '.env.example') return '🔐';
  if (name === '.gitignore') return '🚫';
  if (name.endsWith('.txt')) return '📄';
  return '📄';
}

function TreeItem({ node, depth, onFileSelect, selectedPath }: {
  node: TreeNode;
  depth: number;
  onFileSelect: (path: string, language: string) => void;
  selectedPath: string;
}) {
  const [expanded, setExpanded] = useState(depth < 2);

  if (node.type === 'directory') {
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-1.5 px-2 py-1 text-xs text-gray-300 hover:bg-gray-800/50 transition-colors"
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          <span className="text-[10px] text-gray-500 w-3">
            {expanded ? '▼' : '▶'}
          </span>
          <span>📁</span>
          <span className="font-medium">{node.name}</span>
        </button>
        {expanded && node.children && (
          <div>
            {node.children.map((child) => (
              <TreeItem
                key={child.path}
                node={child}
                depth={depth + 1}
                onFileSelect={onFileSelect}
                selectedPath={selectedPath}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  const isSelected = selectedPath === node.path;

  return (
    <button
      onClick={() => node.language && onFileSelect(node.path, node.language)}
      className={`w-full flex items-center gap-1.5 px-2 py-1 text-xs transition-colors ${
        isSelected
          ? 'bg-blue-900/30 text-blue-300 border-l-2 border-blue-500'
          : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'
      }`}
      style={{ paddingLeft: `${depth * 12 + 8}px` }}
    >
      <span className="w-3"></span>
      <span>{getFileIcon(node.name)}</span>
      <span className="truncate">{node.name}</span>
    </button>
  );
}

export function FileTree({ onFileSelect, selectedPath }: FileTreeProps) {
  return (
    <div className="py-2">
      <div className="px-3 py-2 border-b border-gray-800 mb-1">
        <h2 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
          Explorer
        </h2>
      </div>
      {fileTree.map((node) => (
        <TreeItem
          key={node.path || node.name}
          node={node}
          depth={0}
          onFileSelect={onFileSelect}
          selectedPath={selectedPath}
        />
      ))}
      
      <div className="px-3 py-3 mt-4 border-t border-gray-800">
        <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Project Stats
        </h3>
        <div className="space-y-1 text-[11px] text-gray-400">
          <div className="flex justify-between">
            <span>Files</span>
            <span className="text-gray-300">14</span>
          </div>
          <div className="flex justify-between">
            <span>Python LOC</span>
            <span className="text-gray-300">~2,800</span>
          </div>
          <div className="flex justify-between">
            <span>Test Coverage</span>
            <span className="text-green-400">Core modules</span>
          </div>
          <div className="flex justify-between">
            <span>Dependencies</span>
            <span className="text-gray-300">12 packages</span>
          </div>
        </div>
      </div>
    </div>
  );
}
