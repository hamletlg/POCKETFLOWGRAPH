#!/usr/bin/env python3

"""
Debug script to analyze WebSocket flow without running the full backend
"""

def analyze_websocket_flow():
    print("=== WebSocket Notification System Debug Analysis ===\n")
    
    print("1. EVENT FLOW ANALYSIS:")
    print("   Backend Events Generation:")
    print("   - engine.py:build_graph() sets pf_node.on_event = event_callback")
    print("   - base.py:BasePlatformNode.run() calls callback('node_start', ...)") 
    print("   - main.py:event_callback() uses asyncio.run_coroutine_threadsafe()")
    print("   - websockets.py:manager.broadcast() sends to all connections")
    print()
    
    print("2. POTENTIAL ISSUES IDENTIFIED:")
    print()
    
    print("   Issue #1: Duplicate Startup Event Handlers")
    print("   - main.py has two @app.on_event('startup') decorators")
    print("   - Second one may override the first")
    print("   - This could prevent loop_instance from being set")
    print()
    
    print("   Issue #2: Threading Problem")
    print("   - engine.py uses asyncio.to_thread(flow.run, shared_state)")
    print("   - base.py calls callback from within the thread")
    print("   - callback tries to schedule on main loop via run_coroutine_threadsafe")
    print("   - If loop_instance is None, events are lost")
    print()
    
    print("   Issue #3: Message Format Consistency")
    print("   - Frontend expects: msg.type and msg.payload.node_id")
    print("   - Backend sends: {type: event, payload: payload}")
    print("   - This seems consistent, but verify actual messages")
    print()
    
    print("   Issue #4: Node ID Mapping")
    print("   - Frontend nodes have IDs like 'dndnode_0', 'dndnode_1'")
    print("   - Backend uses IDs from workflow JSON")
    print("   - If mismatched, frontend won't find nodes to style")
    print()
    
    print("   Issue #5: WebSocket Connection Timing")
    print("   - Frontend connects in useEffect on component mount")
    print("   - If workflow runs before connection established, events lost")
    print("   - No explicit connection verification before workflow run")
    print()
    
    print("3. DEBUGGING STEPS:")
    print()
    print("   Step 1: Add logging to verify loop_instance is set")
    print("   Step 2: Add logging in event_callback to see if it's called")
    print("   Step 3: Add logging in manager.broadcast() to verify sends")
    print("   Step 4: Add browser console logging to verify receives")
    print("   Step 5: Check node ID mapping between frontend and backend")
    print()
    
    print("4. QUICK FIXES TO TRY:")
    print()
    print("   A. Consolidate startup handlers:")
    print("      @app.on_event('startup')")
    print("      async def startup():")
    print("          global loop_instance")
    print("          loop_instance = asyncio.get_running_loop()")
    print("          scheduler.start()")
    print()
    
    print("   B. Add safety checks in event_callback:")
    print("      def event_callback(event, payload):")
    print("          if not loop_instance:")
    print("              print('ERROR: loop_instance is None')")
    print("              return")
    print("          # ... rest of callback")
    print()
    
    print("   C. Add connection verification in frontend:")
    print("      ws.onopen = () => {")
    print("          console.log('WebSocket connected, ready for events')")
    print("          setWebSocketReady(true)")
    print("      }")
    print()
    
    print("   D. Verify node ID mapping:")
    print("      console.log('Current node IDs:', nodes.map(n => n.id))")
    print("      console.log('Event node_id:', msg.payload.node_id)")
    print()

if __name__ == "__main__":
    analyze_websocket_flow()
