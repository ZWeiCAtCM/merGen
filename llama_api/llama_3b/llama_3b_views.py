from django.http import JsonResponse
from .llama_3b_service import generate_text
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def generate_text_view(request):
    if request.method == "POST":
        try:
            # 解析请求 body 中的 JSON 数据
            body = json.loads(request.body)
            prompt = body.get("prompt", "")

            # 检查 prompt 是否为空
            if not prompt:
                return JsonResponse({"error": "Prompt is required."}, status=400)

            # 生成文本
            generated_text = generate_text(prompt)
            return JsonResponse({"generated_text": generated_text})
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON."}, status=400)
    else:
        return JsonResponse({"error": "Invalid request method. Only POST is allowed."}, status=405)
