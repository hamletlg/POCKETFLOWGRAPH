import { useEffect, useState } from 'react';
import './index.css';
import { GraphEditor } from './components/GraphEditor';
import { fetchNodes } from './api/client';
import type { NodeMetadata } from './api/client';

function App() {
  const [nodes, setNodes] = useState<NodeMetadata[]>([]);
  const [loading, setLoading] = useState(true);

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
      <GraphEditor availableNodes={nodes} />
    </div>
  );
}

export default App;
