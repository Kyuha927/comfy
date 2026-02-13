import os
import sys
import json
import base64
import time
import argparse
from typing import List, Dict, Any, Optional, Union

from dotenv import load_dotenv
import requests

# Find .env in project root or current dir
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if not os.path.exists(env_path):
    env_path = ".env"
# print(f"[Debug] Loading env from: {os.path.abspath(env_path)} (Exists: {os.path.exists(env_path)})")
load_dotenv(os.path.abspath(env_path))

COMPUTER_USE_BETA = ["computer-use-2025-01-24"]
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"

# Import tools
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.computer import ComputerTool
from tools.bash import BashTool

class ModelRouter:
    def __init__(self):
        from openai import OpenAI
        # Using Google's OpenAI-compatible endpoint directly for highest speed and reliability
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
        self.routing_model = "models/gemini-2.0-flash"
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = None

    def route(self, prompt: str) -> Dict[str, str]:
        """Routes the prompt to the best model using direct Google API."""
        if not self.client:
            print("[Router] No GOOGLE_API_KEY found. Falling back to Gemini 2.0 Flash.")
            return {"provider": "google", "model": "models/gemini-1.5-pro"}

        routing_prompt = f"""Analyze the following user prompt and categorize it to select the best AI model.
Priority Hierarchy:
1. 'heavy_complex': Gemini 1.5 Pro (Deep coding, architectural design)
2. 'standard_fast': Gemini 1.5 Flash (General tasks, quick searches)
3. 'reasoning_free': DeepSeek R1 (Deep logic/math)
4. 'local_simple': Qwen3 (Simple local file ops)

Prompt: "{prompt}"

Return ONLY a JSON object: {{"category": "heavy_complex"|"standard_fast"|"reasoning_free"|"local_simple", "justification": "short reason"}}
"""
        try:
            res = self.client.chat.completions.create(
                model=self.routing_model,
                messages=[{"role": "user", "content": routing_prompt}],
                response_format={"type": "json_object"}
            )
            analysis_text = res.choices[0].message.content
            # Cleanup potential markdown
            if "```json" in analysis_text:
                analysis_text = analysis_text.split("```json")[1].split("```")[0].strip()
            elif "```" in analysis_text:
                analysis_text = analysis_text.split("```")[1].split("```")[0].strip()
                
            analysis = json.loads(analysis_text)
            category = analysis.get("category", "standard_fast")
            print(f"[Router] Category: {category} ({analysis.get('justification', '')})")
            
            if category == "heavy_complex":
                return {"provider": "google", "model": "models/gemini-1.5-pro"} # Use 2.0 Flash as primary for speed
            elif category == "standard_fast":
                return {"provider": "google", "model": "models/gemini-1.5-pro-lite"}
            elif category == "reasoning_free":
                return {"provider": "openrouter", "model": "deepseek/deepseek-r1:free"}
            else:
                return {"provider": "ollama", "model": "qwen3:8b"}
        except Exception as e:
            print(f"[Router] Routing failed ({e}). Falling back to Gemini 2.0 Flash.")
            return {"provider": "google", "model": "models/gemini-1.5-pro"}

