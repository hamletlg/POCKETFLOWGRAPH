"""
FIXED VERSION of the WebSocket useEffect in GraphEditor.tsx
Replace lines 147-197 in GraphEditor.tsx with this enhanced version
"""

// WebSocket Connection with enhanced debugging
useEffect(() => {
    console.log("DEBUG: Setting up WebSocket connection...");
    const ws = new WebSocket('ws://localhost:8000/api/ws');
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 3;

    const connect = () => {
        console.log(`DEBUG: Attempting WebSocket connection (attempt ${reconnectAttempts + 1})...`);
        
        ws.onopen = () => {
            console.log("DEBUG: WebSocket connected successfully!");
            reconnectAttempts = 0;
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                console.log("DEBUG: WebSocket message received:", msg);
                
                // Log current node IDs for debugging
                const currentNodeIds = nodes.map(n => n.id);
                console.log("DEBUG: Current frontend node IDs:", currentNodeIds);
                
                if (msg.type === 'workflow_start') {
                    console.log("DEBUG: Workflow started - clearing execution states");
                    // Clear all states when new workflow starts
                    setExecutingNodes(new Set());
                    setLastExecutedNode(null);
                    setHasError(false);
                } else if (msg.type === 'node_start') {
                    console.log(`DEBUG: Node start event - node_id: ${msg.payload?.node_id}`);
                    if (msg.payload?.node_id) {
                        setExecutingNodes(prev => {
                            const newSet = new Set(prev).add(msg.payload.node_id);
                            console.log("DEBUG: Updated executing nodes:", Array.from(newSet));
                            return newSet;
                        });
                        // Clear previous last executed node when new one starts
                        setLastExecutedNode(null);
                        setHasError(false);
                    } else {
                        console.warn("WARNING: node_start event missing node_id");
                    }
                } else if (msg.type === 'node_end') {
                    console.log(`DEBUG: Node end event - node_id: ${msg.payload?.node_id}`);
                    if (msg.payload?.node_id) {
                        setExecutingNodes(prev => {
                            const newSet = new Set(prev);
                            newSet.delete(msg.payload.node_id);
                            console.log("DEBUG: Updated executing nodes:", Array.from(newSet));
                            return newSet;
                        });
                        setLastExecutedNode(msg.payload.node_id);
                        setHasError(false);
                    } else {
                        console.warn("WARNING: node_end event missing node_id");
                    }
                } else if (msg.type === 'node_error') {
                    console.log(`DEBUG: Node error event - node_id: ${msg.payload?.node_id}, error: ${msg.payload?.error}`);
                    if (msg.payload?.node_id) {
                        setExecutingNodes(prev => {
                            const newSet = new Set(prev);
                            newSet.delete(msg.payload.node_id);
                            return newSet;
                        });
                        setLastExecutedNode(msg.payload.node_id);
                        setHasError(true);
                    } else {
                        console.warn("WARNING: node_error event missing node_id");
                    }
                } else if (msg.type === 'workflow_end') {
                    console.log("DEBUG: Workflow ended");
                    // Keep current state, no alerts
                } else if (msg.type === 'workflow_error') {
                    console.log("DEBUG: Workflow error:", msg.payload);
                    // Keep current state, no alerts
                } else {
                    console.log("DEBUG: Unknown message type:", msg.type);
                }
            } catch (e) {
                console.error("DEBUG: WebSocket message parsing error:", e);
                console.error("DEBUG: Raw message:", event.data);
            }
        };

        ws.onclose = (event) => {
            console.log(`DEBUG: WebSocket closed. Code: ${event.code}, Reason: ${event.reason}`);
            
            // Attempt reconnection if not explicitly closed and haven't exceeded max attempts
            if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                console.log(`DEBUG: Attempting to reconnect in 2 seconds...`);
                setTimeout(connect, 2000);
            }
        };

        ws.onerror = (error) => {
            console.error("DEBUG: WebSocket error:", error);
        };
    };

    connect();

    return () => {
        console.log("DEBUG: Cleaning up WebSocket connection...");
        ws.close();
    };
}, [nodes]); // Add nodes dependency to have access to current node IDs
