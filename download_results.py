import requests
import json
import os

BASE_URL = "https://w2672t3cq8hyic-8188.proxy.runpod.net"
OUTPUT_DIR = r"c:\Users\jhk92\OneDrive\문서\GitHub\ai\Moltbot\output"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def download_recent():
    r = requests.get(f"{BASE_URL}/history")
    history = r.json()
    
    # Get last 5 jobs
    items = list(history.values())[-5:]
    
    print(f"Checking last 5 jobs for outputs...")
    for item in items:
        outputs = item.get('outputs', {})
        for node_id, out in outputs.items():
            if 'images' in out:
                for img in out['images']:
                    fn = img['filename']
                    local_path = os.path.join(OUTPUT_DIR, fn)
                    
                    if os.path.exists(local_path):
                        print(f"Skipping {fn}, already exists.")
                        continue
                        
                    print(f"Downloading {fn}...")
                    img_url = f"{BASE_URL}/view?filename={fn}&type=output"
                    try:
                        img_res = requests.get(img_url)
                        img_res.raise_for_status()
                        with open(local_path, 'wb') as f:
                            f.write(img_res.content)
                        print(f"  Saved to {local_path}")
                    except Exception as e:
                        print(f"  Error downloading {fn}: {e}")

if __name__ == "__main__":
    download_recent()
