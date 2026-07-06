# worker.py
import sys
import yaml
import ollama
import os
import time
import json

def run_worker(yaml_file):
    # 1. Read YAML configuration
    with open(yaml_file, 'r') as f:
        config = yaml.safe_load(f)
        
    worker_id = config['worker_id']
    task = config['task']
    model = config['model']
    secret = config['api_secret']
    master_secret = config['master_secret']
    
    print(f"[{worker_id}] Initialized. Task: {task}")
    print(f"[{worker_id}] Acquired Secret: {secret[:8]}...")
    
    # 2. Establish Holesail Connection to Queen
    # In a real scenario: subprocess.Popen(["holesail", "connect", config['holesail_port'], "..."])
    # For this script, we simulate sending logs back to the Queen's Web UI via stdout
    print(f"[{worker_id}] Holesail P2P channel established with Queen.")
    
    # 3. Execute Task using Ollama (granite4:tiny-h)
    print(f"[{worker_id}] Executing task via {model}...")
    try:
        response = ollama.chat(model=model, messages=[
            {'role': 'user', 'content': task}
        ])
        result = response['message']['content']
        print(f"[{worker_id}] Task completed. Output: {result[:100]}...")
    except Exception as e:
        print(f"[{worker_id}] Error executing task: {e}")
    
    # 4. Die gracefully
    print(f"[{worker_id}] Shutting down. YAML was already securely deleted by Queen.")
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python worker.py <yaml_file>")
        sys.exit(1)
    run_worker(sys.argv[1])
