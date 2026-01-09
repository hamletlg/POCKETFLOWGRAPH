# PocketFlowGraph

## What it is

PocketFlowGraph is an agentic no-code platform built with a local-first philosophy. It is designed to be simple, lightweight, and easy to customize and experiment with. The platform allows users to create and manage workflows visually through a web-based interface, and it can export these workflows to executable Python code.

## Why

PocketFlowGraph was created to fulfill three main objectives:

1. To provide an agentic no-code platform built with PocketFlow, a lightweight agentic library.
2. To enable workflow export to Python code, allowing users to inspect, modify, and extend their workflows programmatically.
3. To serve as a personal no-code agentic platform for research and experimentation with agentic architectures.

## Architecture

The platform consists of two main components:

1. **Backend**: Built with Python and PocketFlow, the backend handles workflow execution, node management, and memory storage. It includes a node registry that manages different types of nodes (e.g., LLM, data, control flow, web, and memory nodes).

2. **Frontend**: Built with React and TypeScript, the frontend provides a visual interface for creating and managing workflows. It includes components for node selection, workflow editing, and workflow execution.

The platform uses a graph-based architecture where nodes represent different operations, and edges represent data flow between nodes. Workflows are defined as directed graphs, and the platform provides tools to create, edit, and execute these workflows.

## Main Types of Nodes Available

PocketFlowGraph includes several types of nodes that can be used to build workflows:

1. **LLM Nodes**: These nodes handle language model operations. They support variable injection using `{input}` and `{memory_key}` and can use both session memory (in-memory) and persistent memory (file-based).

2. **Data Nodes**: These nodes handle data operations. They can store and retrieve data with specific keys, support persistent memory storage, and can extract fields from JSON/string and store them in memory.

3. **Control Flow Nodes**: These nodes handle control flow operations. They support loops, conditionals, and error handling. They can store loop variables and indices in memory and pass memory between sub-workflows.

4. **Web Nodes**: These nodes handle web operations. They can access memory variables in web requests, store web request information in memory, and retrieve previously fetched data.

5. **Memory Nodes**: These nodes handle memory operations. They can store and retrieve data in memory, support persistent memory storage to a JSON file, and can store and retrieve data with specific keys.

6. **Vector Memory Nodes**: These nodes implement semantic search memory using ChromaDB for RAG (Retrieval-Augmented Generation) and episodic memory. They support vector storage and retrieval, semantic search, and storing search results in shared memory.

7. **IO Nodes**: These nodes handle file operations. They can store file metadata in memory, retrieve previously processed files, and support persistent memory storage.

8. **Custom Nodes**: These nodes allow users to create custom operations. They can be implemented as Python classes that inherit from `BasePlatformNode` and implement the required methods.

## How to Use   


1. **Start the platform**: Use the provided script:
   ```
   python start_pocketflow.py
   ```

2. **Creating Workflows**: Use the web interface to create workflows by adding nodes and connecting them with edges.

3. **Exporting**: Export workflows to Python code for further customization and analysis.

4. **Customization**: Modify the platform by adding new nodes or modifying existing ones.

## Requirements

- Python 3.10+
- Node.js 14+
- npm 6+
- A web browser for the frontend interface

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/pocketflowgraph.git
   ```

2. Install dependencies:
   ```
   cd pocketflowgraph
   pip install -r requirements.txt
   ```

3. Install frontend dependencies:
   ```
   cd frontend
   npm install
   ```

4. Start the platform:
   ```
   python start_pocketflow.py
   ```

## License

PocketFlowGraph is licensed under the MIT License. See the LICENSE file for more information.
