import os
import requests

# 参数配置
KEYWORD = "table"
API_URL = f"https://zylalabs.com/api/2226/ikea+product+details+api/2075/search+by+keyword?keyword={KEYWORD}"
HEADERS = {
    "Authorization": "Bearer 7597|Le763utg9WEEHkLFpmb5J9LTolDVoDDzIAGxHD5p"
}

# 当前脚本路径为 resources/
current_dir = os.path.dirname(os.path.abspath(__file__))
image_folder = os.path.join(current_dir, "images", KEYWORD)
os.makedirs(image_folder, exist_ok=True)

# 请求数据
response = requests.get(API_URL, headers=HEADERS)
data = response.json()

# 下载与保存
for idx, product in enumerate(data, start=1):
    img_name = f"{idx:03}.jpg"
    txt_name = f"{idx:03}.txt"
    img_path = os.path.join(image_folder, img_name)
    txt_path = os.path.join(current_dir, txt_name)

    # 下载图片
    image_url = product.get("image")
    try:
        img_data = requests.get(image_url).content
        with open(img_path, "wb") as img_file:
            img_file.write(img_data)
        print(f"✅ 图片下载成功: {img_name}")
    except Exception as e:
        print(f"❌ 图片下载失败: {image_url} - {e}")
        continue

    # 写入 txt 文件
    image_alt = product.get("imageAlt", "No description available.")
    price = product.get("price", {}).get("currentPrice", "N/A")

    with open(txt_path, "w", encoding="utf-8") as txt_file:
        txt_file.write(f"{image_alt}\n")
        txt_file.write(f"<price>{price}</price>\n")
        txt_file.write(f"<uri>{img_name}</uri>\n")

    print(f"📄 文本已生成: {txt_name}")

print("\n🎉 所有图片和对应的描述文件处理完成！")
