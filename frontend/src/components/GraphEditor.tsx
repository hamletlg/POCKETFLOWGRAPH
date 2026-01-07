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
import { saveWorkflow, loadWorkflow, listWorkflows, runWorkflow, exportWorkflow } from '../api/client';
import type { NodeMetadata } from '../api/client';
import { MenuBar } from './MenuBar';
import { fetchWorkspaces, fetchActiveWorkspace, setActiveWorkspace } from '../api/workspace';

interface GraphEditorProps {
    availableNodes: NodeMetadata[];
    onSwitchToExecution?: (workflowName: string | null) => void;
}

const initialNodes: Node[] = [
    {
        id: '1',
        type: 'custom',
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


const GraphEditorContent: React.FC<GraphEditorProps> = ({ availableNodes, onSwitchToExecution }) => {
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

    // Workspace State
    const [workspaces, setWorkspaces] = useState<string[]>([]);
    const [activeWorkspace, setActiveWorkspaceState] = useState<string>("default");
    const [availableWorkflows, setAvailableWorkflows] = useState<string[]>([]);

    useEffect(() => {
        loadWorkspaceData();
    }, []);

    const loadWorkspaceData = async () => {
        try {
            const wsList = await fetchWorkspaces();
            setWorkspaces(wsList);
            const active = await fetchActiveWorkspace();
            setActiveWorkspaceState(active);
            refreshWorkflows();
        } catch (e) {
            console.error("Failed to load workspaces", e);
        }
    };

    const refreshWorkflows = async () => {
        try {
            const wfs = await listWorkflows();
            setAvailableWorkflows(wfs);
        } catch (e) {
            console.error("Failed to list workflows", e);
        }
    };

    const handleSwitchWorkspace = async (name: string) => {
        try {
            await setActiveWorkspace(name);
            setActiveWorkspaceState(name);
            // Refresh workflows for new workspace
            refreshWorkflows();
            // Optionally clear editor
            if (confirm("Switching workspace. Clear current editor?")) {
                resetWorkflow();
            }
        } catch (e) {
            alert("Failed to switch workspace: " + e);
        }
    };

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
                    // alert("Workflow Execution Completed!"); // Removed annoying alert
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
        if (executingNodes.size === 0) return;
        setNodes((nds) =>
            nds.map((node) => {
                const isExecuting = executingNodes.has(node.id);
                const currentBorder = node.style?.border;
                const newBorder = isExecuting ? '2px solid #3b82f6' : '1px solid #777';

                if (currentBorder === newBorder) return node;

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
            onNodesChangeFromHook(changes);
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
                    params: {},
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

        try {
            const result = await runWorkflow(workflow);
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

    // Sidebar & Properties Logic
    const [sidebarWidth, setSidebarWidth] = useState(260);
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [isResizing, setIsResizing] = useState(false);
    const [propertiesPanelWidth, setPropertiesPanelWidth] = useState(320);
    const [isPropertiesOpen, setIsPropertiesOpen] = useState(true);
    const [isResizingProperties, setIsResizingProperties] = useState(false);

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

    // --- MENU BAR HANDLERS ---

    const resetWorkflow = () => {
        setNodes(initialNodes);
        setEdges([]);
        setCurrentWorkflowName(null);
        setIsDirty(false);
    };

    const handleNewProject = () => {
        if (isDirty) {
            if (confirm("You have unsaved changes. Discard?")) {
                resetWorkflow();
            }
        } else {
            resetWorkflow();
        }
    };

    const handleLoadProject = async (name: string) => {
        try {
            const wf = await loadWorkflow(name);
            const newNodes = wf.nodes.map((n: any) => ({
                id: n.id,
                type: n.type === 'note' ? 'note' : (n.type === 'group' ? 'group' : 'custom'),
                position: n.position,
                data: {
                    label: n.label,
                    type: n.type,
                    params: n.data,
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
            setIsDirty(false);
        } catch (e) {
            alert("Error loading: " + e);
        }
    };

    const handleSaveProject = async () => {
        if (!currentWorkflowName) {
            handleSaveAsProject(prompt("Enter project name:") || "");
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

        try {
            await saveWorkflow(currentWorkflowName, workflow);
            refreshWorkflows();
            setIsDirty(false);
            alert("Saved!");
        } catch (e) {
            alert("Error saving: " + e);
        }
    };

    const handleSaveAsProject = async (name: string) => {
        if (!name) return;

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

        try {
            await saveWorkflow(name, workflow);
            setCurrentWorkflowName(name);
            refreshWorkflows();
            setIsDirty(false);
            alert("Saved as " + name);
        } catch (e) {
            alert("Error saving: " + e);
        }
    };

    const handleCloseProject = () => {
        if (isDirty) {
            if (!confirm("You have unsaved changes. Close anyway?")) return;
        }
        resetWorkflow();
    };

    // Export Logic
    const [isExportModalOpen, setIsExportModalOpen] = useState(false);
    const [exportName, setExportName] = useState("");

    const handleExportClick = () => {
        setExportName(currentWorkflowName || "workflow");
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
        <div className="flex flex-col h-screen w-screen overflow-hidden">

            {/* MENU BAR */}
            <MenuBar
                currentWorkflowName={currentWorkflowName}
                isDirty={isDirty}
                workspaces={workspaces}
                activeWorkspace={activeWorkspace}
                onSwitchWorkspace={handleSwitchWorkspace}
                onRefreshWorkspaces={loadWorkspaceData}
                onNewProject={handleNewProject}
                onLoadProject={handleLoadProject}
                onSaveProject={handleSaveProject}
                onSaveAsProject={handleSaveAsProject}
                onCloseProject={handleCloseProject}
                availableWorkflows={availableWorkflows}
                onRefreshWorkflows={refreshWorkflows}
            />

            {/* MAIN CONTENT */}
            <div className="flex flex-1 relative overflow-hidden">

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

                {/* Export Modal */}
                {isExportModalOpen && (
                    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={(e) => e.stopPropagation()}>
                        <div className="bg-white p-6 rounded-2xl shadow-xl w-96 transform transition-all scale-100 opacity-100">
                            <h3 className="text-lg font-bold text-gray-900 mb-4">Export to Python</h3>
                            <input
                                type="text"
                                className="w-full border border-gray-300 p-3 rounded-lg mb-6 focus:ring-2 focus:ring-blue-500 outline-none"
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

                {/* Sidebar */}
                <div
                    ref={sidebarRef}
                    className={`relative flex-shrink-0 bg-gray-50 border-r border-gray-200 transition-all duration-300 ease-in-out ${isSidebarOpen ? '' : 'w-0 overflow-hidden'}`}
                    style={{ width: isSidebarOpen ? sidebarWidth : 0 }}
                >
                    <div className="h-full overflow-hidden" style={{ width: sidebarWidth }}>
                        <Sidebar nodes={availableNodes} />
                    </div>

                    {/* Drag Handle */}
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

                {/* Sidebar Toggle */}
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

                {/* ReactFlow Area */}
                <div className="flex-1 h-full relative" ref={reactFlowWrapper}>
                    {/* Floating Toolbar (Right) */}
                    <div className="absolute top-4 right-4 z-10 flex gap-2">
                        {onSwitchToExecution && (
                            <button
                                onClick={() => onSwitchToExecution(currentWorkflowName)}
                                className="bg-purple-600 text-white px-4 py-2 rounded shadow hover:bg-purple-700 transition flex items-center gap-1"
                            >
                                ▶ Execution View
                            </button>
                        )}
                        <button
                            onClick={handleExportClick}
                            className="bg-gray-600 text-white px-4 py-2 rounded shadow hover:bg-gray-700 transition"
                        >
                            Export Py
                        </button>
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

                {/* Properties Panel Toggle */}
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

                {/* Properties Panel */}
                <div
                    ref={propertiesRef}
                    className={`relative flex-shrink-0 bg-white border-l border-gray-200 transition-all duration-300 ease-in-out ${isPropertiesOpen ? '' : 'w-0 overflow-hidden'}`}
                    style={{ width: isPropertiesOpen ? propertiesPanelWidth : 0 }}
                >
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
        </div>
    );
};
