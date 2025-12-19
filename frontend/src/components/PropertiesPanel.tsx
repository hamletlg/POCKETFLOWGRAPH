import React, { useEffect, useState } from 'react';
import type { Node } from 'reactflow';
import type { NodeMetadata } from '../api/client';

interface PropertiesPanelProps {
    selectedNode: Node | null;
    onUpdateNodeData: (id: string, newData: any) => void;
    availableNodes: NodeMetadata[];
    onDeleteNode: (id: string) => void;
}

export const PropertiesPanel: React.FC<PropertiesPanelProps> = ({ selectedNode, onUpdateNodeData, availableNodes, onDeleteNode }) => {
    const [params, setParams] = useState<Record<string, any>>({});

    // When selection changes, load current params
    useEffect(() => {
        if (selectedNode) {
            setParams(selectedNode.data.params || {});
        } else {
            setParams({});
        }
    }, [selectedNode]);

    if (!selectedNode) {
        return (
            <aside className="w-80 bg-gray-50 border-l border-gray-200 p-4 h-full">
                <div className="text-gray-500 text-sm text-center mt-10">Select a node to edit properties</div>
            </aside>
        );
    }

    // Find metadata to know what fields to show
    const nodeMeta = availableNodes.find(n => n.type === selectedNode.data.type);

    const handleChange = (key: string, value: string) => {
        const newParams = { ...params, [key]: value };
        setParams(newParams);

        // Propagate update to parent (GraphEditor)
        // We update the whole 'data' object, preserving other fields
        onUpdateNodeData(selectedNode.id, {
            ...selectedNode.data,
            params: newParams
        });
    };

    return (
        <aside className="bg-white border-l border-gray-200 p-4 h-full flex flex-col shadow-lg overflow-y-auto w-full">
            <div className="flex justify-between items-center border-b pb-2 mb-4">
                <h3 className="font-bold text-lg text-gray-800">Properties</h3>
                <button
                    onClick={() => onDeleteNode(selectedNode.id)}
                    className="text-red-500 hover:text-red-700 text-xs border border-red-200 hover:bg-red-50 px-2 py-1 rounded transition"
                >
                    Delete Node
                </button>
            </div>

            <div className="mb-4">
                <label className="block text-xs font-semibold text-gray-500 mb-1">ID</label>
                <input
                    type="text"
                    value={selectedNode.id}
                    disabled
                    className="w-full text-sm p-2 bg-gray-100 border rounded text-gray-500"
                />
            </div>

            <div className="mb-4">
                <label className="block text-xs font-semibold text-gray-500 mb-1">Type</label>
                <input
                    type="text"
                    value={selectedNode.data.type}
                    disabled
                    className="w-full text-sm p-2 bg-gray-100 border rounded text-gray-500"
                />
            </div>

            <div className="mb-6">
                <label className="block text-xs font-semibold text-gray-500 mb-1">Label</label>
                <input
                    type="text"
                    value={selectedNode.data.label}
                    onChange={(e) => onUpdateNodeData(selectedNode.id, { ...selectedNode.data, label: e.target.value })}
                    className="w-full text-sm p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none transition"
                />
            </div>

            <h4 className="font-semibold text-sm mb-3 text-gray-700">Parameters</h4>

            {nodeMeta?.params && Object.keys(nodeMeta.params).length > 0 ? (
                <div className="space-y-4">
                    {Object.entries(nodeMeta.params).map(([key, paramDefRaw]) => {
                        // Handle both old string format and new ParameterDefinition format
                        let paramType: string;
                        let enumOptions: string[] | undefined;
                        let defaultValue: any;
                        let description: string | undefined;
                        
                        if (typeof paramDefRaw === 'string') {
                            // Old format - simple string
                            paramType = paramDefRaw;
                        } else {
                            // New format - ParameterDefinition object
                            paramType = paramDefRaw.type;
                            enumOptions = paramDefRaw.enum;
                            defaultValue = paramDefRaw.default;
                            description = paramDefRaw.description;
                        }
                        
                        // Determine input type
                        const isBoolean = paramType === 'boolean';
                        const isEnum = enumOptions && enumOptions.length > 0;
                        const isMultiLine = key.includes('prompt') || key.includes('content') || key.includes('query') || key.includes('script_body');
                        
                        // Get current value or default
                        let currentValue = params[key];
                        if (currentValue === undefined && defaultValue !== undefined) {
                            currentValue = defaultValue;
                        }

                        return (
                            <div key={key} className={isBoolean ? "flex items-center gap-2" : ""}>
                                <label className="block text-xs font-medium text-gray-600 mb-1 capitalize">
                                    {key.replace(/_/g, ' ')}
                                </label>
                                
                                {isBoolean ? (
                                    <input
                                        type="checkbox"
                                        checked={currentValue === 'true' || currentValue === true}
                                        onChange={(e) => handleChange(key, e.target.checked)}
                                        className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                                    />
                                ) : isEnum ? (
                                    <select
                                        value={currentValue || defaultValue || ''}
                                        onChange={(e) => handleChange(key, e.target.value)}
                                        className="w-full text-sm p-2 border border-gray-300 rounded focus:border-blue-500 outline-none bg-white"
                                    >
                                        {enumOptions.map(option => (
                                            <option key={option} value={option}>
                                                {option}
                                            </option>
                                        ))}
                                    </select>
                                ) : isMultiLine ? (
                                    <textarea
                                        value={currentValue || ''}
                                        onChange={(e) => handleChange(key, e.target.value)}
                                        className="w-full text-sm p-2 border border-gray-300 rounded focus:border-blue-500 outline-none min-h-[100px]"
                                        placeholder={`Enter ${key}...`}
                                    />
                                ) : (
                                    <input
                                        type="text"
                                        value={currentValue || ''}
                                        onChange={(e) => handleChange(key, e.target.value)}
                                        className="w-full text-sm p-2 border border-gray-300 rounded focus:border-blue-500 outline-none"
                                        placeholder={`Enter ${key}`}
                                    />
                                )}
                                
                                {/* Show parameter description or type */}
                                {description ? (
                                    <p className="text-[10px] text-gray-500 text-right mt-0.5">{description}</p>
                                ) : !isBoolean && (
                                    <p className="text-[10px] text-gray-400 text-right mt-0.5">{paramType}</p>
                                )}
                            </div>
                        );
                    })}
                </div>
            ) : (
                <p className="text-sm text-gray-400 italic">No configurable parameters.</p>
            )}

        </aside>
    );
};
