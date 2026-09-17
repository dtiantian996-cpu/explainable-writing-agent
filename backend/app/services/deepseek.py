"""用于结构化智能体输出的 DeepSeek Chat Completions 客户端。

AgentRuntime 会把每个智能体的 Prompt 和对应的 Pydantic Schema 传给该客户端。
客户端请求 DeepSeek 返回 JSON 对象，提取 JSON 载荷，并在返回工作流代码前
将其校验为指定 Schema。
"""

from __future__ import annotations

import json
import re
from typing import TypeVar

import httpx
from pydantic import BaseModel

from app.core.config import get_settings


SchemaT = TypeVar("SchemaT", bound=BaseModel)


class DeepSeekClient:
    """DeepSeek 兼容 Chat Completions API 的轻量封装。"""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[SchemaT],
    ) -> SchemaT:
        """生成 JSON 响应，并使用传入的 Schema 进行校验。"""

        payload = {
            "model": self.settings.deepseek_model,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.settings.deepseek_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.deepseek_api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        return schema.model_validate(self._extract_json(content))

    def _extract_json(self, content: str) -> dict:
        """解析模型输出；必要时回退到提取第一个 JSON 对象片段。"""

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))
