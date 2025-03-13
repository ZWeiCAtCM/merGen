from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import base64
import time
import json
from dotenv import load_dotenv
import os

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
BLOCKADE_API_KEY = os.getenv("BLOCKADE_LABS_API_KEY")
BLOCKADE_API_URL = os.getenv("BLOCKADE_LABS_ENDPOINT")
UNITY_ASSETS_PATH = "/app/Material"

@csrf_exempt
def generate_skybox_with_image(request):
    if request.method == "POST":
        try:
            # ✅ 解析 JSON 格式的请求
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON format"}, status=400)

            prompt = data.get("prompt", "A beautiful futuristic bedroom")  # 默认 prompt
            skybox_style_id = 35  # 你想要使用的 Skybox 风格 ID

            # 读取 `new.jpg` 并转为 Base64
            new_image_path = os.path.join(UNITY_ASSETS_PATH, "new.jpg")
            if not os.path.exists(new_image_path):
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
            headers = {"x-api-key": BLOCKADE_API_KEY, "Content-Type": "application/json"}
            print("🔹 Sending request to Skybox AI with prompt:", prompt)
            print("🔹 Skybox AI will send request to this WEBHOOK_URL upon finish:", WEBHOOK_URL)
            response = requests.post(BLOCKADE_API_URL, json=payload, headers=headers)

            # ✅ 添加 debug 日志
            print("🔹 API Response Status:", response.status_code)
            print("🔹 API Key:", BLOCKADE_API_KEY)
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
            data = json.loads(request.body)
            file_url = data.get("file_url")

            if not file_url:
                return JsonResponse({"error": "No file URL received"}, status=400)

            # **✅ 1️⃣ 先把 `new.jpg` 备份成 `old.jpg`**
            new_image_path = os.path.join(UNITY_ASSETS_PATH, "new.jpg")
            old_image_path = os.path.join(UNITY_ASSETS_PATH, "old.jpg")

            if os.path.exists(new_image_path):  # 如果 `new.jpg` 存在
                if os.path.exists(old_image_path):  # 如果 `old.jpg` 已经存在，先删除
                    os.remove(old_image_path)
                os.rename(new_image_path, old_image_path)  # 现在 `old.jpg` 是上一张 `new.jpg`

            # **✅ 2️⃣ 下载新生成的 Skybox 并保存为 `new.jpg`**
            response = requests.get(file_url)
            if response.status_code == 200:
                with open(new_image_path, "wb") as file:
                    file.write(response.content)

                return JsonResponse({"message": "Skybox updated successfully"}, status=200)
            else:
                return JsonResponse({"error": "Failed to download new skybox"}, status=500)

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
def inpainting_from_skybox(request):
    return JsonResponse({"inpainting": "skybox-inpainting"})