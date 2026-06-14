"""AI 助教 LLM 调用（OpenAI 兼容 /v1/chat/completions，异步）。

settings.llm_base_url 为空 → 返回 None（上层据此优雅降级，不报错）。可指向：
- 服务器本机 Ollama：http://host.docker.internal:11434/v1（compose 已配 extra_hosts）
- 外部 API：https://api.deepseek.com/v1 等（配 LLM_API_KEY、LLM_MODEL）
"""
import httpx

from .config import settings


async def chat(messages: list[dict], temperature: float = 0.6) -> str | None:
    """返回模型回答文本；未配置或异常时由调用方处理（None / 抛错）。"""
    if not settings.llm_base_url:
        return None
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    payload = {"model": settings.llm_model, "messages": messages,
               "temperature": temperature, "stream": False}
    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        r = await client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        return (data["choices"][0]["message"]["content"] or "").strip()
