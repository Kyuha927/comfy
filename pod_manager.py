import requests
import os
from dotenv import load_dotenv

load_dotenv()

# RunPod API Key should be in .env as RUNPOD_API_KEY
API_KEY = os.getenv("RUNPOD_API_KEY")
# Target Pod ID
POD_ID = "w2672t3cq8hyic"

def stop_pod(pod_id=POD_ID):
    if not API_KEY:
        print("ERROR: RUNPOD_API_KEY not found in environment variables.")
        return False
        
    print(f"Attempting to stop pod {pod_id}...")
    
    # RunPod API v1 Stop Endpoint
    url = f"https://api.runpod.io/v1/user/pods/{pod_id}/stop"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        print(f"SUCCESS: Pod {pod_id} shutdown signal sent.")
        return True
    except Exception as e:
        print(f"FAILED to stop pod: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return False

if __name__ == "__main__":
    stop_pod()
