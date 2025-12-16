import React from 'react';
import type { NodeMetadata } from '../api/client';

interface SidebarProps {
    nodes: NodeMetadata[];
}

export const Sidebar: React.FC<SidebarProps> = ({ nodes }) => {
    const onDragStart = (event: React.DragEvent, nodeType: string, inputs: string[], outputs: string[]) => {
        event.dataTransfer.setData('application/reactflow', nodeType);
        event.dataTransfer.setData('application/inputs', JSON.stringify(inputs));
        event.dataTransfer.setData('application/outputs', JSON.stringify(outputs));
        event.dataTransfer.effectAllowed = 'move';
    };

    // Category Definitions
    const categories: Record<string, string[]> = {
        "General": ["start", "debug"],
        "AI": ["llm"],
        "Web": ["web_search", "web_fetch", "rss_read"],
        "Data": ["memory", "sqlite"],
        "Input/Output": ["file_read", "file_write"],
        "Scheduling": ["cron"]
    };

    // Group nodes
    const groupedNodes = nodes.reduce((acc, node) => {
        let matched = false;
        for (const [cat, types] of Object.entries(categories)) {
            if (types.includes(node.type)) {
                if (!acc[cat]) acc[cat] = [];
                acc[cat].push(node);
                matched = true;
                break;
            }
        }
        if (!matched) {
            if (!acc["Other"]) acc["Other"] = [];
            acc["Other"].push(node);
        }
        return acc;
    }, {} as Record<string, NodeMetadata[]>);

    // Order categories
    const orderedCategories = ["General", "Scheduling", "AI", "Web", "Data", "Input/Output", "Other"];

    return (
        <aside className="bg-gray-50 border-r border-gray-200 p-4 h-full overflow-y-auto flex flex-col w-full">
            <div className="mb-4 flex-shrink-0">
                <h2 className="text-xl font-bold text-gray-800">Nodes</h2>
                <p className="text-xs text-gray-500">Drag to canvas</p>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto pr-1">
                {orderedCategories.map(cat => {
                    const catNodes = groupedNodes[cat];
                    if (!catNodes || catNodes.length === 0) return null;

                    return (
                        <details key={cat} open className="group">
                            <summary className="flex items-center justify-between font-semibold text-sm text-gray-700 cursor-pointer list-none bg-gray-100 p-2 rounded hover:bg-gray-200 transition mb-2">
                                <span>{cat}</span>
                                <span className="transform group-open:rotate-180 transition-transform text-xs">▼</span>
                            </summary>
                            <div className="space-y-2 pl-1">
                                {catNodes.map((node) => (
                                    <div
                                        key={node.type}
                                        className="p-3 bg-white border border-gray-200 rounded cursor-grab hover:border-blue-500 hover:shadow-md transition-all shadow-sm group/node"
                                        onDragStart={(event) => onDragStart(event, node.type, node.inputs, node.outputs)}
                                        draggable
                                    >
                                        <div className="flex items-center justify-between">
                                            <div className="font-bold text-xs text-gray-800 capitalize">{node.type.replace(/_/g, ' ')}</div>
                                            <div className="w-2 h-2 rounded-full bg-green-400 opacity-0 group-hover/node:opacity-100 transition-opacity"></div>
                                        </div>
                                        <div className="text-[10px] text-gray-500 mt-1 leading-tight">{node.description}</div>
                                    </div>
                                ))}
                            </div>
                        </details>
                    );
                })}
            </div>
        </aside>
    );
};
