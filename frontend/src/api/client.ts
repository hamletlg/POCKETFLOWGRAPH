import axios from 'axios';

const API_BASE = 'http://localhost:8000';

export interface NodeMetadata {
    type: string;
    description: string;
    inputs: string[];
    outputs: string[];
    params: Record<string, string>;
}

export const fetchNodes = async (): Promise<NodeMetadata[]> => {
    const response = await axios.get(`${API_BASE}/api/nodes`);
    return response.data;
};

export const runWorkflow = async (workflow: any) => {
    const response = await axios.post(`${API_BASE}/api/workflow/run`, workflow);
    return response.data;
};

export const listWorkflows = async (): Promise<string[]> => {
    const response = await axios.get(`${API_BASE}/api/workflows`);
    return response.data;
};

export const saveWorkflow = async (name: string, workflow: any) => {
    const response = await axios.post(`${API_BASE}/api/workflows/${name}`, workflow);
    return response.data;
};

export const loadWorkflow = async (name: string) => {
    const response = await axios.get(`${API_BASE}/api/workflows/${name}`);
    return response.data;
};

export const deleteWorkflow = async (name: string) => {
    const response = await axios.delete(`${API_BASE}/api/workflows/${name}`);
    return response.data;
};

export const exportWorkflow = async (workflow: any) => {
    const response = await axios.post(`${API_BASE}/api/export`, workflow, {
        responseType: 'blob' // Important for handling file downloads
    });
    return response.data;
};
