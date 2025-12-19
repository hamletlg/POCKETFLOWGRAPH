import React, { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import ReactFlow, {
    addEdge,
    useNodesState,
    useEdgesState,
    Controls,
    Background,
    updateEdge,
} from 'reactflow';
import type { Connection, Edge, Node, NodeChange } from 'reactflow';
import 'reactflow/dist/style.css';
import { Sidebar } from './Sidebar';
import { PropertiesPanel } from './PropertiesPanel';
import CustomNode from './CustomNode';
import NoteNode from './NoteNode';
import ButtonEdge from './ButtonEdge';
import { HumanInputModal } from './HumanInputModal';
import { saveWorkflow, loadWorkflow, listWorkflows, runWorkflow, deleteWorkflow, exportWorkflow } from '../api/client';
import type { NodeMetadata } from '../api/client';

const WorkflowList = ({ onLoad, refreshTrigger }: { onLoad: (name: string) => void, refreshTrigger: number }) => {
    const [workflows, setWorkflows] = useState<string[]>([]);

    // Refresh list helper
    const refresh = () => listWorkflows().then(setWorkflows).catch(console.error);

    useEffect(() => {
        refresh();
    }, [refreshTrigger]);

    // Delete Modal Logic;
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [workflowToDelete, setWorkflowToDelete] = useState<string | null>(null);

    const handleDeleteClick = (e: React.MouseEvent, name: string) => {
        e.stopPropagation();
        setWorkflowToDelete(name);
        setIsDeleteModalOpen(true);
    };

    const confirmDelete = async () => {
        if (!workflowToDelete) return;

        try {
            await deleteWorkflow(workflowToDelete);
            await refresh(); // Refresh the list after deletion
            setIsDeleteModalOpen(false);
            setWorkflowToDelete(null);
            // Optional: alert("Deleted " + workflowToDelete); 
        } catch (err) {
            alert("Failed to delete: " + err);
        }
    };

    return (
        <div className="max-h-60 overflow-y-auto">
            {/* Delete Confirmation Modal */}
            {isDeleteModalOpen && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={(e) => e.stopPropagation()}>
                    <div className="bg-white p-6 rounded-2xl shadow-xl w-80 transform transition-all scale-100 opacity-100">
                        <h3 className="text-lg font-bold text-gray-900 mb-2">Delete Workflow?</h3>
                        <p className="text-sm text-gray-600 mb-6">
                            Are you sure you want to delete <strong>{workflowToDelete}</strong>? This cannot be undone.
                        </p>
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={(e) => { e.stopPropagation(); setIsDeleteModalOpen(false); }}
                                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors font-medium text-sm"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={(e) => { e.stopPropagation(); confirmDelete(); }}
                                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium text-sm"
                            >
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {workflows.length === 0 && <div className="p-2 text-sm text-gray-500">No saved workflows</div>}
            {workflows.map(w => (
                <div
                    key={w}
                    className="flex items-center justify-between p-2 hover:bg-blue-50 cursor-pointer text-sm text-gray-700 border-b border-gray-100 last:border-0 group/item"
                    onClick={() => onLoad(w)}
                >
                    <span className="flex-1 truncate">{w}</span>
                    <button
                        onClick={(e) => handleDeleteClick(e, w)}
                        className="opacity-0 group-hover/item:opacity-100 text-red-500 hover:text-red-700 p-1 hover:bg-red-50 rounded transition-all"
                        title="Delete Workflow"
                    >
                        ✕
                    </button>
                </div>
            ))}
        </div>
    );
};

interface GraphEditorProps {
    availableNodes: NodeMetadata[];
}

const initialNodes: Node[] = [
    {
        id: '1',
        type: 'custom', // Use our custom node
        data: {
            label: 'Start Flow',
            type: 'start',
            outputs: ['default']
        },
        position: { x: 250, y: 5 },
    },
];

const getId = () => `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

export const GraphEditor: React.FC<GraphEditorProps> = (props) => {
    return <GraphEditorContent {...props} />;
};

// Moving Content content here to allow hooks
const GraphEditorContent: React.FC<GraphEditorProps> = ({ availableNodes }) => {
    const reactFlowWrapper = useRef<HTMLDivElement>(null);
    const [nodes, setNodes, onNodesChangeFromHook] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);
    const [executionStatus, setExecutionStatus] = useState<string | null>(null);
    const [executionResult, setExecutionResult] = useState<string | null>(null);
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
    const [isDirty, setIsDirty] = useState(false);
    const [currentWorkflowName, setCurrentWorkflowName] = useState<string | null>(null);
    const [humanInputRequest, setHumanInputRequest] = useState<any>(null);

    const nodeTypes = useMemo(() => ({
        custom: CustomNode,
        note: NoteNode
    }), []);

    const edgeTypes = useMemo(() => ({
        button: ButtonEdge,
    }), []);

    const defaultEdgeOptions = useMemo(() => ({
        type: 'button',
    }), []);

    // State for Execution Visualization
    const [executingNodes, setExecutingNodes] = useState<Set<string>>(new Set());

    // WebSocket Connection
    useEffect(() => {
        const ws = new WebSocket('ws://localhost:8000/api/ws');

        ws.onopen = () => {
            console.log("Connected to WebSocket");
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'node_start') {
                    setExecutingNodes(prev => new Set(prev).add(msg.payload.node_id));
                } else if (msg.type === 'node_end' || msg.type === 'node_error') {
                    setExecutingNodes(prev => {
                        const next = new Set(prev);
                        next.delete(msg.payload.node_id);
                        return next;
                    });
                } else if (msg.type === 'workflow_end') {
                    // Clear all
                    setExecutingNodes(new Set());
                    alert("Workflow Execution Completed!");
                } else if (msg.type === 'workflow_error') {
                    setExecutingNodes(new Set());
                    alert("Workflow Error: " + msg.payload);
                } else if (msg.type === 'USER_INPUT_REQUIRED') {
                    setHumanInputRequest(msg.payload);
                }
            } catch (e) {
                console.error("WS Error", e);
            }
        };

        return () => {
            ws.close();
        };
    }, []);

    // Update nodes styling based on execution
    useEffect(() => {
        if (executingNodes.size === 0) {
            // Optionally reset styles when nothing is executing
            // but usually we want them to stay as-is or clear.
            // Let's just avoid unnecessary setNodes calls.
            return;
        }
        setNodes((nds) =>
            nds.map((node) => {
                const isExecuting = executingNodes.has(node.id);
                const currentBorder = node.style?.border;
                const newBorder = isExecuting ? '2px solid #3b82f6' : '1px solid #777';

                if (currentBorder === newBorder) return node; // Optimization

                return {
                    ...node,
                    style: {
                        ...node.style,
                        border: newBorder,
                        boxShadow: isExecuting ? '0 0 10px #3b82f6' : 'none',
                        transition: 'all 0.3s ease'
                    },
                };
            })
        );
    }, [executingNodes, setNodes]);


    const onNodesChange = useCallback(
        (changes: NodeChange[]) => {
            setIsDirty(true);
            onNodesChangeFromHook(changes); // Call the original handler
        },
        [onNodesChangeFromHook]
    );

    const onConnect = useCallback(
        (params: Connection) => {
            setEdges((eds) => addEdge({ ...params, type: 'button' }, eds));
            setIsDirty(true);
        },
        [setEdges],
    );

    const onEdgeUpdate = useCallback(
        (oldEdge: Edge, newConnection: Connection) => {
            setEdges((els) => updateEdge(oldEdge, newConnection, els));
            setIsDirty(true);
        },
        [setEdges]
    );

    const onDragOver = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }, []);

    const onDrop = useCallback(
        (event: React.DragEvent) => {
            event.preventDefault();

            if (!reactFlowWrapper.current || !reactFlowInstance) {
                return;
            }

            const type = event.dataTransfer.getData('application/reactflow');

            if (typeof type === 'undefined' || !type) {
                return;
            }

            // Find full metadata
            const nodeMeta = availableNodes.find(n => n.type === type);

            const position = reactFlowInstance.screenToFlowPosition({
                x: event.clientX,
                y: event.clientY,
            });

            const newNode: Node = {
                id: getId(),
                type: type === 'note' ? 'note' : (type === 'group' ? 'group' : 'custom'),
                position,
                data: {
                    label: type === 'note' ? '' : type,
                    type: type,
                    inputs: nodeMeta?.inputs || [],
                    outputs: nodeMeta?.outputs || [],
                    params: {}, // Initialize params as empty object for values
                    onChange: type === 'note' ? (val: string) => {
                        setNodes((nds) => nds.map((n) => {
                            if (n.id === newNode.id) {
                                return { ...n, data: { ...n.data, label: val } };
                            }
                            return n;
                        }));
                        setIsDirty(true);
                    } : undefined
                },
                // Groups need specific styling
                style: type === 'group' ? { width: 400, height: 300, backgroundColor: 'rgba(243, 244, 246, 0.4)', borderRadius: '12px', border: '2px dashed #9ca3af' } : {},
            };

            setNodes((nds) => nds.concat(newNode));
            setIsDirty(true);
        },
        [reactFlowInstance, setNodes, availableNodes],
    );

    const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
        setSelectedNodeId(node.id);
    }, []);

    const onPaneClick = useCallback(() => {
        setSelectedNodeId(null);
    }, []);

    const updateNodeData = useCallback((id: string, newData: any) => {
        setNodes((nds) => nds.map((node) => {
            if (node.id === id) {
                return { ...node, data: newData };
            }
            return node;
        }));
        setIsDirty(true);
    }, [setNodes]);

    const deleteNode = useCallback((id: string) => {
        setNodes((nds) => nds.filter((node) => node.id !== id));
        setEdges((eds) => eds.filter((edge) => edge.source !== id && edge.target !== id));
        setSelectedNodeId(null);
        setIsDirty(true);
    }, [setNodes, setEdges]);

    const selectedNode = useMemo(() => {
        return nodes.find(n => n.id === selectedNodeId) || null;
    }, [nodes, selectedNodeId]);

    const handleRun = async () => {
        console.log("Handle Run Clicked");
        setExecutionStatus("Running...");
        setExecutionResult(null);

        const workflow = {
            nodes: nodes.map(n => ({
                id: n.id,
                type: n.data.type || 'start',
                label: n.data.label,
                position: n.position,
                data: n.data.params || {}
            })),
            edges: edges.map(e => ({
                source: e.source,
                target: e.target,
                sourceHandle: e.sourceHandle,
                targetHandle: e.targetHandle
            }))
        };

        // Debug Log
        console.log("Submitting Workflow:", JSON.stringify(workflow, null, 2));

        try {
            const result = await runWorkflow(workflow);
            console.log("Workflow Result:", result);
            setExecutionStatus("Completed");
            setExecutionResult(JSON.stringify(result, null, 2));
        } catch (error) {
            console.error("Workflow Error:", error);
            setExecutionStatus("Error");
            setExecutionResult(String(error));
        }
    };

    const startNode = nodes.find(n => n.data.type === 'start');
    const showOverlay = startNode?.data.params?.show_overlay !== false;

    const [sidebarWidth, setSidebarWidth] = useState(260);
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [isResizing, setIsResizing] = useState(false);
    const [propertiesPanelWidth, setPropertiesPanelWidth] = useState(320);
    const [isPropertiesOpen, setIsPropertiesOpen] = useState(true);
    const [isResizingProperties, setIsResizingProperties] = useState(false);

    // Sidebar Logic
    const sidebarRef = useRef<HTMLDivElement>(null);
    const startResizing = useCallback(() => setIsResizing(true), []);
    const stopResizing = useCallback(() => setIsResizing(false), []);

    const resize = useCallback(
        (mouseMoveEvent: MouseEvent) => {
            if (isResizing) {
                const newWidth = mouseMoveEvent.clientX;
                if (newWidth > 150 && newWidth < 600) {
                    setSidebarWidth(newWidth);
                }
            }
        },
        [isResizing]
    );

    useEffect(() => {
        if (isResizing) {
            window.addEventListener("mousemove", resize);
            window.addEventListener("mouseup", stopResizing);
        }
        return () => {
            window.removeEventListener("mousemove", resize);
            window.removeEventListener("mouseup", stopResizing);
        };
    }, [isResizing, resize, stopResizing]);

    const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

    // Properties Logic
    const propertiesRef = useRef<HTMLDivElement>(null);

    const startResizingProperties = useCallback(() => setIsResizingProperties(true), []);
    const stopResizingProperties = useCallback(() => setIsResizingProperties(false), []);

    const resizeProperties = useCallback(
        (mouseMoveEvent: MouseEvent) => {
            if (isResizingProperties) {
                const newWidth = window.innerWidth - mouseMoveEvent.clientX;
                if (newWidth > 200 && newWidth < 600) {
                    setPropertiesPanelWidth(newWidth);
                }
            }
        },
        [isResizingProperties]
    );

    useEffect(() => {
        if (isResizingProperties) {
            window.addEventListener("mousemove", resizeProperties);
            window.addEventListener("mouseup", stopResizingProperties);
        }
        return () => {
            window.removeEventListener("mousemove", resizeProperties);
            window.removeEventListener("mouseup", stopResizingProperties);
        };
    }, [isResizingProperties, resizeProperties, stopResizingProperties]);

    const toggleProperties = () => setIsPropertiesOpen(!isPropertiesOpen);

    // Save Modal Logic
    const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
    const [saveName, setSaveName] = useState("");
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    const saveInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (isSaveModalOpen && saveInputRef.current) {
            saveInputRef.current.focus();
        }
    }, [isSaveModalOpen]);

    const handleSaveConfirm = async () => {
        console.log("handleSaveConfirm triggered. Name:", saveName);
        if (!saveName) {
            alert("Please enter a name");
            return;
        }

        const workflow = {
            nodes: nodes.map(n => ({
                id: n.id,
                type: n.data.type || 'start',
                label: n.data.label,
                position: n.position,
                data: n.data.params || {}
            })),
            edges: edges.map(e => ({
                source: e.source,
                target: e.target,
                sourceHandle: e.sourceHandle,
                targetHandle: e.targetHandle
            }))
        };
        console.log("Workflow object created:", workflow);

        try {
            console.log("Calling saveWorkflow API...");
            await saveWorkflow(saveName, workflow);
            console.log("API call success");
            setCurrentWorkflowName(saveName);
            setIsSaveModalOpen(false);
            setSaveName(""); // Reset
            setRefreshTrigger(prev => prev + 1); // Trigger list refresh
            setIsDirty(false); // Reset dirty state
            alert("Saved successfully!");
        } catch (e) {
            console.error("Save error:", e);
            alert("Error saving: " + e);
        }
    };

    // New Workflow Logic
    const [isNewModalOpen, setIsNewModalOpen] = useState(false);

    const resetWorkflow = () => {
        setNodes(initialNodes);
        setEdges([]);
        setSaveName("");
        setCurrentWorkflowName(null);
        setIsDirty(false);
    };

    const handleNewClick = () => {
        if (isDirty) {
            setIsNewModalOpen(true);
        } else {
            resetWorkflow();
        }
    };

    const confirmNew = () => {
        resetWorkflow();
        setIsNewModalOpen(false);
    };

    // Export Logic
    const [isExportModalOpen, setIsExportModalOpen] = useState(false);
    const [exportName, setExportName] = useState("");

    const handleExportClick = () => {
        setExportName(saveName || "workflow");
        setIsExportModalOpen(true);
    };

    const confirmExport = async () => {
        try {
            const workflow = {
                nodes: nodes.map(n => ({
                    id: n.id,
                    type: n.data.type || 'start',
                    label: n.data.label,
                    position: n.position,
                    data: n.data.params || {}
                })),
                edges: edges.map(e => ({
                    source: e.source,
                    target: e.target,
                    sourceHandle: e.sourceHandle,
                    targetHandle: e.targetHandle
                }))
            };

            const blob = await exportWorkflow(workflow);
            const url = window.URL.createObjectURL(new Blob([blob]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `${exportName.endsWith('.py') ? exportName : exportName + '.py'}`);
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);

            setIsExportModalOpen(false);
        } catch (e) {
            alert("Export failed: " + e);
        }
    };

    return (
        <div className="flex h-screen w-screen overflow-hidden">
            {/* Human Input Modal */}
            {humanInputRequest && (
                <HumanInputModal
                    requestId={humanInputRequest.request_id}
                    prompt={humanInputRequest.prompt}
                    fields={humanInputRequest.fields}
                    contextData={humanInputRequest.data}
                    onClose={() => setHumanInputRequest(null)}
                />
            )}

            {/* New Workflow Confirmation Modal */}
            {isNewModalOpen && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={(e) => e.stopPropagation()}>
                    <div className="bg-white p-6 rounded-2xl shadow-xl w-80 transform transition-all scale-100 opacity-100">
                        <h3 className="text-lg font-bold text-gray-900 mb-2">Discard Changes?</h3>
                        <p className="text-sm text-gray-600 mb-6">
                            You have unsaved changes. Creating a new workflow will discard them.
                        </p>
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={(e) => { e.stopPropagation(); setIsNewModalOpen(false); }}
                                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors font-medium text-sm"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={(e) => { e.stopPropagation(); confirmNew(); }}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm"
                            >
                                Continue
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Export Modal */}
            {isExportModalOpen && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={(e) => e.stopPropagation()}>
                    <div className="bg-white p-6 rounded-2xl shadow-xl w-96 transform transition-all scale-100 opacity-100">
                        <h3 className="text-lg font-bold text-gray-900 mb-4">Export to Python</h3>
                        <p className="text-sm text-gray-600 mb-4">
                            Enter a filename for your Python script.
                        </p>
                        <input
                            type="text"
                            className="w-full border border-gray-300 p-3 rounded-lg mb-6 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                            placeholder="filename.py"
                            value={exportName}
                            onChange={e => setExportName(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && confirmExport()}
                            autoFocus
                        />
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={(e) => { e.stopPropagation(); setIsExportModalOpen(false); }}
                                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors font-medium text-sm"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={(e) => { e.stopPropagation(); confirmExport(); }}
                                className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 transition-colors font-medium text-sm"
                            >
                                Download
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Save Modal */}
            <div className={`absolute inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm transition-all duration-300 ease-out ${isSaveModalOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}>
                <div className={`bg-white p-6 rounded-2xl shadow-2xl w-96 transform transition-all duration-300 ease-out ${isSaveModalOpen ? 'scale-100 translate-y-0 opacity-100' : 'scale-90 translate-y-4 opacity-0'}`}>
                    <h2 className="text-xl font-bold mb-4 text-gray-800">Save Workflow</h2>
                    <input
                        ref={saveInputRef}
                        type="text"
                        className="w-full border border-gray-300 p-3 rounded-lg mb-6 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                        placeholder="Workflow Name (e.g. my-flow)"
                        value={saveName}
                        onChange={e => setSaveName(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSaveConfirm()}
                    />
                    <div className="flex justify-end gap-3">
                        <button
                            onClick={() => setIsSaveModalOpen(false)}
                            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors font-medium"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleSaveConfirm}
                            className="px-6 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg hover:shadow-lg hover:from-blue-700 hover:to-blue-800 transition-all font-medium"
                        >
                            Save
                        </button>
                    </div>
                </div>
            </div>

            {/* Resizable Sidebar Wrapper */}
            <div
                ref={sidebarRef}
                className={`relative flex-shrink-0 bg-gray-50 border-r border-gray-200 transition-all duration-300 ease-in-out ${isSidebarOpen ? '' : 'w-0 overflow-hidden'}`}
                style={{ width: isSidebarOpen ? sidebarWidth : 0 }}
            >
                <div className="h-full overflow-hidden" style={{ width: sidebarWidth }}>
                    <Sidebar nodes={availableNodes} />
                </div>

                {/* Drag Handle (Sidebar) */}
                {isSidebarOpen && (
                    <div
                        className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-400 z-50 group transition-colors"
                        onMouseDown={startResizing}
                    >
                        <div className="absolute right-0 top-1/2 -translate-y-1/2 w-4 h-8 bg-gray-200 rounded-l flex items-center justify-center cursor-pointer hover:bg-blue-400 text-gray-500 hover:text-white shadow-md -mr-1"
                            onClick={(e) => { e.stopPropagation(); toggleSidebar(); }}>
                            ‹
                        </div>
                    </div>
                )}
            </div>

            {/* Collapsed Sidebar Toggle Button */}
            {!isSidebarOpen && (
                <div className="absolute left-0 top-1/2 z-50">
                    <button
                        onClick={toggleSidebar}
                        className="bg-white border border-gray-300 shadow-md p-1 rounded-r text-gray-600 hover:text-blue-600 hover:bg-gray-50"
                    >
                        ›
                    </button>
                </div>
            )}

            {/* Main Canvas Area */}
            <div className="flex-1 h-full relative" ref={reactFlowWrapper}>
                {/* Workflow Name Header */}
                <div className="absolute top-4 left-4 z-10 flex items-center gap-3">
                    <div className="bg-white/80 backdrop-blur px-4 py-2 rounded-xl shadow-sm border border-gray-200 flex items-center gap-2">
                        <span className="text-gray-400 font-medium">Workflow:</span>
                        <span className="text-gray-800 font-bold">
                            {currentWorkflowName || 'Untitled Workflow'}
                        </span>
                        {isDirty && (
                            <span className="flex h-2 w-2 rounded-full bg-blue-500 animate-pulse" title="Unsaved changes"></span>
                        )}
                    </div>
                </div>

                <div className="absolute top-4 right-4 z-10 flex gap-2">
                    <button
                        onClick={handleNewClick}
                        className="bg-purple-600 text-white px-4 py-2 rounded shadow hover:bg-purple-700 transition"
                    >
                        New
                    </button>
                    <button
                        onClick={handleExportClick}
                        className="bg-gray-600 text-white px-4 py-2 rounded shadow hover:bg-gray-700 transition"
                    >
                        Export Py
                    </button>
                    <button
                        onClick={() => setIsSaveModalOpen(true)}
                        className="bg-green-600 text-white px-4 py-2 rounded shadow hover:bg-green-700 transition"
                    >
                        Save
                    </button>

                    <div className="relative group">
                        <button
                            className="bg-yellow-600 text-white px-4 py-2 rounded shadow hover:bg-yellow-700 transition"
                        >
                            Load
                        </button>
                        <div className="absolute right-0 mt-0 w-48 bg-white rounded shadow-xl hidden group-hover:block border border-gray-200 overflow-hidden z-50">
                            <WorkflowList refreshTrigger={refreshTrigger} onLoad={async (name) => {
                                try {
                                    const wf = await loadWorkflow(name);
                                    // Transform back to ReactFlow format
                                    const newNodes = wf.nodes.map((n: any) => ({
                                        id: n.id,
                                        type: n.type === 'note' ? 'note' : (n.type === 'group' ? 'group' : 'custom'),
                                        position: n.position,
                                        data: {
                                            label: n.label,
                                            type: n.type,
                                            params: n.data,
                                            // We need to re-fetch metadata or store it? 
                                            // ideally we persist it, but for now let's hope it maps back
                                            inputs: availableNodes.find(x => x.type === n.type)?.inputs || [],
                                            outputs: availableNodes.find(x => x.type === n.type)?.outputs || [],
                                            onChange: n.type === 'note' ? (val: string) => {
                                                setNodes((nds) => nds.map((node) => {
                                                    if (node.id === n.id) {
                                                        return { ...node, data: { ...node.data, label: val } };
                                                    }
                                                    return node;
                                                }));
                                                setIsDirty(true);
                                            } : undefined
                                        },
                                        style: n.style || {}
                                    }));

                                    const newEdges = wf.edges.map((e: any) => ({
                                        id: `e${e.source}-${e.target}`,
                                        source: e.source,
                                        target: e.target,
                                        sourceHandle: e.sourceHandle,
                                        targetHandle: e.targetHandle
                                    }));

                                    setNodes(newNodes);
                                    setEdges(newEdges);
                                    setCurrentWorkflowName(name);
                                    setIsDirty(false); // Reset dirty state on load
                                } catch (e) {
                                    alert("Error loading: " + e);
                                }
                            }} />
                        </div>
                    </div>

                    <button
                        onClick={handleRun}
                        className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition"
                        disabled={executionStatus === "Running..."}
                    >
                        {executionStatus === "Running..." ? "Running..." : "Run"}
                    </button>
                </div>

                {/* Conditional Result Overlay */}
                {executionResult && showOverlay && (
                    <div className="absolute bottom-4 left-4 right-4 z-10 bg-white p-4 border rounded shadow-lg max-h-48 overflow-auto">
                        <h3 className="font-bold text-sm mb-2">Execution Result:</h3>
                        <pre className="text-xs text-gray-800 whitespace-pre-wrap">{executionResult}</pre>
                        <button
                            onClick={() => setExecutionResult(null)}
                            className="absolute top-2 right-2 text-gray-500 hover:text-gray-700"
                        >
                            x
                        </button>
                    </div>
                )}

                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={(changes) => {
                        onNodesChange(changes);
                        // Only mark dirty if there are actual changes
                        if (changes.length > 0) setIsDirty(true);
                    }}
                    onEdgesChange={(changes) => {
                        onEdgesChange(changes);
                        if (changes.length > 0) setIsDirty(true);
                    }}
                    onConnect={onConnect}
                    onEdgeUpdate={onEdgeUpdate}
                    nodeTypes={nodeTypes}
                    edgeTypes={edgeTypes}
                    defaultEdgeOptions={defaultEdgeOptions}
                    onInit={setReactFlowInstance}
                    onDrop={onDrop}
                    onDragOver={onDragOver}
                    onNodeClick={onNodeClick}
                    onPaneClick={onPaneClick}
                    fitView
                    snapToGrid
                    snapGrid={[15, 15]}
                >
                    <Controls />
                    <Background color="#aaa" gap={16} />
                </ReactFlow>
            </div>

            {/* Collapsed Properties Toggle Button */}
            {!isPropertiesOpen && (
                <div className="absolute right-0 top-1/2 z-50">
                    <button
                        onClick={toggleProperties}
                        className="bg-white border border-gray-300 shadow-md p-1 rounded-l text-gray-600 hover:text-blue-600 hover:bg-gray-50"
                    >
                        ‹
                    </button>
                </div>
            )}

            {/* Resizable Properties Panel Wrapper */}
            <div
                ref={propertiesRef}
                className={`relative flex-shrink-0 bg-white border-l border-gray-200 transition-all duration-300 ease-in-out ${isPropertiesOpen ? '' : 'w-0 overflow-hidden'}`}
                style={{ width: isPropertiesOpen ? propertiesPanelWidth : 0 }}
            >
                {/* Drag Handle (Properties) - On Left Side */}
                {isPropertiesOpen && (
                    <div
                        className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-400 z-50 group transition-colors"
                        onMouseDown={startResizingProperties}
                    >
                        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-4 h-8 bg-gray-200 rounded-r flex items-center justify-center cursor-pointer hover:bg-blue-400 text-gray-500 hover:text-white shadow-md -ml-1"
                            onClick={(e) => { e.stopPropagation(); toggleProperties(); }}>
                            ›
                        </div>
                    </div>
                )}

                <div className="h-full overflow-hidden" style={{ width: propertiesPanelWidth }}>
                    <PropertiesPanel
                        selectedNode={selectedNode}
                        onUpdateNodeData={updateNodeData}
                        availableNodes={availableNodes}
                        onDeleteNode={deleteNode}
                    />
                </div>
            </div>
        </div>
    );
};
