import React, { useState } from 'react';
import { createWorkspace, deleteWorkspace } from '../api/workspace';

interface MenuBarProps {
    currentWorkflowName: string | null;
    isDirty: boolean;
    workspaces: string[];
    activeWorkspace: string;
    onSwitchWorkspace: (name: string) => void;
    onRefreshWorkspaces: () => void;
    onNewProject: () => void;
    onLoadProject: (name: string) => void;
    onSaveProject: () => void;
    onSaveAsProject: (name: string) => void;
    onCloseProject: () => void;
    availableWorkflows: string[];
    onRefreshWorkflows: () => void;
}

export const MenuBar: React.FC<MenuBarProps> = ({
    currentWorkflowName,
    isDirty,
    workspaces,
    activeWorkspace,
    onSwitchWorkspace,
    onRefreshWorkspaces,
    onNewProject,
    onLoadProject,
    onSaveProject,
    onSaveAsProject,
    onCloseProject,
    availableWorkflows,
    onRefreshWorkflows
}) => {
    const [isWsDropdownOpen, setIsWsDropdownOpen] = useState(false);
    const [isFileDropdownOpen, setIsFileDropdownOpen] = useState(false);
    const [newWsName, setNewWsName] = useState("");
    const [isCreatingWs, setIsCreatingWs] = useState(false);

    const handleCreateWorkspace = async () => {
        if (!newWsName) return;
        try {
            await createWorkspace(newWsName);
            setNewWsName("");
            setIsCreatingWs(false);
            onRefreshWorkspaces();
        } catch (e) {
            alert("Failed to create workspace: " + e);
        }
    };

    const handleDeleteWorkspace = async (e: React.MouseEvent, name: string) => {
        e.stopPropagation();
        if (!confirm(`Are you sure you want to delete workspace "${name}"? This will delete all data inside it.`)) return;
        try {
            await deleteWorkspace(name);
            onRefreshWorkspaces();
        } catch (error) {
            alert("Failed to delete workspace: " + error);
        }
    }

    return (
        <div className="bg-gray-800 text-white p-2 flex items-center justify-between shadow-md">
            <div className="flex items-center space-x-4">
                <span className="font-bold text-lg">PocketFlow</span>

                {/* Workspace Selector */}
                <div className="relative">
                    <button
                        onClick={() => setIsWsDropdownOpen(!isWsDropdownOpen)}
                        className="bg-gray-700 px-3 py-1 rounded hover:bg-gray-600 flex items-center"
                    >
                        WS: {activeWorkspace}
                        <span className="ml-2 text-xs">▼</span>
                    </button>
                    {isWsDropdownOpen && (
                        <div className="absolute top-full left-0 mt-1 w-64 bg-white text-black rounded shadow-lg z-50 p-2 border border-gray-200">
                            <div className="font-semibold text-xs text-gray-500 mb-2">Switch Workspace</div>
                            {workspaces.map(ws => (
                                <div
                                    key={ws}
                                    className={`flex justify-between items-center cursor-pointer px-2 py-1 rounded hover:bg-blue-100 ${ws === activeWorkspace ? 'bg-blue-50 font-bold' : ''}`}
                                    onClick={() => { onSwitchWorkspace(ws); setIsWsDropdownOpen(false); }}
                                >
                                    <span>{ws}</span>
                                    {ws !== "default" && ws !== activeWorkspace && (
                                        <button
                                            onClick={(e) => handleDeleteWorkspace(e, ws)}
                                            className="text-red-500 hover:text-red-700 text-xs px-1 hover:bg-red-100 rounded"
                                            title="Delete Workspace"
                                        >
                                            ✕
                                        </button>
                                    )}
                                </div>
                            ))}
                            <div className="border-t my-2"></div>
                            {isCreatingWs ? (
                                <div className="flex flex-col space-y-2">
                                    <input
                                        autoFocus
                                        className="border p-1 text-sm rounded bg-gray-50 text-black"
                                        value={newWsName}
                                        onChange={e => setNewWsName(e.target.value)}
                                        placeholder="New WS Name"
                                    />
                                    <div className="flex space-x-2">
                                        <button onClick={handleCreateWorkspace} className="bg-green-600 text-white px-2 py-1 rounded text-xs">Create</button>
                                        <button onClick={() => setIsCreatingWs(false)} className="bg-gray-400 text-white px-2 py-1 rounded text-xs">Cancel</button>
                                    </div>
                                </div>
                            ) : (
                                <button
                                    onClick={() => setIsCreatingWs(true)}
                                    className="w-full text-left text-blue-600 hover:text-blue-800 text-sm px-2"
                                >
                                    + Create New Workspace
                                </button>
                            )}
                        </div>
                    )}
                </div>

                {/* File Menu */}
                <div className="relative">
                    <button
                        onClick={() => { setIsFileDropdownOpen(!isFileDropdownOpen); onRefreshWorkflows(); }}
                        className="hover:bg-gray-700 px-3 py-1 rounded"
                    >
                        Project
                    </button>
                    {isFileDropdownOpen && (
                        <div className="absolute top-full left-0 mt-1 w-48 bg-white text-black rounded shadow-lg z-50 py-1 border border-gray-200">
                            <div
                                onClick={() => { onNewProject(); setIsFileDropdownOpen(false); }}
                                className="px-4 py-2 hover:bg-gray-100 cursor-pointer"
                            >
                                New Project
                            </div>

                            <div className="relative group">
                                <div className="px-4 py-2 hover:bg-gray-100 cursor-pointer flex justify-between items-center">
                                    Open Project ▸
                                </div>
                                <div className="absolute left-full top-0 w-48 bg-white rounded shadow-lg border border-gray-200 hidden group-hover:block max-h-64 overflow-y-auto">
                                    {availableWorkflows.length === 0 && <div className="px-4 py-2 text-gray-500 italic text-sm">No projects</div>}
                                    {availableWorkflows.map(wf => (
                                        <div
                                            key={wf}
                                            onClick={() => { onLoadProject(wf); setIsFileDropdownOpen(false); }}
                                            className="px-4 py-2 hover:bg-gray-100 cursor-pointer"
                                        >
                                            {wf}
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="border-t my-1"></div>
                            <div
                                onClick={() => { onSaveProject(); setIsFileDropdownOpen(false); }}
                                className={`px-4 py-2 hover:bg-gray-100 cursor-pointer ${!currentWorkflowName ? 'text-gray-400' : ''}`}
                            >
                                Save
                            </div>
                            <div
                                onClick={() => {
                                    const name = prompt("Enter project name:", currentWorkflowName || "");
                                    if (name) { onSaveAsProject(name); setIsFileDropdownOpen(false); }
                                }}
                                className="px-4 py-2 hover:bg-gray-100 cursor-pointer"
                            >
                                Save As...
                            </div>
                            <div className="border-t my-1"></div>
                            <div
                                onClick={() => { onCloseProject(); setIsFileDropdownOpen(false); }}
                                className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-red-600"
                            >
                                Close Project
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <div className="flex items-center space-x-4">
                {currentWorkflowName && (
                    <div className="text-sm">
                        <span className="text-gray-400">Project:</span> {currentWorkflowName}
                        {isDirty && <span className="text-yellow-400 ml-1">● (Unsaved)</span>}
                    </div>
                )}
            </div>
        </div>
    );
};
