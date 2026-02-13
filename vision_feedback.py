import os
import base64
import requests
import json
from dotenv import load_dotenv

load_dotenv(encoding="utf-8")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("MODEL", "claude-3-5-sonnet-20240620")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_image(image_path, prompt):
    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY not found.")
        return

    base64_image = encode_image(image_path)
    media_type = "image/png"  # Assuming PNG from ComfyUI
    if image_path.endswith(".jpg") or image_path.endswith(".jpeg"):
        media_type = "image/jpeg"

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    data = {
        "model": MODEL,
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_image
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        text_response = result['content'][0]['text']
        print("\n--- AI Analysis Result ---")
        print(text_response)
        
        # Parse score
        import re
        score = 0
        match = re.search(r"Score:\s*(\d+)/10", text_response, re.IGNORECASE)
        if match:
            score = int(match.group(1))
        else:
             # Fallback: look for just rating
             match = re.search(r"Rating:\s*(\d+)/10", text_response, re.IGNORECASE)
             if match:
                 score = int(match.group(1))

        return score, text_response
    except Exception as e:
        print(f"Error calling Anthropic API: {e}")
        if hasattr(e, 'response') and e.response:
             print(f"Response: {e.response.text}")
        return 0, str(e)

if __name__ == "__main__":
    # Find the most recent serverless image
    output_dir = "output"
    files = [f for f in os.listdir(output_dir) if f.startswith("serverless_") and f.endswith(".png")]
    if not files:
        print("No serverless images found in output/.")
        exit()
    
    # Sort by modification time (newest first)
    latest_image = max([os.path.join(output_dir, f) for f in files], key=os.path.getmtime)
    print(f"Analyzing latest image: {latest_image}")

    prompt = (
        "Analyze this pixel art character image. "
        "1. Is the resolution high quality and clear (1024x1024 level) or blurry/broken? "
        "2. Does it accurately depict a 'dieselpunk villain'? "
        "3. Rate the overall quality from 1 to 10. "
        "IMPORTANT: You MUST end your response with exactly: 'Score: X/10' where X is the number."
    )
    
    score, text = analyze_image(latest_image, prompt)
    print(f"Parsed Score: {score}")
