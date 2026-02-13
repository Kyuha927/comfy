import requests
import json

BASE_URL = "https://w2672t3cq8hyic-8188.proxy.runpod.net"

def check_status():
    print(f"Checking status for {BASE_URL}...")
    
    # 1. Check Queue
    try:
        res_queue = requests.get(f"{BASE_URL}/queue")
        res_queue.raise_for_status()
        queue_data = res_queue.json()
        
        pending = queue_data.get("queue_pending", [])
        running = queue_data.get("queue_running", [])
        
        print(f"\n--- Queue Status ---")
        print(f"Pending Jobs: {len(pending)}")
        for job in pending:
            print(f"  - ID: {job[1]}")
            
        print(f"Running Jobs: {len(running)}")
        for job in running:
            print(f"  - ID: {job[1]}")
            
    except Exception as e:
        print(f"Error checking queue: {e}")

    # 2. Check History
    try:
        res_history = requests.get(f"{BASE_URL}/history")
        res_history.raise_for_status()
        history_data = res_history.json()
        
        print(f"\n--- Recent History (Last 3) ---")
        items = list(history_data.items())
        total_items = len(items)
        for i in range(max(0, total_items - 3), total_items):
            prompt_id, details = items[i]
            status = details.get("status", {})
            completed = status.get("completed", False)
            outputs = details.get("outputs", {})
            
            print(f"  - Prompt ID: {prompt_id} | Completed: {completed}")
            if outputs:
                print(f"    Outputs:")
                for node_id, output in outputs.items():
                    if "images" in output:
                        for img in output["images"]:
                            print(f"      Node {node_id}: {img.get('filename')} (Subfolder: {img.get('subfolder')})")
            if not completed:
                print(f"    Messages: {status.get('messages', [])}")
                
    except Exception as e:
        print(f"Error checking history: {e}")

if __name__ == "__main__":
    check_status()
