import { useEffect, useRef, useState } from 'react';
import Prism from 'prismjs';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-bash';
import 'prismjs/components/prism-yaml';
import 'prismjs/components/prism-docker';
import { FileData } from '../App';

interface CodeViewerProps {
  file: FileData;
  loading: boolean;
}

function getPrismLanguage(language: string): string {
  switch (language) {
    case 'python': return 'python';
    case 'bash': return 'bash';
    case 'yaml': return 'yaml';
    case 'dockerfile': return 'docker';
    default: return 'python';
  }
}

export function CodeViewer({ file, loading }: CodeViewerProps) {
  const codeRef = useRef<HTMLElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (codeRef.current && file.content) {
      Prism.highlightElement(codeRef.current);
    }
  }, [file]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(file.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const lines = file.content.split('\n');
  const lineCount = lines.length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex items-center gap-3 text-gray-400">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <span>Loading {file.name}...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* File header */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-gray-800">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-300 font-mono">{file.path}</span>
          <span className="px-1.5 py-0.5 rounded text-[10px] bg-gray-800 text-gray-400">
            {lineCount} lines
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
        >
          {copied ? (
            <>
              <span className="text-green-400">✓</span>
              <span className="text-green-400">Copied!</span>
            </>
          ) : (
            <>
              <span>📋</span>
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code content */}
      <div className="flex-1 overflow-auto bg-[#0d1117]">
        <div className="flex min-h-full">
          {/* Line numbers */}
          <div className="flex-shrink-0 py-4 px-2 text-right select-none border-r border-gray-800/50 bg-[#0d1117]">
            {lines.map((_, i) => (
              <div key={i} className="text-[11px] leading-[1.5rem] text-gray-600 font-mono px-2">
                {i + 1}
              </div>
            ))}
          </div>

          {/* Code */}
          <div className="flex-1 overflow-x-auto py-4 px-4">
            <pre className="text-[12px] leading-[1.5rem] font-mono">
              <code ref={codeRef} className={`language-${getPrismLanguage(file.language)}`}>
                {file.content}
              </code>
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
