import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI()
TARGET_URL = "http://127.0.0.1:9119"

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, path: str):
    async with httpx.AsyncClient(base_url=TARGET_URL, timeout=60.0) as client:
        # 1. Capture original request data
        body = await request.body()
        
        # 2. Filter headers to prevent 500 errors (remove connection-specific headers)
        headers = {k: v for k, v in request.headers.items() 
                   if k.lower() not in ["host", "connection", "accept-encoding"]}
        headers["Host"] = "127.0.0.1:9119"
        
        try:
            # 3. Stream the request to the target
            req = client.build_request(
                request.method,
                path,
                params=request.query_params,
                headers=headers,
                content=body
            )
            response = await client.send(req, stream=True)
            return StreamingResponse(
                response.aiter_raw(),
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except Exception as e:
            return {"error": str(e)}, 500

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9120)
