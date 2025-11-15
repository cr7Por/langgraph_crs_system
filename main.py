import argparse
from typing import Dict, Any
import json
import re

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from graph_abs import run_with_monitoring_events, set_user_global_fact, set_user_like_ornot

app = FastAPI()

from fastapi import Body
from graph_abs import delete_user_session_history

@app.post("/delete_session_history")
async def delete_session_history(
    user_id: str = Query(
        ...,
        description="The user id.",
        examples=["User_A"],
    ),
    session_id: str = Query(
        ...,
        description="The session id.",
        examples=["session_1"],
    ),
):
    """
    Delete the history of a particular session_id for a user from redis.
    """
    try:
        result = await delete_user_session_history(user_id, session_id)
        return {"message": f"History for session_id={session_id} and user_id={user_id} deleted.", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete history: {str(e)}")



@app.post("/upload_user_fact")
async def upload_user_fact(
    user_id: str = Query(
        "User_A",
        description="The user id.",
        examples=["User_A"],
    ),
    user_fact: str = Form(...),
):
    """
    Upload user fact to the global info.
    """
    set_user_global_fact(user_id, user_fact)
    return {"message": "User fact uploaded to global info successfully"}

@app.post("/upload_user_like_ornot")
async def upload_user_like_ornot(
    user_id: str = Query(
        ...,
        description="The user id.",
        examples=["User_A"],
    ),
    user_like_ornot_reason: str = Form(...),
):
    """
    Upload user like or not feedback to Redis.
    """
    set_user_like_ornot(user_id, user_like_ornot_reason)
    return {"message": "User like or not feedback uploaded successfully"}

@app.get("/query/")
async def perform_query(
    original_query: str = Query(
        ...,
        description="Your question here.",
        examples=["Write a report about Milvus."],
    ),
    dataset_id: str = Query(
        ...,
        description="The dataset id user can retrieve.",
        examples=["1"],
    ),
    user_id: str = Query(
        "User_A",
        description="The user id.",
        examples=["User_A"],
    ),
    thread_id: str = Query(
        ...,
        description="The session id.",
        examples=["session_1"],
    ),
    do_web_search: bool = Query(
        True,
        description="Whether to do web search.",
        examples=[True],
    ),
):
    """
    Stream responses from the chatbot for the provided query.
    """
    async def event_stream():
        last_video_url_local = None
        last_image_url_local = None
        def _iter_messages(msgs):
            if isinstance(msgs, list):
                for m in msgs:
                    yield m
            elif msgs is not None:
                yield msgs

        def _extract_first_url_from_text(text: str):
            matches = re.findall(r"https?://[\w\-./?=&%#]+", text)
            return matches[0] if matches else None

        def _extract_url_from_chunk(chunk: Dict[str, Any], list_key: str):
            if not isinstance(chunk, dict):
                return None
            urls = chunk.get(list_key)
            if isinstance(urls, list):
                for candidate in reversed(urls):
                    if isinstance(candidate, str) and candidate:
                        return candidate
            for msg in _iter_messages(chunk.get("messages")):
                content = getattr(msg, "content", None)
                if isinstance(content, str):
                    url = _extract_first_url_from_text(content)
                    if url:
                        return url
            return None
        print(f"[event_stream] 开始 original_query={original_query} dataset_id={dataset_id} user_id={user_id} thread_id={thread_id}")
        try:
            async for event in run_with_monitoring_events(original_query, dataset_id, user_id, thread_id, do_web_search):
                ev_type = event.get("event")
                print(f"[event_stream] 收到 事件: {event}")
                data = event.get("data")
                parsed_url = None
                parsed_url = None

                if ev_type == "on_chain_end":
                    node = event.get("name")
                    print(f"[event_stream] 收到 on_chain_end event: {node} {event}")

                elif ev_type == "on_chain_stream":
                    #print(f"[event_stream] 收到 on_chain_stream event: {event}")
                    metadata = event.get("metadata")
                    node = event.get("name")
                    if node not in {"agent", "summarize"}:
                        print(f"[event_stream] node 不是 agent, summarize : {node}")
                        continue
                    data = event.get("data")

                    print(f"[event_stream] data: {node}: {data}")
                    if not isinstance(data, dict):
                        data = {}
                    
                    # Handle chunk_obj extraction safely
                    chunk_obj = None
                    try:
                        chunk_obj = data.get("chunk") if isinstance(data, dict) else None
                    except (AttributeError, TypeError) as e:
                        print(f"[event_stream] Error getting chunk_obj: {e}")
                        chunk_obj = None
                    
                    if chunk_obj and hasattr(chunk_obj, "content") and chunk_obj.content:
                        #print(f"[event_stream] 收到 chunk_obj: {chunk_obj.content}")
                        yield f"{chunk_obj.content}"
                    elif isinstance(chunk_obj, dict):
                        msg = None
                        try:
                            if "messages" in chunk_obj:
                                msg = chunk_obj.get("messages")
                            elif "agent" in chunk_obj and isinstance(chunk_obj.get("agent"), dict):
                                msg = chunk_obj.get("agent", {}).get("messages")
                        except (AttributeError, TypeError) as e:
                            print(f"[event_stream] Error getting messages from chunk_obj: {e}")
                            msg = None

                        # Handle different message types
                        if msg:
                            # If msg is a single message object
                            if hasattr(msg, "content"):
                                if isinstance(msg.content, str) and msg.content:
                                    print(f"[event_stream] 输出消息内容 (单条): {msg.content[:100]}...")
                                    yield f"{msg.content}"
                                elif isinstance(msg.content, list):
                                    # Handle list content
                                    for content_item in msg.content:
                                        if isinstance(content_item, str) and content_item:
                                            print(f"[event_stream] 输出消息内容 (列表项): {content_item[:100]}...")
                                            yield f"{content_item}"
                            # If msg is a list of messages
                            elif isinstance(msg, list):
                                for m in msg:
                                    if hasattr(m, "content"):
                                        if isinstance(m.content, str) and m.content:
                                            print(f"[event_stream] 输出消息内容 (列表): {m.content[:100]}...")
                                            yield f"{m.content}"
                                        elif isinstance(m.content, list):
                                            for content_item in m.content:
                                                if isinstance(content_item, str) and content_item:
                                                    print(f"[event_stream] 输出消息内容 (列表中的列表项): {content_item[:100]}...")
                                                    yield f"{content_item}"
        except Exception as e:
            print(ev_type)
            print(f"[event_stream] Exception: {e}")
            yield f"error: {str(e)}\n\n"
        print(f"[event_stream] 正常结束 original_query={original_query} thread_id={thread_id}")

    print(f"[perform_query] 被调用 original_query={original_query} thread_id={thread_id}")
    try:
        response = StreamingResponse(event_stream(), media_type="text/event-stream")
        print("[perform_query] 返回 StreamingResponse")
        return response
    except Exception as e:
        print(f"[perform_query] Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FastAPI Server")
    #parser.add_argument("--enable-cors", type=bool, default=False, help="Enable CORS support")
    #args = parser.parse_args()
    # if args.enable_cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    print("CORS is enabled.")
    # else:
    #     print("CORS is disabled.")
    uvicorn.run(app, host="0.0.0.0", port=8191)
