import asyncio
import json
import logging

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class ChatService:
    def __init__(self, client, token):
        self.token = token
        self.client = client
        self.group_id_queue = asyncio.Queue(maxsize=10)  # 使用 asyncio.Queue
        self.group_id_in_use = set()  # 记录当前正在使用的 group_id
        self.lock = asyncio.Lock()  # 限制同时请求新的 group_id 的数量

    async def get_new_group_id(self):
        """访问 API 前申请新的 group_id，只能使用一次，不能缓存"""
        url = "https://chat.julianwl.com/api/group/create"
        payload = {"appId": 0}
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            response_data = response.json()
            if response_data.get("code") == 200 and response_data.get("success"):
                group_id = response_data["data"]["id"]
                if group_id not in self.group_id_in_use:
                    await self.group_id_queue.put(group_id)  # 将新的 group_id 添加到队列
                    return group_id
        except httpx.RequestError as e:
            logging.error("请求失败: %s", e)
        return None

    async def get_available_group_id(self):
        """获取可用的 group_id，若没有则申请新的"""
        if not self.group_id_queue.empty():
            return await self.group_id_queue.get()  # 从队列中取出一个可用的 group_id

        async with self.lock:  # 加锁确保线程安全
            return await self.get_new_group_id()  # 申请新的 group_id

    async def get_response_from_api(self, system_prompt, user_prompt):
        """从 API 获取响应，支持重试机制"""
        group_id = await self.get_available_group_id()
        if group_id is None:
            return None

        payload = {
            "prompt": user_prompt,
            "appId": None,
            "options": {
                "temperature": 0.8,
                "model": 3,
                "groupId": group_id,
                "usingNetwork": False
            },
            "systemMessage": system_prompt
        }

        async def fetch_response(attempts):
            for attempt in range(attempts):
                try:
                    response = await self.client.post("https://chat.julianwl.com/api/chatgpt/chat-process",
                                                      json=payload)
                    response.raise_for_status()

                    response_texts = []
                    async for line in response.aiter_lines():
                        if line:
                            decoded_line = json.loads(line)
                            if "text" in decoded_line:
                                response_texts.append(decoded_line["text"])
                            else:
                                logging.error("Unexpected response format: %s", decoded_line)
                                break

                    # 标记该 group_id 已完成
                    self.group_id_in_use.discard(group_id)
                    return response_texts[-1] if response_texts else None  # 返回最后一个文本响应
                except (httpx.RequestError, ValueError) as e:
                    logging.error("请求失败或解析错误: %s", e)
                    await asyncio.sleep(1)  # 等待一段时间后重试

            # 标记该 group_id 已完成
            self.group_id_in_use.discard(group_id)
            return None  # 如果失败，返回 None

        last_response_text = await fetch_response(3)
        return last_response_text


@app.on_event("startup")
async def startup_event():
    token = load_token()
    app.state.client = httpx.AsyncClient(
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        limits=httpx.Limits(max_connections=100)  # 设置最大连接数
    )
    app.state.chat_service = ChatService(app.state.client, token)


def load_token():
    """从文件中加载 API token"""
    with open("token", "r") as file:
        return file.read().strip()


@app.on_event("shutdown")
async def shutdown_event():
    await app.state.client.aclose()  # 关闭 httpx 客户端


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


@app.post('/v1/chat/completions')
async def chat_completions(request: ChatRequest):
    """聊天接口，处理用户输入并返回助手的响应"""
    if not request.messages or not isinstance(request.messages, list):
        raise HTTPException(status_code=400, detail="输入无效")

    system_prompt = request.messages[0].content
    user_prompt = request.messages[1].content if len(request.messages) > 1 else ""

    last_response_text = await app.state.chat_service.get_response_from_api(system_prompt, user_prompt)
    if last_response_text is None:
        raise HTTPException(status_code=500, detail="从 API 获取响应失败")

    response = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 666,
        "model": "gpt-3.5-turbo",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": last_response_text
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 666,
            "completion_tokens": 666,
            "total_tokens": 666
        }
    }

    return response


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
