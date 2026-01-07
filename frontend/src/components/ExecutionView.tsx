import React, { useState, useEffect, useCallback } from 'react';

// Types
export interface ExecutionEvent {
    id: string;
    type: 'workflow_start' | 'node_start' | 'node_end' | 'node_error' | 'llm_call' | 'llm_response' | 'user_input_required' | 'user_input_received' | 'workflow_end' | 'workflow_error' | 'state_update';
    timestamp: Date;
    nodeId?: string;
    nodeName?: string;
    payload: any;
}

interface ExecutionViewProps {
    onSwitchToEditor: () => void;
    currentWorkflowName: string | null;
}

// Sub-components
const ExecutionLog: React.FC<{
    events: ExecutionEvent[];
    selectedEventId: string | null;
    onSelectEvent: (id: string) => void;
    filter: string;
    onFilterChange: (filter: string) => void;
}> = ({ events, selectedEventId, onSelectEvent, filter, onFilterChange }) => {

    const getEventIcon = (type: string) => {
        switch (type) {
            case 'workflow_start': return '🚀';
            case 'node_start': return '🟢';
            case 'node_end': return '✅';
            case 'node_error': return '🔴';
            case 'llm_call': return '🤖';
            case 'llm_response': return '💬';
            case 'user_input_required': return '👤';
            case 'user_input_received': return '👍';
            case 'workflow_end': return '🏁';
            case 'workflow_error': return '❌';
            case 'state_update': return '📊';
            default: return '•';
        }
    };

    const getEventColor = (type: string) => {
        switch (type) {
            case 'node_error':
            case 'workflow_error':
                return 'bg-red-50 border-red-200 hover:bg-red-100';
            case 'user_input_required':
                return 'bg-amber-50 border-amber-200 hover:bg-amber-100';
            case 'llm_call':
            case 'llm_response':
                return 'bg-purple-50 border-purple-200 hover:bg-purple-100';
            default:
                return 'bg-white border-gray-200 hover:bg-gray-50';
        }
    };

    const filteredEvents = filter === 'all'
        ? events
        : events.filter(e => e.type === filter || (filter === 'errors' && (e.type === 'node_error' || e.type === 'workflow_error')));

    return (
        <div className="h-full flex flex-col bg-gray-50">
            <div className="p-3 border-b bg-white">
                <h2 className="font-bold text-gray-800 mb-2">Execution Log</h2>
                <select
                    value={filter}
                    onChange={(e) => onFilterChange(e.target.value)}
                    className="w-full text-sm border border-gray-300 rounded px-2 py-1"
                >
                    <option value="all">All Events</option>
                    <option value="errors">Errors Only</option>
                    <option value="node_start">Node Start</option>
                    <option value="node_end">Node End</option>
                    <option value="llm_call">LLM Calls</option>
                    <option value="llm_response">LLM Responses</option>
                    <option value="user_input_required">Human Input</option>
                </select>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {filteredEvents.length === 0 ? (
                    <div className="text-center text-gray-400 text-sm py-8">
                        No events yet. Run a workflow to see activity.
                    </div>
                ) : (
                    filteredEvents.map((event) => (
                        <div
                            key={event.id}
                            onClick={() => onSelectEvent(event.id)}
                            className={`p-2 rounded border cursor-pointer transition-all ${getEventColor(event.type)} ${selectedEventId === event.id ? 'ring-2 ring-blue-500' : ''}`}
                        >
                            <div className="flex items-center gap-2">
                                <span className="text-lg">{getEventIcon(event.type)}</span>
                                <div className="flex-1 min-w-0">
                                    <div className="text-xs font-medium text-gray-800 truncate">
                                        {event.nodeName || event.type.replace(/_/g, ' ')}
                                    </div>
                                    <div className="text-[10px] text-gray-500">
                                        {event.timestamp.toLocaleTimeString()}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

const MessageInspector: React.FC<{
    event: ExecutionEvent | null;
    onHumanResponse?: (requestId: string, data: any) => void;
}> = ({ event, onHumanResponse: _onHumanResponse }) => {

    if (!event) {
        return (
            <div className="h-full flex items-center justify-center bg-white">
                <div className="text-center text-gray-400">
                    <div className="text-4xl mb-2">📋</div>
                    <p>Select an event to view details</p>
                </div>
            </div>
        );
    }

    const renderPayload = () => {
        if (event.type === 'llm_response' && event.payload?.response) {
            return (
                <div className="space-y-4">
                    <div>
                        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Response</h4>
                        <div className="bg-gray-50 p-3 rounded-lg border text-sm whitespace-pre-wrap">
                            {event.payload.response}
                        </div>
                    </div>
                    {event.payload.model && (
                        <div>
                            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Model</h4>
                            <div className="text-sm">{event.payload.model}</div>
                        </div>
                    )}
                    {event.payload.duration_ms && (
                        <div>
                            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Duration</h4>
                            <div className="text-sm">{event.payload.duration_ms}ms</div>
                        </div>
                    )}
                </div>
            );
        }

        if (event.type === 'llm_call' && event.payload?.prompt_preview) {
            return (
                <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Prompt Preview</h4>
                    <div className="bg-gray-50 p-3 rounded-lg border text-sm whitespace-pre-wrap max-h-96 overflow-auto">
                        {event.payload.prompt_preview}
                    </div>
                </div>
            );
        }

        if (event.type === 'node_error' || event.type === 'workflow_error') {
            return (
                <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                    <h4 className="text-sm font-semibold text-red-800 mb-2">Error</h4>
                    <pre className="text-sm text-red-700 whitespace-pre-wrap">
                        {typeof event.payload === 'string' ? event.payload : JSON.stringify(event.payload, null, 2)}
                    </pre>
                </div>
            );
        }

        if (event.type === 'user_input_required') {
            return (
                <div className="bg-amber-50 p-4 rounded-lg border border-amber-200">
                    <h4 className="text-sm font-semibold text-amber-800 mb-2">👤 Human Input Required</h4>
                    <p className="text-sm text-amber-700 mb-4">{event.payload?.prompt || 'Awaiting user input...'}</p>
                    {event.payload?.data && (
                        <div className="mb-4">
                            <h5 className="text-xs font-semibold text-amber-600 uppercase mb-1">Context</h5>
                            <pre className="bg-white p-2 rounded border text-xs overflow-auto max-h-40">
                                {typeof event.payload.data === 'object' ? JSON.stringify(event.payload.data, null, 2) : String(event.payload.data)}
                            </pre>
                        </div>
                    )}
                    <p className="text-xs text-amber-600 italic">Use the modal that appears to respond.</p>
                </div>
            );
        }

        // Default: show raw payload
        return (
            <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Payload</h4>
                <pre className="bg-gray-50 p-3 rounded-lg border text-xs overflow-auto max-h-96">
                    {typeof event.payload === 'object' ? JSON.stringify(event.payload, null, 2) : String(event.payload)}
                </pre>
            </div>
        );
    };

    return (
        <div className="h-full bg-white p-4 overflow-y-auto">
            <div className="mb-4 pb-4 border-b">
                <div className="flex items-center gap-2 mb-1">
                    <span className="text-2xl">
                        {event.type === 'workflow_start' ? '🚀' :
                            event.type === 'node_start' ? '🟢' :
                                event.type === 'node_end' ? '✅' :
                                    event.type === 'node_error' ? '🔴' :
                                        event.type === 'llm_call' ? '🤖' :
                                            event.type === 'llm_response' ? '💬' :
                                                event.type === 'user_input_required' ? '👤' :
                                                    event.type === 'workflow_end' ? '🏁' : '•'}
                    </span>
                    <h3 className="font-bold text-lg text-gray-800">
                        {event.nodeName || event.type.replace(/_/g, ' ')}
                    </h3>
                </div>
                <div className="text-sm text-gray-500">
                    {event.timestamp.toLocaleString()} • {event.nodeId ? `ID: ${event.nodeId}` : event.type}
                </div>
            </div>

            {renderPayload()}
        </div>
    );
};

const StatePanel: React.FC<{
    sharedMemory: Record<string, any>;
    results: Record<string, any>;
}> = ({ sharedMemory, results }) => {

    const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
        memory: true,
        results: true,
    });

    const toggleSection = (section: string) => {
        setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
    };

    return (
        <div className="h-full bg-gray-50 overflow-y-auto">
            {/* Shared Memory */}
            <div className="border-b">
                <button
                    onClick={() => toggleSection('memory')}
                    className="w-full p-3 flex items-center justify-between bg-white hover:bg-gray-50 transition-colors"
                >
                    <span className="font-semibold text-gray-800">📦 Shared Memory</span>
                    <span className="text-gray-400">{expandedSections.memory ? '▼' : '▶'}</span>
                </button>
                {expandedSections.memory && (
                    <div className="p-3 bg-white">
                        {Object.keys(sharedMemory).length === 0 ? (
                            <p className="text-sm text-gray-400 italic">Empty</p>
                        ) : (
                            <pre className="text-xs bg-gray-50 p-2 rounded border overflow-auto max-h-48">
                                {JSON.stringify(sharedMemory, null, 2)}
                            </pre>
                        )}
                    </div>
                )}
            </div>

            {/* Results */}
            <div className="border-b">
                <button
                    onClick={() => toggleSection('results')}
                    className="w-full p-3 flex items-center justify-between bg-white hover:bg-gray-50 transition-colors"
                >
                    <span className="font-semibold text-gray-800">📊 Node Results</span>
                    <span className="text-gray-400">{expandedSections.results ? '▼' : '▶'}</span>
                </button>
                {expandedSections.results && (
                    <div className="p-3 bg-white">
                        {Object.keys(results).length === 0 ? (
                            <p className="text-sm text-gray-400 italic">No results yet</p>
                        ) : (
                            <div className="space-y-2">
                                {Object.entries(results).map(([key, value]) => (
                                    <div key={key} className="bg-gray-50 p-2 rounded border">
                                        <div className="text-xs font-semibold text-gray-600 mb-1">{key}</div>
                                        <pre className="text-xs overflow-auto max-h-24">
                                            {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                                        </pre>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

// Main Component
export const ExecutionView: React.FC<ExecutionViewProps> = ({ onSwitchToEditor, currentWorkflowName }) => {
    const [events, setEvents] = useState<ExecutionEvent[]>([]);
    const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
    const [filter, setFilter] = useState('all');
    const [sharedMemory, setSharedMemory] = useState<Record<string, any>>({});
    const [results, setResults] = useState<Record<string, any>>({});
    const [isRunning, setIsRunning] = useState(false);

    // WebSocket connection
    useEffect(() => {
        const ws = new WebSocket('ws://localhost:8000/api/ws');

        ws.onopen = () => {
            console.log("ExecutionView: Connected to WebSocket");
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                const newEvent: ExecutionEvent = {
                    id: `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                    type: msg.type,
                    timestamp: new Date(),
                    nodeId: msg.payload?.node_id,
                    nodeName: msg.payload?.node_name || msg.payload?.node_id,
                    payload: msg.payload,
                };

                setEvents(prev => [...prev, newEvent]);

                // Handle specific event types
                if (msg.type === 'workflow_start') {
                    setIsRunning(true);
                    setEvents([]); // Clear previous events on new run
                } else if (msg.type === 'workflow_end' || msg.type === 'workflow_error') {
                    setIsRunning(false);
                    // Update state from final results if available
                    if (msg.payload?.results) {
                        setResults(msg.payload.results);
                    }
                } else if (msg.type === 'state_update') {
                    if (msg.payload?.memory) setSharedMemory(msg.payload.memory);
                    if (msg.payload?.results) setResults(msg.payload.results);
                }
            } catch (e) {
                console.error("ExecutionView WS Error", e);
            }
        };

        return () => {
            ws.close();
        };
    }, []);

    const selectedEvent = events.find(e => e.id === selectedEventId) || null;

    const clearEvents = useCallback(() => {
        setEvents([]);
        setSelectedEventId(null);
        setSharedMemory({});
        setResults({});
    }, []);

    return (
        <div className="h-screen w-screen flex flex-col bg-gray-100">
            {/* Header */}
            <div className="h-12 bg-white border-b flex items-center justify-between px-4 shadow-sm">
                <div className="flex items-center gap-4">
                    <button
                        onClick={onSwitchToEditor}
                        className="text-sm text-gray-600 hover:text-blue-600 transition-colors flex items-center gap-1"
                    >
                        ← Back to Editor
                    </button>
                    <div className="h-6 w-px bg-gray-300"></div>
                    <h1 className="font-bold text-gray-800">
                        ▶ Execution View
                        {currentWorkflowName && <span className="font-normal text-gray-500 ml-2">— {currentWorkflowName}</span>}
                    </h1>
                </div>
                <div className="flex items-center gap-2">
                    {isRunning && (
                        <div className="flex items-center gap-2 text-sm text-green-600">
                            <span className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></span>
                            Running...
                        </div>
                    )}
                    <button
                        onClick={clearEvents}
                        className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                    >
                        Clear Log
                    </button>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Panel: Execution Log */}
                <div className="w-64 border-r flex-shrink-0">
                    <ExecutionLog
                        events={events}
                        selectedEventId={selectedEventId}
                        onSelectEvent={setSelectedEventId}
                        filter={filter}
                        onFilterChange={setFilter}
                    />
                </div>

                {/* Center Panel: Message Inspector */}
                <div className="flex-1 border-r">
                    <MessageInspector event={selectedEvent} />
                </div>

                {/* Right Panel: State */}
                <div className="w-80 flex-shrink-0">
                    <StatePanel sharedMemory={sharedMemory} results={results} />
                </div>
            </div>
        </div>
    );
};

export default ExecutionView;
