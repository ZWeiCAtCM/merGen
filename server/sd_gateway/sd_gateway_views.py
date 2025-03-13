from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv
import json
import os

project_root = Path(__file__).resolve().parent.parent.parent
dotenv_path = project_root / ".env"

load_dotenv(dotenv_path=dotenv_path)

SD_API_HOST = os.getenv("SD_API_HOST")
SD_API_PORT = os.getenv("SD_API_PORT")

URL = f"http://{SD_API_HOST}:{SD_API_PORT}"
@csrf_exempt
def txt2img_sd(request):
    if request.method == "POST":
        try:
            # 解析请求体中的 JSON 数据
            payload = json.loads(request.body)

            # 确保 URL 是正确的
            url = f'{URL}/sdapi/v1/txt2img'  # URL 需要定义为实际的 API 地址

            # 发送 POST 请求到外部 API
            response = requests.post(url=url, json=payload)
            
            # 检查请求的响应
            if response.status_code != 200:
                return JsonResponse({"error": "Failed to generate image"}, status=response.status_code)

            # 解析响应的 JSON 数据
            r = response.json()

            # 解码和保存图像
            image_data = r.get('images', [None])[0]
            if image_data:
                with open("sd_gateway/outputs/output.png", 'wb') as f:
                    f.write(base64.b64decode(image_data))
            else:
                return JsonResponse({"error": "No image data returned from the API"}, status=500)

            # 返回响应数据
            return JsonResponse(r, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)
@csrf_exempt
def img2img_sd(request):
    return JsonResponse({"doodle": "sd-doodle"})
@csrf_exempt
def inpainting_from_sd(request):
    return JsonResponse({"inpainting": "sd-inpainting"})