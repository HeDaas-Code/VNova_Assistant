# -*- coding: utf-8 -*-
"""
VNova Assistant - 视觉小说制作助手
Ollama API通信接口模块
"""

import ollama
import json
import uuid
import os

class OllamaClient:
    """A client to interact with a local Ollama instance."""
    def __init__(self, config_path='config.json'):
        config = self._load_config(config_path)
        self.host = config.get('ollama_host', 'http://localhost:11434') # Store host
        self.model = config.get('default_model', 'llama3')
        self.client = ollama.Client(host=self.host) # Use stored host for init
        self._check_connection()

    def _load_config(self, config_path):
        """Loads configuration from a JSON file."""
        # Construct absolute path relative to the script's location might be safer
        # For simplicity now, assume config.json is in the root directory where main.py runs
        # A more robust approach would involve finding the project root
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Error decoding {config_path}. Using default settings.")
            except Exception as e:
                print(f"Warning: Could not load {config_path}: {e}. Using default settings.")
        else:
            print(f"Warning: Configuration file {config_path} not found. Using default settings.")
        return {} # Return empty dict if file not found or error

    def _check_connection(self):
        """Checks if the connection to the Ollama server is successful."""
        try:
            # A lightweight request to check connectivity
            self.client.list()
            print(f"Successfully connected to Ollama at {self.host}") # Use stored host
        except Exception as e:
            print(f"Error connecting to Ollama at {self.host}: {e}") # Use stored host
            # Depending on the application design, might raise an exception
            # or set a status flag.
            raise ConnectionError(f"Failed to connect to Ollama: {e}")

    def generate_story_segment(self, prompt, character_info=None, world_info=None):
        """Generates a story segment based on the prompt and context."""
        request_id = str(uuid.uuid4())
        full_prompt = f"你是VNova Assistant(视觉小说制作助手)的剧情写作引擎。请根据以下信息生成一段剧情文本。"
        if character_info:
            full_prompt += f"\n## 人物设定:\n{json.dumps(character_info, ensure_ascii=False, indent=2)}\n"
        if world_info:
            full_prompt += f"\n## 世界观设定:\n{json.dumps(world_info, ensure_ascii=False, indent=2)}\n"

        full_prompt += f"\n## 当前剧情提示:\n{prompt}\n"
        full_prompt += "\n请严格按照以下 JSON 格式返回生成的剧情文本，只包含必要的剧情内容，不要添加额外的解释或评论：\n"
        full_prompt += "```json\n{\n  \"story_text\": \"<生成的剧情文本>\",\n  \"suggestions\": [\"<后续发展建议1>\", \"<后续发展建议2>\"] // 可选的后续发展建议\n}\n```"

        print(f"\n--- Sending Request (ID: {request_id}) to Ollama ---")
        print(f"Model: {self.model}")
        # print(f"Prompt:\n{full_prompt}") # Be careful logging full prompts if they contain sensitive info
        print("Prompt: [See details above]")
        print("--------------------------------------------------")

        try:
            response = self.client.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': full_prompt}],
                format='json' # Request JSON output directly if model supports it
            )

            print(f"\n--- Received Response (ID: {request_id}) from Ollama ---")
            # print(f"Raw Response: {response}")

            if response and 'message' in response and 'content' in response['message']:
                content_str = response['message']['content']
                try:
                    # Attempt to parse the JSON content directly
                    parsed_content = json.loads(content_str)
                    print(f"Parsed Content: {json.dumps(parsed_content, ensure_ascii=False, indent=2)}")
                    # Basic validation
                    if isinstance(parsed_content, dict) and 'story_text' in parsed_content:
                         return request_id, parsed_content
                    else:
                        print("Error: Response JSON does not contain 'story_text' key.")
                        return request_id, {"error": "Invalid JSON structure received", "raw_content": content_str}
                except json.JSONDecodeError as json_err:
                    print(f"Error: Failed to parse Ollama response as JSON: {json_err}")
                    print(f"Raw Content causing error: {content_str}")
                    # Attempt to extract from markdown code block if parsing failed
                    if '```json' in content_str:
                        try:
                            json_part = content_str.split('```json')[1].split('```')[0].strip()
                            parsed_content = json.loads(json_part)
                            print(f"Parsed Content (from markdown): {json.dumps(parsed_content, ensure_ascii=False, indent=2)}")
                            if isinstance(parsed_content, dict) and 'story_text' in parsed_content:
                                return request_id, parsed_content
                            else:
                                print("Error: Extracted JSON does not contain 'story_text' key.")
                                return request_id, {"error": "Invalid extracted JSON structure", "raw_content": content_str}
                        except (IndexError, json.JSONDecodeError) as inner_err:
                            print(f"Error: Failed to extract/parse JSON from markdown block: {inner_err}")
                            return request_id, {"error": "Failed to parse JSON response", "raw_content": content_str}
                    else:
                         return request_id, {"error": "Non-JSON response received", "raw_content": content_str}
            else:
                print("Error: Unexpected response structure from Ollama.")
                return request_id, {"error": "Unexpected response structure", "raw_response": response}

        except Exception as e:
            print(f"Error during Ollama API call: {e}")
            return request_id, {"error": f"API call failed: {e}"}

# Example Usage (for testing)
if __name__ == '__main__':
    # Assume config.json is in the parent directory relative to this script for testing
    # In the actual application, the path might be relative to main.py
    config_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
    try:
        # Pass the relative path to the config file
        client = OllamaClient(config_path=config_file_path)

        # Example prompt
        prompt = "主角在一个雨夜进入了一家古老的咖啡馆。"
        char_info = {"name": "雨宫优子", "description": "神秘的女高中生，似乎隐藏着秘密。"}
        world_info = {"setting": "现代都市，但流传着一些都市传说。"}

        req_id, result = client.generate_story_segment(prompt, char_info, world_info)

        print(f"\n--- Final Result (Request ID: {req_id}) ---")
        if 'error' in result:
            print(f"Generation failed: {result['error']}")
            if 'raw_content' in result:
                print(f"Raw Content: {result['raw_content']}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

    except ConnectionError as ce:
        print(f"Connection Error: {ce}")
    except Exception as ex:
        print(f"An unexpected error occurred: {ex}")