import sys
import threading
import http.server
import urllib.request
import urllib.error
import asyncio
import websockets

# Configuration targeted precisely at the nesquena/hermes-webui runtime default
TARGET_HTTP = "http://127.0.0.1:8000"
TARGET_WS = "ws://127.0.0.1:8000"
PROXY_PORT_HTTP = 19000
PROXY_PORT_WS = 19001

class CORSProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass 

    def handle_proxy(self):
        url = f"{TARGET_HTTP}{self.path}"
        req_headers = {k: v for k, v in self.headers.items() if k.lower() not in ['host', 'origin']}
        req_headers['Origin'] = TARGET_HTTP
        req_headers['Host'] = "127.0.0.1:8000"
        
        content_length = int(self.headers.get('Content-Length', 0))
        req_data = self.rfile.read(content_length) if content_length > 0 else None

        req = urllib.request.Request(url, data=req_data, headers=req_headers, method=self.command)
        try:
            with urllib.request.urlopen(req) as response:
                self.send_response(response.status)
                for key, val in response.getheaders():
                    if key.lower() not in ['content-encoding', 'transfer-encoding', 'connection']:
                        self.send_header(key, val)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(response.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(str(e).encode())

    do_GET = do_POST = do_PUT = do_DELETE = do_OPTIONS = handle_proxy

def run_http_proxy():
    server = http.server.HTTPServer(('127.0.0.1', PROXY_PORT_HTTP), CORSProxyHandler)
    server.serve_forever()

async def ws_forward(src, dst):
    try:
        async for message in src:
            await dst.send(message)
    except Exception:
        pass

async def ws_handler(client_ws):
    headers = {"Origin": TARGET_HTTP, "Host": "127.0.0.1:8000"}
    try:
        async with websockets.connect(TARGET_WS + client_ws.path, extra_headers=headers) as target_ws:
            await asyncio.gather(
                ws_forward(client_ws, target_ws),
                ws_forward(target_ws, client_ws)
            )
    except Exception:
        pass

async def main_ws():
    async with websockets.serve(ws_handler, "127.0.0.1", PROXY_PORT_WS):
        await asyncio.Future()

if __name__ == '__main__':
    threading.Thread(target=run_http_proxy, daemon=True).start()
    asyncio.run(main_ws())
