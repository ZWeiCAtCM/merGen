# api/views.py
import os
import json
import tempfile
import asyncio
import traceback

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from llama.agent import InterioAgent
from llama.utils import data_url_from_image

# 缓存初始化后的 agent 实例
agent_instance = None
# 全局 session_id，所有 API 都共享
global_session_id = None

async def get_agent():
    global agent_instance
    if agent_instance is None:
        document_dir = os.path.join(settings.BASE_DIR, 'resources', 'documents')
        image_dir = os.path.join(settings.BASE_DIR, 'resources', 'images')
        agent_instance = InterioAgent(document_dir, image_dir)
        await agent_instance.initialize(settings.LLAMA_STACK_HOST, settings.LLAMA_STACK_PORT)
    return agent_instance

async def get_global_session(agent):
    global global_session_id
    if not global_session_id:
        global_session_id = await agent.create_chat_session()
    return global_session_id

@csrf_exempt
@require_http_methods(["POST"])
async def chat_view(request):
    """
    聊天接口，支持文本和图片输入，所有请求共用同一个全局会话。
    如果请求以 multipart/form-data 方式发送：
      - 文本消息在字段 "message"
      - 图片文件在字段 "image"（可选）
    如果请求以 JSON 格式发送，则仅处理 "message" 字段（如有图片建议使用 form-data）。
    
    响应示例：
    {
       "session_id": "<全局会话ID>",
       "reply": "<agent 回复的文本>"
    }
    """
    try:
        # 如果有文件上传，则认为是 multipart/form-data
        if request.FILES:
            user_message = request.POST.get('message', '')
            image_file = request.FILES.get('image')
        else:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            image_file = None
    except Exception:
        return JsonResponse({'error': 'Invalid input'}, status=400)
    
    if not user_message and not image_file:
        return JsonResponse({'error': 'No message or image provided'}, status=400)
    
    # 构造消息内容
    content = []
    if image_file:
        suffix = os.path.splitext(image_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in image_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        try:
            data_url = data_url_from_image(tmp_path)
        finally:
            os.remove(tmp_path)
        content.append({"type": "image", "image": {"url": {"uri": data_url}}})
    
    if user_message:
        content.append({"type": "text", "text": user_message})
    
    # 获取 agent 实例和全局会话
    agent = await get_agent()
    global global_session_id
    if not global_session_id:
        global_session_id = await agent.create_chat_session()
    session_id = global_session_id

    # 构造发送给 agent 的消息字典
    message = {"role": "user", "content": content}
    
    try:
        reply = await agent.chat_turn(session_id, message)
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'session_id': session_id, 'reply': reply})

@csrf_exempt
@require_http_methods(["POST"])
async def list_items_view(request):
    image_file = request.FILES.get('image')
    if not image_file:
        return JsonResponse({'error': 'No image provided'}, status=400)
    
    suffix = os.path.splitext(image_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        for chunk in image_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        agent = await get_agent()
        # 使用全局 session
        session_id = await get_global_session(agent)
        # 修改 list_items 方法，使其支持传入 session_id
        result = await agent.list_items(tmp_path, session_id=session_id)
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
    finally:
        os.remove(tmp_path)
    return JsonResponse(result)

@csrf_exempt
@require_http_methods(["POST"])
async def suggest_alternatives_view(request):
    image_file = request.FILES.get('image')
    item = request.POST.get('item')
    if not image_file or not item:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    suffix = os.path.splitext(image_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        for chunk in image_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        agent = await get_agent()
        session_id = await get_global_session(agent)
        alternatives = await agent.suggest_alternatives(tmp_path, item, session_id=session_id)
    except Exception as e:
        error_details = traceback.format_exc()
        print(error_details)  # 打印到控制台
        # 在开发阶段返回详细错误信息
        return JsonResponse({'error': error_details}, status=500)
    finally:
        os.remove(tmp_path)
    return JsonResponse({'alternatives': alternatives})

@csrf_exempt
@require_http_methods(["POST"])
async def retrieve_images_view(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    description = data.get('description')
    if not description:
        return JsonResponse({'error': 'No description provided'}, status=400)

    try:
        agent = await get_agent()
        session_id = await get_global_session(agent)
        results = await agent.retrieve_images(description, session_id=session_id)
    except Exception as e:
        error_details = traceback.format_exc()
        print(error_details)  # 打印到控制台
        # 在开发阶段返回详细错误信息
        return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse(results, safe=False)
