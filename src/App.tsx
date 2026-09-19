import { useState, useEffect, useCallback } from 'react';
import { FileTree } from './components/FileTree';
import { CodeViewer } from './components/CodeViewer';
import { Header } from './components/Header';
import { ArchitectureDiagram } from './components/ArchitectureDiagram';
import { StrategyOverview } from './components/StrategyOverview';

export type ViewMode = 'code' | 'architecture' | 'overview';

export interface FileData {
  name: string;
  path: string;
  language: string;
  content: string;
}

function App() {
  const [selectedFile, setSelectedFile] = useState<FileData | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('overview');
  const [loading, setLoading] = useState(false);

  const fetchFile = useCallback(async (path: string, language: string) => {
    setLoading(true);
    try {
      const response = await fetch(`/code/${path}`);
      if (!response.ok) throw new Error(`Failed to fetch ${path}`);
      const content = await response.text();
      setSelectedFile({ name: path.split('/').pop() || path, path, language, content });
      setViewMode('code');
    } catch (err) {
      console.error('Failed to fetch file:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Default to overview on load
  }, []);

  return (
    <div className="h-screen flex flex-col bg-[#0d1117] text-gray-200 overflow-hidden">
      <Header viewMode={viewMode} setViewMode={setViewMode} />
      
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside className="w-72 border-r border-gray-800 overflow-y-auto bg-[#0d1117] flex-shrink-0">
          <FileTree onFileSelect={fetchFile} selectedPath={selectedFile?.path || ''} />
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-hidden">
          {viewMode === 'overview' && <StrategyOverview onNavigate={setViewMode} onFileSelect={fetchFile} />}
          {viewMode === 'architecture' && <ArchitectureDiagram />}
          {viewMode === 'code' && selectedFile && (
            <CodeViewer file={selectedFile} loading={loading} />
          )}
          {viewMode === 'code' && !selectedFile && (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <div className="text-6xl mb-4">📂</div>
                <p className="text-lg">Select a file from the sidebar to view its source code</p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
