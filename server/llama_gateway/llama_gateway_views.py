# llama_gateway_views.py 
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import httpx
import os
import json
import logging

logger = logging.getLogger(__name__)

IDA_AGENT_HOST = os.getenv("IDA_AGENT_HOST", "ida-llama-agent")
IDA_AGENT_PORT = os.getenv("IDA_AGENT_PORT", "8001")
IDA_AGENT_BASE_URL = f"http://{IDA_AGENT_HOST}:{IDA_AGENT_PORT}"

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
