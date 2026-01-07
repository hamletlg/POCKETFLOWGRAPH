import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import type { NodeProps } from 'reactflow';
import type { NodeMetadata } from '../api/client';

// We extend NodeProps to include our specific data structure
interface CustomNodeData extends NodeMetadata {
    label: string;
}

const CustomNode = ({ data, selected }: NodeProps<CustomNodeData>) => {
    return (
        <div className={`px-4 py-2 shadow-md rounded-md bg-white border-2 min-w-[150px] transition-all duration-200 ${selected ? 'border-blue-500 ring-2 ring-blue-300 shadow-lg' : 'border-gray-200'}`}>
            <div className="flex flex-col">
                <div className="font-bold text-sm border-b pb-1 mb-2 text-center text-gray-700">
                    {data.label}
                </div>

                <div className="flex justify-between">
                    {/* Inputs - Left Side */}
                    <div className="flex flex-col gap-2 relative">
                        {data.inputs?.map((input, index) => (
                            <div key={`input-${index}`} className="relative h-4 flex items-center">
                                <Handle
                                    type="target"
                                    position={Position.Left}
                                    id={`in-${input}`}
                                    style={{ left: -22, top: '50%', transform: 'translateY(-50%)' }}
                                    className="w-3 h-3 bg-blue-500"
                                />
                                <span className="text-xs text-gray-500 ml-1">{input !== 'default' ? input : 'In'}</span>
                            </div>
                        ))}
                    </div>

                    {/* Outputs - Right Side */}
                    <div className="flex flex-col gap-2 relative items-end">
                        {data.outputs?.map((output, index) => (
                            <div key={`output-${index}`} className="relative h-4 flex items-center justify-end">
                                <span className="text-xs text-gray-500 mr-1">{output !== 'default' ? output : 'Out'}</span>
                                <Handle
                                    type="source"
                                    position={Position.Right}
                                    id={`out-${output}`}
                                    style={{ right: -22, top: '50%', transform: 'translateY(-50%)' }}
                                    className="w-3 h-3 bg-green-500"
                                />
                            </div>
                        ))}
                    </div>
                </div>

                <div className="text-[10px] text-gray-400 mt-2 text-center">
                    {data.type}
                </div>
            </div>
        </div>
    );
};

export default memo(CustomNode);
