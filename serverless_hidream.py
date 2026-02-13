import requests
import json
import time
import os
import random
import base64
import random
from dotenv import load_dotenv

# Force UTF-8 encoding for .env loading
load_dotenv(encoding="utf-8")

# ===== Configuration =====
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
ENDPOINT_ID = "mlwf2u9itds0v3"
BASE_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"
# WORKFLOW_PATH = "hidream_i1_full_api.json" # Unused
OUTPUT_DIR = "output"

# Node IDs from Template (Simplified)
# 4: CheckpointLoader, 3: KSampler, 6: Pos, 7: Neg, 5: Latent, 8: Decode, 9: Save
# Using "hidream_i1_full_nf4.safetensors"

WORKFLOW_TEMPLATE = {
    "3": {
        "inputs": {
            "seed": 42,
            "steps": 28,
            "cfg": 7.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0]
        },
        "class_type": "KSampler"
    },
    "4": {
        "inputs": {
            "ckpt_name": "flux1-dev-fp8.safetensors"
        },
        "class_type": "CheckpointLoaderSimple"
    },
    "5": {
        "inputs": {
            "width": 768,
            "height": 768,
            "batch_size": 1
        },
        "class_type": "EmptyLatentImage"
    },
    "6": {
        "inputs": {
            "text": "",
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode"
    },
    "7": {
        "inputs": {
            "text": "",
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode"
    },
    "8": {
        "inputs": {
            "samples": ["3", 0],
            "vae": ["4", 2]
        },
        "class_type": "VAEDecode"
    },
    "9": {
        "inputs": {
            "images": ["8", 0],
            "filename_prefix": "hidream_serverless"
        },
        "class_type": "SaveImage"
    }
}

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def save_metadata(seed, pos, neg, width, height, steps, cfg):
    filename = f"serverless_{seed}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Seed: {seed}\n")
        f.write(f"Resolution: {width}x{height}\n")
        f.write(f"Steps: {steps}\n")
        f.write(f"CFG: {cfg}\n")
        f.write(f"Positive Prompt:\n{pos}\n\n")
        f.write(f"Negative Prompt:\n{neg}\n")
    print(f"📝 Metadata saved: {filepath}")

def generate_serverless_image(prompt_pos, prompt_neg, seed, steps=28, cfg=7.0, width=1024, height=1024):
    workflow = WORKFLOW_TEMPLATE.copy()
    
    # Update Workflow Nodes
    workflow["6"]["inputs"]["text"] = prompt_pos
    workflow["7"]["inputs"]["text"] = prompt_neg
    
    workflow["3"]["inputs"]["seed"] = seed
    workflow["3"]["inputs"]["steps"] = steps
    workflow["3"]["inputs"]["cfg"] = cfg
    
    workflow["5"]["inputs"]["width"] = width
    workflow["5"]["inputs"]["height"] = height
    
    filename_prefix = f"serverless_{seed}"
    workflow["9"]["inputs"]["filename_prefix"] = filename_prefix

    # Prepare Payload
    payload = {
        "input": {
            "workflow": workflow
        }
    }
    
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 1. Send Request
    print(f"🚀 Sending Job to Serverless Endpoint... (Seed: {seed})")
    try:
        response = requests.post(f"{BASE_URL}/run", json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        job_id = result.get("id")
        print(f"✅ Job Started: {job_id}")
        
        # Save Metadata
        save_metadata(seed, prompt_pos, prompt_neg, width, height, steps, cfg)
        
        return job_id
    except Exception as e:
        print(f"❌ Failed to start job: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return None

def wait_and_download(job_id, seed):
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}"
    }
    
    print(f"⏳ Waiting for Job {job_id} to complete...")
    start_time = time.time()
    
    while True:
        try:
            response = requests.get(f"{BASE_URL}/status/{job_id}", headers=headers)
            response.raise_for_status()
            status_data = response.json()
            status = status_data.get("status")
            
            if status == "COMPLETED":
                print("✅ Job COMPLETED!")
                output = status_data.get("output", {})
                
                images = []
                if "images" in output:
                    images = output["images"]
                elif "message" in output and isinstance(output["message"], str):
                    # Sometimes comes as a base64 string or URL in message
                    pass
                
                if isinstance(images, list) and len(images) > 0:
                    saved_files = []
                    for idx, img_data in enumerate(images):
                         # If it's a URL
                        if isinstance(img_data, str) and img_data.startswith("http"):
                             fname = f"serverless_{seed}_{idx}.png"
                             download_url(img_data, fname)
                             saved_files.append(os.path.join(OUTPUT_DIR, fname))
                        # If it's a dict with 'url'
                        elif isinstance(img_data, dict) and "url" in img_data:
                             fname = f"serverless_{seed}_{idx}.png"
                             download_url(img_data["url"], fname)
                             saved_files.append(os.path.join(OUTPUT_DIR, fname))
                        # If it's a dict with base64 'image' or 'data'
                        elif isinstance(img_data, dict) and ("image" in img_data or "data" in img_data):
                             b64_data = img_data.get("image") or img_data.get("data")
                             fname = f"serverless_{seed}_{idx}.png"
                             save_base64_image(b64_data, fname)
                             saved_files.append(os.path.join(OUTPUT_DIR, fname))
                        else:
                            print(f"⚠️ Unknown image format: {img_data.keys() if isinstance(img_data, dict) else img_data}")
                    return saved_files
                else:
                    print(f"⚠️ No images found in output. Raw output keys: {output.keys()}")
                    return []

            elif status == "FAILED":
                print(f"❌ Job FAILED: {status_data.get('error')}")
                return False
                
            elif status in ["IN_QUEUE", "IN_PROGRESS"]:
                time.sleep(5)
            else:
                print(f"Unknown status: {status}")
                time.sleep(5)
                
        except Exception as e:
            print(f"Error polling status: {e}")
            time.sleep(5)

        if time.time() - start_time > 600: # 10 min timeout
            print("⏱ Timeout waiting for job.")
            return False

def save_base64_image(b64_str, filename):
    try:
        save_path = os.path.join(OUTPUT_DIR, filename)
        with open(save_path, "wb") as f:
            f.write(base64.b64decode(b64_str))
        print(f"💾 Saved (Base64): {save_path}")
    except Exception as e:
        print(f"Failed to save base64 image: {e}")

def download_url(url, filename):
    try:
        r = requests.get(url)
        r.raise_for_status()
        save_path = os.path.join(OUTPUT_DIR, filename)
        with open(save_path, 'wb') as f:
            f.write(r.content)
        print(f"💾 Saved: {save_path}")
    except Exception as e:
        print(f"Failed to download image from {url}: {e}")

if __name__ == "__main__":
    if not RUNPOD_API_KEY:
        print("ERROR: RUNPOD_API_KEY not found. Please set it in .env")
        exit(1)

    # Test Run
    seed = random.randint(1, 9999999999)
    
    # User-Requested Dieselpunk Prompt
    pos = (
        "(masterpiece, best quality), 16-bit pixel art, character sprite, "
        "white background, dieselpunk villain, large muscular male, "
        "tattered black formal suit covered in dust and oil, rusty mechanical armor, "
        "worn-out metal, exposed wires, flickering dim amber eye sensor, "
        "industrial machinery parts on chest, massive heavy hydraulic arm cannon, "
        "retro game style, gritty texture, detailed weathering"
    )
    neg = "low quality, blurry, 3d, realistic, photo, bad anatomy"
    
    job_id = generate_serverless_image(pos, neg, seed)
    if job_id:
        files = wait_and_download(job_id, seed)
        print(f"Generated files: {files}")
