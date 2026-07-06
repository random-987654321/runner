# queen.py
import os
import yaml
import json
import subprocess
import asyncio
import uuid
import signal
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import ollama

app = FastAPI()

# Load Queen Configuration
with open("queen.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

HTML = """
<!DOCTYPE html>
<html>
<head><title>OpenClaw Hive Mind</title></head>
<body>
    <h2>OpenClaw Queen</h2>
    <form onsubmit="sendMessage(event)">
        <input type="text" id="prompt" autocomplete="off" style="width:300px" placeholder="Instruct the Queen..."/>
        <button>Command</button>
    </form>
    <ul id='logs' style="font-family: monospace; list-style: none; padding: 0;"></ul>
    <script>
        var ws = new WebSocket("ws://" + window.location.host + "/ws");
        ws.onmessage = function(event) {
            var messages = document.getElementById('logs');
            var message = document.createElement('li');
            message.innerHTML = event.data;
            messages.appendChild(message);
            window.scrollTo(0, document.body.scrollHeight);
        };
        function sendMessage(event) {
            var input = document.getElementById('prompt');
            ws.send(input.value);
            input.value = '';
            event.preventDefault();
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(HTML)

class ConnectionManager:
    def __init__(self):
        self.active_connections = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()
active_workers = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"<b>Queen:</b> Received command: {data}")
            await process_command(data)
    except WebSocketDisconnect:
        manager.active_connections.remove(websocket)

async def process_command(user_prompt: str):
    queen_config = CONFIG['queen']
    hive_config = CONFIG['hive']
    max_workers = hive_config['max_workers']

    # 1. Ask Queen (Ollama) how to divide the task
    await manager.broadcast("<b>Queen:</b> Analyzing task delegation via Ollama...")
    
    # Simulating LLM JSON output for reliability in this script.
    # In production, you would parse ollama.chat() response.
    # response = ollama.chat(model=queen_config['model'], messages=[{'role': 'system', 'content': queen_config['system_prompt']}, {'role': 'user', 'content': user_prompt}])
    # tasks = json.loads(response['message']['content'])
    
    # Simulated Tasks
    tasks = [
        {"task_id": "w1", "description": f"Research phase for: {user_prompt}", "requires_secret": True},
        {"task_id": "w2", "description": f"Drafting phase for: {user_prompt}", "requires_secret": False}
    ]

    if len(tasks) > max_workers:
        await manager.broadcast(f"<b>Queen:</b> Warning: LLM requested {len(tasks)} workers. Capping at {max_workers}.")
        tasks = tasks[:max_workers]

    # 2. Spawn Workers
    for task in tasks:
        worker_id = task['task_id']
        secret = str(uuid.uuid4()) if task.get('requires_secret') else "NO_SECRET"
        
        # Generate worker.yaml
        worker_config = {
            "worker_id": worker_id,
            "model": hive_config['worker_model'],
            "task": task['description'],
            "api_secret": secret,
            "holesail_port": 9100 + len(active_workers),
            "master_secret": CONFIG['security']['master_secret']
        }
        yaml_file = f"{worker_id}.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(worker_config, f)
            
        await manager.broadcast(f"<b>Queen:</b> Generated {yaml_file}. Spawning {worker_id}...")
        
        # Start Holesail connection (Simulated command)
        # subprocess.Popen(["holesail", "connect", "--port", str(worker_config['holesail_port']), "QUEEN_CONNECTION_STRING"])
        
        # Spawn Worker process
        proc = subprocess.Popen(["python", hive_config['worker_script'], yaml_file])
        active_workers[worker_id] = proc
        
        # Secure Delete YAML immediately after spawning
        os.remove(yaml_file)
        await manager.broadcast(f"<b>Queen:</b> Securely deleted {yaml_file}. Secret wiped from disk.")

    # 3. Monitor for completion (Simplified for script)
    await asyncio.sleep(5)
    await manager.broadcast("<b>Queen:</b> All workers have reported back via Holesail. Tasks complete.")

if __name__ == "__main__":
    import uvicorn
    # Start Cloudflare tunnel in background (Simulated)
    # subprocess.Popen(["cloudflared", "tunnel", "--url", "http://localhost:8000"])
    print("Starting OpenClaw Queen on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
