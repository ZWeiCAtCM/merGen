# llama/agent.py

import asyncio
import json
import textwrap
import uuid
from pathlib import Path
from typing import List

import logging

logger = logging.getLogger(__name__)

from .utils import (
    create_single_turn,
    data_url_from_image,
)

from llama_stack_client import LlamaStackClient
from llama_stack_client.types import QueryConfig
from llama_stack_client.types.agent_create_params import AgentConfig

from termcolor import cprint
import os
MODEL = os.getenv("TOGETHER_LLAMA_MODEL")


class InterioAgent:
    def __init__(self, document_dir: str, image_dir: str):
        self.document_dir = document_dir
        self.image_dir = image_dir

    async def initialize(self, host: str, port: int):
        self.client = LlamaStackClient(base_url=f"http://{host}:{port}")
        # setup agent for inference
        self.agent_id = await self._get_agent()
        # setup memory bank for RAG
        self.bank_id = await self.build_vector_db(self.document_dir)

    async def _get_agent(self):
        agent_config = AgentConfig(
            model=MODEL,
            instructions="",
            sampling_params={"strategy": {"type": "greedy"}},
            enable_session_persistence=True,
        )
        response = self.client.agents.create(
            agent_config=agent_config,
        )
        self.agent_id = response.agent_id
        return self.agent_id
    
    async def create_chat_session(self) -> str:
        """
        创建一个新的对话会话，并返回 session_id
        """
        session_response = self.client.agents.session.create(
            agent_id=self.agent_id,
            session_name=uuid.uuid4().hex,
        )
        return session_response.session_id

    async def chat_turn(self, session_id: str, message: dict) -> str:
        """
        在已有会话中进行一轮对话。
        :param session_id: 已创建会话的 session_id
        :param message: 用户消息字典，格式例如：
            {
            "role": "user",
            "content": [
                {"type": "text", "text": "你好"},
                {"type": "image", "image": {"url": {"uri": "<data_url>"}}}
            ]
            }
        :return: agent 回复的文本
        """
        generator = self.client.agents.turn.create(
            agent_id=self.agent_id,
            session_id=session_id,
            messages=[message],
            stream=True,
        )
        for chunk in generator:
            if chunk.event.payload.event_type == "turn_complete":
                turn = chunk.event.payload.turn
                break
        return turn.output_message.content.strip()

    async def list_items(self, file_path: str, session_id: str = None) -> dict:
        """
        分析图片并返回描述和家具列表，使用指定的 session_id 保持上下文。
        """
        assert self.agent_id is not None, "Agent not initialized, call initialize() first"
        text = textwrap.dedent(
            """
            Analyze the image and provide exactly a 4-sentence description of the architectural style and furniture items present. Include only furniture items that are visible.
            Return the result as a valid JSON object in exactly this format (no additional text or explanations):
            {
                "description": "a 4-sentence architectural description of the image",
                "items": ["item1", "item2", "item3", ...]
            }
            """
        )
        # 如果没有传入 session_id，则创建新的会话（你也可以选择强制要求传入）
        if not session_id:
            session_response = self.client.agents.session.create(
                agent_id=self.agent_id,
                session_name=uuid.uuid4().hex,
            )
            session_id = session_response.session_id

        data_url = data_url_from_image(file_path)
        message = {
            "role": "user",
            "content": [
                {"type": "image", "image": {"url": {"uri": data_url}}},
                {"type": "text", "text": text},
            ],
        }
        response = self.client.agents.turn.create(
            agent_id=self.agent_id,
            session_id=session_id,
            messages=[message],
            stream=True,
        )

        for chunk in response:
            payload = chunk.event.payload
            if payload.event_type == "turn_complete":
                turn = payload.turn
                break

        result = turn.output_message.content
        try:
            d = json.loads(result.strip())
        except Exception:
            cprint(f"Error parsing JSON output: {result}", color="red")
            raise
        return d

    async def suggest_alternatives(self, file_path: str, item: str, n: int = 3, session_id: str = None) -> List[str]:
        """
        同样支持传入 session_id
        """
        prompt = textwrap.dedent(
            """
            For the given image, your task is to carefully examine the image to provide alternative suggestions for {item}.
            The {item} should fit well with the overall aesthetic of the room.
            Carefully analyze the image and generate alternative descriptions.
            Each description should be 10-20 words long, each on a separate line.
            Return results in the following format:
            [
                {{"description": "first alternative suggestion"}},
                {{"description": "second alternative suggestion"}}
            ]
            Only provide {n} alternative descriptions.
            """
        )
        text_prompt = prompt.format(item=item, n=n)
        data_url = data_url_from_image(file_path)
        if not session_id:
            session_response = self.client.agents.session.create(
                agent_id=self.agent_id,
                session_name=uuid.uuid4().hex,
            )
            session_id = session_response.session_id

        message = {
            "role": "user",
            "content": [
                {"type": "image", "image": {"url": {"uri": data_url}}},
                {"type": "text", "text": text_prompt},
            ],
        }
        generator = self.client.agents.turn.create(
            agent_id=self.agent_id,
            session_id=session_id,
            messages=[message],
            stream=True,
        )
        for chunk in generator:
            payload = chunk.event.payload
            if payload.event_type == "turn_complete":
                turn = payload.turn
                break
        result = turn.output_message.content
        print(result)
        return [r["description"].strip() for r in json.loads(result.strip())]

    async def retrieve_images(self, description: str, session_id: str = None):
        """
        同样支持传入 session_id
        """
        assert self.bank_id is not None, "Setup bank before calling this method via initialize()"
        if not session_id:
            session_response = self.client.agents.session.create(
                agent_id=self.agent_id,
                session_name=uuid.uuid4().hex,
            )
            session_id = session_response.session_id

        agent_config = AgentConfig(
            enable_session_persistence=False,
            model=MODEL,
            instructions="",
            sampling_params={"strategy": {"type": "greedy"}},
            toolgroups=[
                {
                    "name": "builtin::rag",
                    "args": {
                        "vector_db_ids": [self.bank_id],
                        "query_config": QueryConfig(
                            max_chunks=5,
                            max_tokens_in_context=4096,
                            query_generator_config={
                                "type": "llm",
                                "model": MODEL,
                                "template": textwrap.dedent(
                                    """
                                You are given a conversation between a user and their assistant.
                                From this conversation, you need to extract a one sentence description that is being asked for by the user.
                                This one sentence description will be used to query a memory bank to retrieve relevant images.

                                Analyze the provided conversation and respond with one line description and no other text or explanation.

                                Here is the conversation:
                                {% for message in messages %}
                                {{ message.role }}> {{ message.content }}
                                {% endfor %}
                                """
                                ),
                            },
                        ),
                    },
                },
            ],
        )
        prompt = textwrap.dedent(
            """
            You are given a description of an item.
            Your task is to find images of that item in the memory bank that match the description.
            Return the top 4 most relevant results.

            Return results in the following format:
            [
                {
                    "image": "uri value",
                    "description": "description of the image",
                },
                {
                    "image": "uri value",
                    "description": "description of the image 2",
                }
            ]
            The uri value is enclosed in the tags <uri> and </uri>.
            The description is a summarized explanation of why this item is relevant and how it can enhance the room.

            Return JSON as suggested, Do not return any other text or explanations.
            Do not create uri values, return actual uri value (eg. "011.webp") as is.
            """
        )
        description_text = f"Description: {description}"
        message = {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "text", "text": description_text},
            ],
        }
        response = create_single_turn(self.client, agent_config, [message])
        result = response.strip()
        print("Raw response:", result)
        return json.loads(result)

    # NOTE: If using a persistent memory bank, building on the fly is not needed
    # and LlamaStack apis can leverage existing banks
    async def build_vector_db(self, local_dir: str) -> str:
        """
        Build a vector db that can be used to store and retrieve images.
        """
        self.live_bank = "interio_bank"
        logger.info("Registering vector db with id: %s", self.live_bank)
        self.client.vector_dbs.register(
            vector_db_id=self.live_bank,
            embedding_model="all-MiniLM-L6-v2",
            embedding_dimension=384,
        )

        local_dir = Path(local_dir)
        documents = []
        for i, file in enumerate(local_dir.iterdir()):
            if file.is_file():
                logger.info("Processing file: %s", file.name)
                with file.open("r") as f:
                    content = f.read()
                logger.debug("Content of %s: %s", file.name, content)
                documents.append({
                    "document_id": uuid.uuid4().hex,
                    "content": content,
                    "mime_type": "text/plain",
                })
        logger.info("Total documents processed: %d", len(documents))
        
        assert len(documents) > 0, "No documents found in the provided directory"
        logger.info("Inserting documents into vector db '%s'", self.live_bank)
        self.client.tool_runtime.rag_tool.insert(
            vector_db_id=self.live_bank,
            documents=documents,
            chunk_size_in_tokens=512,
        )
        logger.info("Documents inserted successfully into vector db")
        
        return "interio_bank"