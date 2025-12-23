import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

export interface Workspace {
    name: string;
}

export const fetchWorkspaces = async (): Promise<string[]> => {
    const res = await axios.get(`${API_BASE}/workspaces`);
    return res.data;
};

export const createWorkspace = async (name: string): Promise<void> => {
    await axios.post(`${API_BASE}/workspaces`, { name });
};

export const fetchActiveWorkspace = async (): Promise<string> => {
    const res = await axios.get(`${API_BASE}/workspaces/active`);
    return res.data.name;
};

export const setActiveWorkspace = async (name: string): Promise<void> => {
    await axios.post(`${API_BASE}/workspaces/active`, { name });
};

export const deleteWorkspace = async (name: string): Promise<void> => {
    await axios.delete(`${API_BASE}/workspaces/${name}`);
};
