from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import base64
import time
import json
from dotenv import load_dotenv
import os
import asyncio
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

UNITY_WEBSOCKET_GROUP = "unity_updates"

# 加载 .env 变量
load_dotenv()

# ✅ 尝试获取 ngrok URL，最多等待 30 秒
def get_ngrok_url(max_retries=10, delay=3):
    """等待 ngrok 启动，最多重试 10 次，每次间隔 3 秒"""
    for _ in range(max_retries):
        try:
            response = requests.get("http://ngrok:4040/api/tunnels")  # 🔹 这里的 `ngrok` 是 `Docker Compose` 里的 `ngrok` 服务名
            tunnels = response.json().get("tunnels", [])
            for tunnel in tunnels:
                if tunnel["proto"] == "https":
                    return tunnel["public_url"]
        except requests.exceptions.RequestException:
            print("⏳ ngrok 还没启动，等待中...")
        time.sleep(delay)
    print("❌ 30s 内未能获取 ngrok URL，使用默认值")
    return None

# ✅ 自动获取 ngrok URL
NGROK_URL = get_ngrok_url()
if NGROK_URL:
    print(f"✅ 成功获取 ngrok URL: {NGROK_URL}")
    WEBHOOK_URL = NGROK_URL + "/api/pano-gen/webhook/"
else:
    print("❌ 无法获取 ngrok URL，Webhook 可能无法正常工作！")
    WEBHOOK_URL = None

# Blockade Labs API Key
BLOCKADE_LABS_API_KEY = os.getenv("BLOCKADE_LABS_API_KEY")
BLOCKADE_LABS_ENDPOINT = os.getenv("BLOCKADE_LABS_ENDPOINT")
# Blockade Labs API Key
SEGMIND_API_KEY = os.getenv("SEGMIND_API_KEY")
SEGMIND_ENDPOINT = os.getenv("SEGMIND_ENDPOINT")

UNITY_ASSETS_PATH = "/app/Material"

@csrf_exempt
def generate_skybox_with_image(request):
    if request.method == "POST":
        try:
            # ✅ 解析 JSON 格式的请求
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                print("Invalid JSON format")
                return JsonResponse({"error": "Invalid JSON format"}, status=400)

            prompt = data.get("prompt", "A beautiful futuristic bedroom")  # 默认 prompt
            version = data.get("version", "current")  # 默认 current.jpeg
            skybox_style_id = 147  # 你想要使用的 Skybox 风格 ID

            # 读取 `new.jpg` 并转为 Base64
            new_image_path = os.path.join(UNITY_ASSETS_PATH, version + ".jpg")
            if not os.path.exists(new_image_path):
                print(f"{new_image_path} not found inside Docker")
                return JsonResponse({"error": f"{new_image_path} not found inside Docker"}, status=400)
            
            with open(new_image_path, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode("utf-8")

            # 发送请求到 Blockade Labs API
            payload = {
                "skybox_style_id": skybox_style_id,
                "prompt": prompt,
                "control_image": base64_image,
                "control_model": "remix",
                "webhook_url": WEBHOOK_URL  # Blockade Labs 生成完成后回调
            }
            headers = {"x-api-key": BLOCKADE_LABS_API_KEY, "Content-Type": "application/json"}
            print("🔹 Sending request to Skybox AI with prompt:", prompt)
            print("🔹 Skybox AI will send request to this WEBHOOK_URL upon finish:", WEBHOOK_URL)
            response = requests.post(BLOCKADE_LABS_ENDPOINT, json=payload, headers=headers)

            # ✅ 添加 debug 日志
            print("🔹 API Response Status:", response.status_code)
            print("🔹 API Response Text:", response.text)  # 确保 API 实际返回了 JSON
            try:
                return JsonResponse(response.json(), safe=False)  # 解析 JSON
            except requests.exceptions.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON response from Blockade Labs API", "response_text": response.text}, status=500)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)

@csrf_exempt
def skybox_webhook(request):
    if request.method == "POST":
        try:
            # 解析 JSON 数据
            data = json.loads(request.body)
            status = data.get("status", "")
            file_url = data.get("file_url", "")

            # ✅ 处理 Skybox 生成过程中的状态更新
            if status in ["dispatched", "processing"]:
                print(f"🔄 Skybox 生成状态: {status}, 等待完成...")
                return JsonResponse({"message": f"Status updated: {status}"}, status=202)

            # ✅ 只有在 status = "complete" 时才处理图片
            if status == "complete":
                if not file_url:
                    return JsonResponse({"error": "No file URL received"}, status=400)

                # **✅ 备份 `current.jpg` 到 `previous.jpg`**
                unity_assets_path = "/app/Material"
                new_image_path = os.path.join(unity_assets_path, "current.jpg")
                old_image_path = os.path.join(unity_assets_path, "previous.jpg")

                if os.path.exists(new_image_path):
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                    os.rename(new_image_path, old_image_path)

                # **✅ 下载新生成的 Skybox 并保存为 `current.jpg`**
                response = requests.get(file_url)
                if response.status_code == 200:
                    with open(new_image_path, "wb") as file:
                        file.write(response.content)

                    # **✅ 发送 WebSocket 通知给 Unity**
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        UNITY_WEBSOCKET_GROUP,
                        {
                            "type": "send_update",
                            "message": "Skybox updated"
                        }
                    )

                    print("✅ Skybox 更新完成，通知 Unity")
                    return JsonResponse({"message": "Skybox updated successfully"}, status=200)
                else:
                    return JsonResponse({"error": "Failed to download new skybox"}, status=500)

            # 🚨 如果 `status` 不是 "dispatched", "processing", "complete" 之外的其他情况
            return JsonResponse({"error": f"Unexpected status: {status}"}, status=400)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
