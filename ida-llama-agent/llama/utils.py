# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import asyncio
import base64
import mimetypes
import uuid
# from PIL import Image

# TODO: This should move into a common util as will be needed by all apps

# def data_url_from_compressed_image(file_path, quality=50, desired_width=1000, desired_height=500):
#     # 打开图片并进行压缩和可选缩放
#     with Image.open(file_path) as img:
#         if desired_width and desired_height:
#             img = img.resize((desired_width, desired_height))
#         buffer = io.BytesIO()
#         img.save(buffer, format="JPEG", quality=quality)
#         image_bytes = buffer.getvalue()
    
#     # 使用 mimetypes 猜测 MIME 类型，但这里强制输出为 JPEG 类型
#     mime_type = "image/jpeg"
#     encoded_string = base64.b64encode(image_bytes).decode("utf-8")
#     data_url = f"data:{mime_type};base64,{encoded_string}"
#     return data_url

def data_url_from_image(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        raise ValueError("Could not determine MIME type of the file")

    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

    data_url = f"data:{mime_type};base64,{encoded_string}"
    return data_url



async def create_single_turn(client, agent_config, messages, retries=1, delay=0):
    # for attempt in range(retries):
    try:
        response = client.agents.create(agent_config=agent_config)
        agent_id = response.agent_id
        await asyncio.sleep(delay)  # 等待，防止一下子超过速率
        response = client.agents.session.create(
            agent_id=agent_id,
            session_name=uuid.uuid4().hex,
        )
        session_id = response.session_id
        await asyncio.sleep(delay)  # 再等一下，防止一下子超过速率
        generator = client.agents.turn.create(
            agent_id=agent_id,
            session_id=session_id,
            messages=messages,
            stream=True,
        )

        for chunk in generator:
            if chunk is None or chunk.event is None:
                continue
            payload = chunk.event.payload
            if payload.event_type == "turn_complete":
                await asyncio.sleep(delay)  # 等一下，节流
                return payload.turn.output_message.content

    except Exception as e:
        if "429" in str(e) or "rate limit" in str(e).lower():
            print(f"Rate limit hit. Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
            delay *= 2
        else:
            raise
    # raise RuntimeError("Exceeded retry attempts for single turn creation")

