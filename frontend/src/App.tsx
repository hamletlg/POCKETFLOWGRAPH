import { useEffect, useState } from 'react';
import './index.css';
import { GraphEditor } from './components/GraphEditor';
import { ExecutionView } from './components/ExecutionView';
import { fetchNodes } from './api/client';
import type { NodeMetadata } from './api/client';

import { ReactFlowProvider } from 'reactflow';
import 'reactflow/dist/style.css';

type ViewMode = 'editor' | 'execution';

function App() {
  const [nodes, setNodes] = useState<NodeMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentView, setCurrentView] = useState<ViewMode>('editor');
  const [currentWorkflowName, setCurrentWorkflowName] = useState<string | null>(null);

  useEffect(() => {
    const loadNodes = async () => {
      try {
        const data = await fetchNodes();
        setNodes(data);
      } catch (error) {
        console.error("Failed to fetch nodes:", error);
      } finally {
        setLoading(false);
      }
    };
    loadNodes();
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  return (
    <div className="h-screen w-screen bg-white">
      {/* Keep both views mounted to preserve state, use CSS to show/hide */}
      <div className={currentView === 'editor' ? 'h-full w-full' : 'hidden'}>
        <ReactFlowProvider>
          <GraphEditor
            availableNodes={nodes}
            onSwitchToExecution={(workflowName) => {
              setCurrentWorkflowName(workflowName);
              setCurrentView('execution');
            }}
          />
        </ReactFlowProvider>
      </div>
      <div className={currentView === 'execution' ? 'h-full w-full' : 'hidden'}>
        <ExecutionView
          onSwitchToEditor={() => setCurrentView('editor')}
          currentWorkflowName={currentWorkflowName}
        />
      </div>
    </div>
  );
}

export default App;
