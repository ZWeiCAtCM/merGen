# llama_gateway_views.py 
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import httpx
import os
import json
import logging
import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

IDA_AGENT_HOST = os.getenv("IDA_AGENT_HOST", "ida-llama-agent")
IDA_AGENT_PORT = os.getenv("IDA_AGENT_PORT", "8001")
IDA_AGENT_BASE_URL = f"http://{IDA_AGENT_HOST}:{IDA_AGENT_PORT}"

# 创建日志文件
timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_DIR = Path("/app/logs")  # 容器内路径，会映射到你本地 logs 文件夹
LOG_DIR.mkdir(parents=True, exist_ok=True)
CHAT_LOG_PATH = LOG_DIR / f"llama_chat_log_{timestamp_str}.txt"

async def proxy_request(endpoint, request):
    url = f"{IDA_AGENT_BASE_URL}{endpoint}"
    headers = dict(request.headers)
    headers.pop("host", None)
    timeout = httpx.Timeout(60.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        if "multipart/form-data" in headers.get("content-type", ""):
            response = await client.post(url, data=request.POST, files=request.FILES, headers=headers)
        else:
            response = await client.post(url, content=request.body, headers=headers)
    try:
        content = response.json()
    except Exception:
        content = response.text

    # ✅ 写入日志文件
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_input = request.body.decode("utf-8", errors="ignore")
        ai_response = json.dumps(content, ensure_ascii=False, indent=2) if isinstance(content, dict) else str(content)

        log_entry = (
            f"\n=== Proxy Call at {timestamp} ===\n"
            f"[Endpoint] {endpoint}\n"
            f"[User Input]\n{user_input}\n\n"
            f"[Response]\n{ai_response}\n"
            f"====================================\n"
        )

        with open(CHAT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        logger.warning(f"Failed to log proxy_request to {endpoint}: {e}")

    # return response
    return content, response.status_code

async def chat_proxy(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Method Not Allowed'}, status=405)
    print("Sending request:", request)
    content, status_code = await proxy_request("/api/chat/", request)
    print("Response content:", content)
    response = JsonResponse(content, status=status_code, safe=False)
    return response

async def list_items_proxy(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Method Not Allowed'}, status=405)
    content, status_code = await proxy_request("/api/list_items/", request)
    return JsonResponse(content, status=status_code, safe=False)

async def suggest_alternatives_proxy(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Method Not Allowed'}, status=405)
    content, status_code = await proxy_request("/api/suggest_alternatives/", request)
    return JsonResponse(content, status=status_code, safe=False)

async def retrieve_images_proxy(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Method Not Allowed'}, status=405)
    content, status_code = await proxy_request("/api/retrieve_images/", request)
    return JsonResponse(content, status=status_code, safe=False)