class MoltbotAgent:
    def __init__(self, provider: str = "anthropic", model: Optional[str] = None):
        self.provider = provider
        self.messages = []
        self.computer_tool = ComputerTool()
        self.bash_tool = BashTool()
        
        # Determine the API type and client setup
        if self.provider == "anthropic":
            from anthropic import Anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            base_url = os.getenv("ANTHROPIC_BASE_URL")
            self.client = Anthropic(api_key=api_key, base_url=base_url)
            self.model = model or DEFAULT_ANTHROPIC_MODEL
            self.beta_features = COMPUTER_USE_BETA
            self.api_type = "anthropic"
        elif self.provider == "google":
            from openai import OpenAI
            # Use Google's OpenAI-compatible endpoint directly
            api_key = os.getenv("GOOGLE_API_KEY")
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
            self.client = OpenAI(api_key=api_key, base_url=base_url)
            self.model = model or "models/gemini-2.0-flash"
            self.api_type = "openai"
        elif self.provider == "openrouter":
            from openai import OpenAI
            api_key = os.getenv("OPENROUTER_API_KEY")
            base_url = "https://openrouter.ai/api/v1"
            self.client = OpenAI(api_key=api_key, base_url=base_url)
            self.model = model or "deepseek/deepseek-r1:free"
            self.api_type = "openai"
        elif self.provider in ["openai", "copilot"]:
            from openai import OpenAI
            # Legacy/Generic OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL")
            self.client = OpenAI(api_key=api_key, base_url=base_url)
            self.model = model or "gpt-4o"
            self.api_type = "openai"
        elif self.provider == "ollama":
            self.endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
            self.model = model or "qwen3:8b"
            self.api_type = "ollama"
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        self.messages: List[Dict[str, Any]] = []

        # Inject system prompt for non-Anthropic providers to mimic "Computer Use" behavior
        if self.provider != "anthropic":
            system_prompt = """You are a capable agent with the ability to use a computer. 
You can view the screen, move the mouse, click, type, and run terminal commands.

**Available Tools:**
1. `computer`:
   - `action`: "screenshot", "mouse_move", "left_click", "right_click", "double_click", "type", "key", "wait".
   - `coordinate`: [x, y] coordinates (integers). Top-left is (0,0). Required for movement.
   - `text`: String to type or key sequence.
2. `bash`: Execute shell commands.

**Guidelines:**
- START by taking a screenshot to see the screen.
- Analyze the screenshot to determine the exact [x, y] coordinates of UI elements.
- ACT by calling the `computer` tool.
- If you need to verify an action, take another screenshot.
- You are interacting with a Windows machine.

**Input Format:**
- You will receive screenshots as images in the user messages.
"""
            self.messages.append({"role": "system", "content": system_prompt})
        
    def get_tool_definitions(self):
        """Standard tools for Anthropic/Ollama/OpenAI"""
        # Anthropic 'computer' tool is special
        if self.provider == "anthropic":
            return [
                self.computer_tool.get_definition(),
                self.bash_tool.get_definition()
            ]
        else:
            # For OpenAI/Ollama, we convert the computer tool to a standard function call format
            # and may need to provide it as a list of many small tools or a single dispatch tool.
            # Simplified for now: standard tool definitions.
            return [
                {
                    "type": "function",
                    "function": {
                        "name": "computer",
                        "description": "Perform computer actions: screenshot, mouse_move, left_click, right_click, double_click, type, key, wait.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["screenshot", "mouse_move", "left_click", "right_click", "double_click", "type", "key", "wait"]},
                                "coordinate": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2},
                                "text": {"type": "string"}
                            },
                            "required": ["action"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "bash",
                        "description": "Run a local shell command.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "command": {"type": "string"}
                            },
                            "required": ["command"]
                        }
                    }
                }
            ]

    def run(self, prompt: str):
        print(f"[{self.provider}] Moltbot 시작: {prompt}")
        for response_text in self.get_response(prompt):
            if not response_text.startswith("[Tool"):
                print(f"\nAssistant: {response_text}")

    def get_response(self, prompt: str):
        """Generator that yields text responses, including tool results if needed."""
        self.messages.append({"role": "user", "content": prompt})
        
        while True:
            # print("Thinking...")
            response = None
            if self.api_type == "anthropic":
                response = self._call_anthropic()
            elif self.api_type == "openai":
                response = self._call_openai()
            elif self.api_type == "ollama":
                response = self._call_ollama()
            
            if response is None or response.get("stop") is None:
                yield f"Error: No valid response from model ({self.provider})."
                break
                
            if response["stop"]:
                yield response['text']
                break
            
            if response['text']:
                yield response['text']
                
            # Handle tool calls
            tool_results = []
            for tool_call in response["tool_calls"]:
                name = tool_call["name"]
                args = tool_call["args"]
                call_id = tool_call["id"]
                
                # yield f"[Tool execution: {name}]"
                try:
                    if name == "computer":
                        result = self.computer_tool.execute(args)
                    elif name == "bash":
                        result = self.bash_tool.execute(args)
                    else:
                        result = f"Error: Unknown tool {name}"
                except Exception as e:
                    result = f"Error: {str(e)}"
                
                tool_results.append({
                    "id": call_id,
                    "name": name,
                    "content": result
                })
            
            self._append_tool_results(response["assistant_msg"], tool_results)

    def _call_anthropic(self):
        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=4096,
                tools=self.get_tool_definitions(),
                messages=self.messages,
                betas=self.beta_features,
                timeout=120.0  # 2 minute timeout
            )
        except Exception as e:
            print(f"[anthropic] request failed: {e}")
            raise
        
        tool_calls = []
        text = ""
        for block in response.content:
            if block.type == "text":
                text += block.text
            elif block.type == "tool_use":
                tool_calls.append({"id": block.id, "name": block.name, "args": block.input})
                
        return {
            "stop": response.stop_reason == "end_turn",
            "text": text,
            "tool_calls": tool_calls,
            "assistant_msg": {"role": "assistant", "content": response.content}
        }

    def _call_openai(self):
        # Convert messages to OpenAI format if needed (e.g. image content)
        # For simplicity, assuming text only or standard OAI image blocks
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.get_tool_definitions(),
            tool_choice="auto"
        )
        
        msg = response.choices[0].message
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({"id": tc.id, "name": tc.function.name, "args": json.loads(tc.function.arguments)})
        
        return {
            "stop": not tool_calls,
            "text": msg.content or "",
            "tool_calls": tool_calls,
            "assistant_msg": msg.model_dump()
        }

    def _call_ollama(self):
        # Ollama tools API is still evolving, using a generic POST
        # For Qwen2.5-VL, we need to ensure images are passed correctly
        payload = {
            "model": self.model,
            "messages": self.messages,
            "tools": self.get_tool_definitions(),
            "stream": False
        }
        res = requests.post(f"{self.endpoint}/api/chat", json=payload).json()
        msg = res["message"]
        
        tool_calls = []
        if "tool_calls" in msg:
            for tc in msg["tool_calls"]:
                tool_calls.append({"id": "ollama_" + str(time.time()), "name": tc["function"]["name"], "args": tc["function"]["arguments"]})
        
        return {
            "stop": not tool_calls,
            "text": msg["content"] or "",
            "tool_calls": tool_calls,
            "assistant_msg": msg
        }

    def _append_tool_results(self, assistant_msg, results):
        self.messages.append(assistant_msg)
        
        if self.provider == "anthropic":
            content = []
            for r in results:
                formatted_content = r["content"]
                if isinstance(formatted_content, dict) and "type" in formatted_content:
                    formatted_content = [formatted_content]
                content.append({
                    "type": "tool_result",
                    "tool_use_id": r["id"],
                    "content": formatted_content
                })
            self.messages.append({"role": "user", "content": content})
        else:
            # OpenAI / Ollama standard tool result format
            for r in results:
                content = r["content"]
                image_block = None
                
                if isinstance(content, dict) and "type" in content and content["type"] == "image":
                    # Extract image data
                    image_data = content["source"]["data"]
                    media_type = content["source"]["media_type"]
                    
                    # Tool message must have a string content
                    content = "Screenshot captured. See the following user message for the image."
                    
                    # Prepare image block for the follow-up user message
                    image_block = {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_data}"
                        }
                    }
                
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": r["id"],
                    "name": r["name"],
                    "content": str(content)
                })
                
                if image_block:
                    # Inject image as the most recent user context for the model to "see"
                    self.messages.append({
                        "role": "user",
                        "content": [image_block]
                    })

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--provider", default=os.getenv("PROVIDER", "anthropic"))
    parser.add_argument("--model", default=os.getenv("MODEL"))
    args = parser.parse_args()
    
    if args.provider == "auto":
        router = ModelRouter()
        decision = router.route(args.prompt)
        print(f"[Router] Decision: {decision['provider']} ({decision['model']})")
        agent = MoltbotAgent(provider=decision['provider'], model=decision['model'])
    else:
        agent = MoltbotAgent(provider=args.provider, model=args.model)
        
    agent.run(args.prompt)
