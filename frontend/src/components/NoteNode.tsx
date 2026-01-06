import { memo } from 'react';
import { NodeResizer } from 'reactflow';
import type { NodeProps } from 'reactflow';

const NoteNode = ({ data, selected }: NodeProps) => {
    return (
        <div className="h-full w-full">
            <NodeResizer
                color="#ff0071"
                isVisible={selected}
                minWidth={100}
                minHeight={100}
            />
            <div
                className={`h-full w-full p-4 rounded-sm shadow-md bg-yellow-100 border border-yellow-200 flex flex-col font-serif ${selected ? 'ring-2 ring-yellow-400' : ''}`}
                style={{                    
                    backgroundColor: '#fef3c7'
                }}
            >
                <textarea
                    className="bg-transparent border-none outline-none resize-none flex-1 text-sm text-gray-800 placeholder-gray-400 w-full h-full"
                    placeholder="Type a note..."
                    defaultValue={data.label}
                    onChange={(evt) => {
                        if (data.onChange) data.onChange(evt.target.value);
                    }}
                />
            </div>
        </div>
    );
};

export default memo(NoteNode);