def generate_from_skybox(request):
    return JsonResponse({"panoramic": "skybox-panoramic"})

@csrf_exempt
def doodle_from_skybox(request):
    return JsonResponse({"doodle": "skybox-doodle"})

@csrf_exempt
def inpainting_from_segmind(request):
    if request.method == "POST":
        try:
            # ✅ 解析 JSON 格式的请求
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                print("Invalid JSON format")
                return JsonResponse({"error": "Invalid JSON format"}, status=400)

            prompt = data.get("prompt", "A beautiful futuristic bedroom")  # 默认 prompt
            version = "current"  # 默认 current.jpeg

            # 读取 `current.jpg` 并转为 Base64
            image_path = os.path.join(UNITY_ASSETS_PATH, version + ".jpg")
            if not os.path.exists(image_path):
                print(f"{image_path} not found inside Docker")
                return JsonResponse({"error": f"{image_path} not found inside Docker"}, status=400)
            
            with open(image_path, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode("utf-8")
            
            # 读取 `mask.jpg` 并转为 Base64
            mask_path = os.path.join(UNITY_ASSETS_PATH, "mask.png")
            if not os.path.exists(mask_path):
                print(f"{mask_path} not found inside Docker")
                return JsonResponse({"error": f"{mask_path} not found inside Docker"}, status=400)
            
            with open(mask_path, "rb") as mask_file:
                base64_mask = base64.b64encode(mask_file.read()).decode("utf-8")

            # 发送请求到 segmind API
            payload = {
            "base64": False,
            "guidance_scale": 3.5,
            "image": base64_image,
            "image_format": "jpeg",
            "mask": base64_mask,
            "negative_prompt": "bad quality, painting, blur",
            "num_inference_steps": 25,
            "prompt": prompt,
            "quality": 95,
            "sampler": "euler",
            "samples": 1,
            "scheduler": "simple",
            "seed": 12467,
            "strength": 0.9
            }
            headers = {"x-api-key": SEGMIND_API_KEY, "Content-Type": "application/json"}
            print("🔹 Sending request to segmind with prompt:", prompt)
            response = requests.post(SEGMIND_ENDPOINT, json=payload, headers=headers)
            print(response.content)  # The response is the generated image

            # **✅ 备份 `current.jpg` 到 `previous.jpg`**
            unity_assets_path = "/app/Material"
            new_image_path = os.path.join(unity_assets_path, "current.jpg")
            old_image_path = os.path.join(unity_assets_path, "previous.jpg")

            if os.path.exists(new_image_path):
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
                os.rename(new_image_path, old_image_path)

            # **✅ 下载新生成的 Skybox 并保存为 `current.jpg`**
  
            if response.status_code == 200:
                with open(new_image_path, "wb") as file:
                    file.write(response.content)

                # **✅ 发送 WebSocket 通知给 Unity**
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    UNITY_WEBSOCKET_GROUP,
                    {
                        "type": "send_update",
                        "message": "Skybox updated"
                    }
                )

                print("✅ Skybox 更新完成，通知 Unity")
                return JsonResponse({"message": "Skybox updated successfully"}, status=200)
            else:
                return JsonResponse({"error": "Inpainting failed"}, status=500)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)