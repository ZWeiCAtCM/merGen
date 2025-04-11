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
            instructions="""
            You are a professional **interior designer**. 
            All of your conversations should be framed from the perspective of an expert in interior design.
            You will use precise design terminology and industry-standard vocabulary in your responses.
            Always consider spatial harmony, materiality, color palettes, lighting, furniture style, and architectural context in your answers.
            Never respond as a general assistant; always remain in your role as an interior designer.
            When asked to give a prompt, it means a prompt for image generation. always only directly answer the content of the prompt and nothing else, no prefix or suffix.
            """,
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
                # Enable memory as a tool for RAG
                {
                    "name": "builtin::rag",
                    "args": {
                        "vector_db_ids": [self.bank_id],
                        "query": description, 
                        "query_config":  {
                            "max_chunks": 5,
                            "max_tokens_in_context": 4096,
                        },
                    },
                },
            ],
        )
        
        prompt = textwrap.dedent(
            """
            Your task is to retrieve relevant 3 matching images along with prices from memory bank using the RAG tool.
            You will receive a query from the user.
            Use the tool to perform the search.
            Don't provide duplicated images.
            Once you receive the tool result, don't repeatedly make another tool call, return 3 matching images to show their image paths and prices and description in the following example JSON array format.

            Follow this JSON array example format exactly:
            [
                {
                    "image":"001.jpeg",
                    "price":"$100",
                    "description":"A beautiful table with a modern design."
                }, 
                {
                    "image":"009.jpeg",
                    "price":"$120",
                    "description":"A stylish chair with a vintage look."
                }, 
                {
                    "image":"006.jpeg",
                    "price":"$160",
                    "description":"A cozy sofa with a contemporary style."
                }
            ]
            image paths are enclosed in <uri> tags but dont include tags themselves.
            prices are enclosed in <price> tags but dont include tags themselves.
            descriptions are summaries based on the corresponding image document.
            Do not include explanations or extra characters.
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
        response = await create_single_turn(self.client, agent_config, [message])
        print("LLaMA raw response:", response)
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