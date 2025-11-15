import logger

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.messages import RemoveMessage
from langgraph.graph import StateGraph, START, END

from utils import init_model
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from typing import TypedDict, Annotated, Optional
from langgraph.graph import add_messages
from langchain_core.runnables import RunnableConfig
import asyncio

from dotenv import load_dotenv
import redis
import json
import os, time
from agent_tools import get_rag_data, search_web_using_bocha
from langchain_tavily import TavilySearch
tavily_search = TavilySearch(api_key=os.getenv("TAVILY_API_KEY"))
#from langgraph.graph import dispatch_custom_event
from langchain_core.callbacks import dispatch_custom_event
#from video_gen_agent import video_gen_agent    

load_dotenv()
# Redis connection (optional)
_redis_client = None
try:
    _redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD") or None,
        decode_responses=True,
        socket_timeout=2,
    )
    # Ping to verify
    _redis_client.ping()
    print("Redis connected for summary storage.")
except Exception as _e:
    _redis_client = None
    print(f"Redis not available, fallback to file: {_e}")

user_global_info = {} # user_id -> session_id -> info
def set_user_global_fact(user_id: str, fact: str):
    # Update in-memory store first
    existing = user_global_info.get(user_id, {})
 
    localtime = time.asctime( time.localtime(time.time()) )
    fact = "record time: " + localtime + "\n" + fact
    if 'user_fact' not in existing:
        existing['user_fact'] = fact
    else:
        existing['user_fact'] = existing['user_fact'] + '\n' + fact
    user_global_info[user_id] = existing

    if _redis_client is not None:
        try:
            _redis_client.set(f"chat:user_fact:{user_id}", existing['user_fact'])
        except Exception as e:
            print(f"[set_user_global_info] Redis set error for {user_id}: {e}")
    else:
        try:
            to_persist = {
                "user_fact": existing['user_fact'],
            }
            with open(f"user_global_info_{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(to_persist, f, ensure_ascii=False)
        except Exception as e:
            print(f"[set_user_global_fact] File persist error for {user_id}: {e}")

def set_user_like_ornot(user_id: str, user_like_ornot_reason: str):
    """Save user like or not feedback to Redis and file"""
    # Update in-memory store first
    existing = user_global_info.get(user_id, {})
    
    localtime = time.asctime(time.localtime(time.time()))
    feedback = f"record time: {localtime}\n{user_like_ornot_reason}"
    
    if 'user_like_ornot' not in existing:
        existing['user_like_ornot'] = feedback
    else:
        existing['user_like_ornot'] = existing['user_like_ornot'] + '\n\n' + feedback
    user_global_info[user_id] = existing
    
    # Persist to Redis when available
    if _redis_client is not None:
        try:
            _redis_client.set(f"chat:user_like_ornot:{user_id}", existing['user_like_ornot'])
        except Exception as e:
            print(f"[set_user_like_ornot] Redis set error for {user_id}: {e}")
    else:
        # Fallback to file
        try:
            # Read existing file and merge
            to_persist = {}
            if os.path.exists(f"user_global_info_{user_id}.json"):
                try:
                    with open(f"user_global_info_{user_id}.json", "r", encoding="utf-8") as rf:
                        to_persist = json.load(rf)
                except:
                    pass
            # Update with new like_ornot data
            to_persist["user_like_ornot"] = existing['user_like_ornot']
            # Write back
            with open(f"user_global_info_{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(to_persist, f, ensure_ascii=False)
        except Exception as e:
            print(f"[set_user_like_ornot] File persist error for {user_id}: {e}")

def set_user_session_history(user_id: str, session_id: str, info: dict):
    # Update in-memory store first
    #print('set_user_global_info', session_id, info)
    existing = user_global_info.get(user_id, {}).get(session_id, {})
    #print(f"set_user_session_history: {info} and {existing}")
    existing['summary'] = info['summary']
    # Merge new history with existing history instead of overwriting
    #existing_history = existing.get('history', '')
    new_history = info.get('history', '')
    # Only append if new_history is not empty and not already in existing_history
    #if new_history and not existing_history.endswith(new_history):
    #existing['history'] = existing_history + '\n\n' + new_history if existing_history else new_history
    #else:
    existing['history'] = new_history
    user_global_info[user_id][session_id] = existing
    #print(f"set_user_global_info: {session_id} {list(existing.keys())}")

    # Persist summary to Redis when available
    summary_value = existing.get("summary", "")
    history_value = existing.get("history", "")
    if _redis_client is not None:
        try:
            _redis_client.set(f"chat:summary:{user_id}:{session_id}", summary_value)
            _redis_client.set(f"chat:history:{user_id}:{session_id}", history_value)
        except Exception as e:
            print(f"[set_user_global_info] Redis set error for {session_id}: {e}")
    else:
        # Keep JSON file as optional fallback/debug snapshot (messages_history only for visibility)
        try:
            to_persist = {
                "summary": summary_value,
                "history": history_value,
            }
            with open(f"user_global_info_{user_id}_{session_id}.json", "w", encoding="utf-8") as f:
                json.dump(to_persist, f, ensure_ascii=False)
        except Exception as e:
            print(f"[set_user_global_info] File persist error for {user_id}:{session_id}: {e}")

def get_user_global_info(user_id: str) -> str:
    # Ensure in-memory object exists
    if user_id not in user_global_info:
        user_global_info[user_id] = {}
    if 'user_fact' not in user_global_info[user_id]:
        user_global_info[user_id]['user_fact'] = ""
    
    # Load user fact from Redis if available; fallback to file
    try:
        user_fact_loaded = None
        if _redis_client is not None:
            try:
                user_fact_key = f"chat:user_fact:{user_id}"
                user_fact_loaded = _redis_client.get(user_fact_key)
                print(f"[get_user_global_info] Redis get user_fact: {user_fact_loaded}")
            except Exception as e:
                print(f"[get_user_global_info] Redis get error for {user_id}:{user_fact_key}: {e}")

        if user_fact_loaded is not None:
            user_global_info[user_id]['user_fact'] = user_fact_loaded
        elif os.path.exists(f"user_global_info_{user_id}.json"):
            with open(f"user_global_info_{user_id}.json", "r", encoding="utf-8") as f:
                persisted = json.load(f)
                if isinstance(persisted, dict):
                    user_global_info[user_id]['user_fact'] = persisted.get("user_fact", "")
                    
    except Exception as e:
        print(f"[get_user_global_info] Load error for {user_id}: {e}")

    # Do not print potentially large/non-serializable structures
    #print(f"get_user_global_info: {user_id} {session_id} keys={list(user_global_info[user_id][session_id].keys())}")
    return user_global_info.get(user_id, {}).get('user_fact', '')

def get_user_session_history(user_id: str, session_id: str) -> dict:
    # Ensure in-memory object exists
    if user_id not in user_global_info:
        user_global_info[user_id] = {}
   
    if session_id not in user_global_info[user_id]:
        user_global_info[user_id][session_id] = {}

    # Load summary from Redis if available; fallback to file
    try:
        summary_loaded = None
        history_loaded = None
        
        if _redis_client is not None:
            try:
                summary_loaded = _redis_client.get(f"chat:summary:{user_id}:{session_id}")
                history_loaded = _redis_client.get(f"chat:history:{user_id}:{session_id}")
            except Exception as e:
                print(f"[get_user_global_info] Redis get error for {user_id}:{session_id}: {e}")

        if summary_loaded is not None:
            user_global_info[user_id][session_id]["summary"] = summary_loaded
            user_global_info[user_id][session_id]["history"] = history_loaded
        elif os.path.exists(f"user_global_info_{session_id}.json"):
            with open(f"user_global_info_{user_id}_{session_id}.json", "r", encoding="utf-8") as f:
                persisted = json.load(f)
                if isinstance(persisted, dict):
                    user_global_info[user_id][session_id]["summary"] = persisted.get("summary", "")
                    user_global_info[user_id][session_id]["history"] = persisted.get("history", "")
                    
    except Exception as e:
        print(f"[get_user_global_info] Load error for {session_id}: {e}")

    # Do not print potentially large/non-serializable structures
    #print(f"get_user_global_info: {user_id} {session_id} keys={list(user_global_info[user_id][session_id].keys())}")
    return user_global_info.get(user_id, {}).get(session_id, {})

async def delete_user_session_history(user_id: str, session_id: str):
    """
    Delete the history and summary of a particular session_id for a user from redis and file, and in-memory.
    """
    result = {"redis": False, "file": False, "memory": False}
    # Remove from Redis
    if '_redis_client' in globals() and _redis_client is not None:
        try:
            redis_history_key = f"chat:history:{user_id}:{session_id}"
            redis_summary_key = f"chat:summary:{user_id}:{session_id}"
            _redis_client.delete(redis_history_key)
            _redis_client.delete(redis_summary_key)
            result["redis"] = True
        except Exception as e:
            print(f"[delete_user_session_history] Redis delete error for {user_id}:{session_id}: {e}")

    # Remove from file
    file_deleted = False
    file_path = f"user_global_info_{user_id}_{session_id}.json"
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            file_deleted = True
        except Exception as e:
            print(f"[delete_user_session_history] File delete error for {file_path}: {e}")
    result["file"] = file_deleted

    # Remove from memory
    mem_deleted = False
    try:
        if user_id in user_global_info:
            if session_id in user_global_info[user_id]:
                del user_global_info[user_id][session_id]
                mem_deleted = True
    except Exception as e:
        print(f"[delete_user_session_history] Memory delete error for {user_id}:{session_id}: {e}")
    result["memory"] = mem_deleted

    return result

chat_tools = [get_rag_data, search_web_using_bocha, tavily_search] 

chat_tool_node = ToolNode(chat_tools)

class State(TypedDict):
    messages: Annotated[list, add_messages]
    user_facts: str
    dataset_id: str
    do_web_search: bool = False
    intention: str #  the intention of the user
    summary: str #  the summary of the conversation
    history: str #  the history of the conversation that is not summarized yet
    #N: int = 10 #  the number of messages to keep 
    threshold: int = 2000 #  the threshold of messages, if len > threshold, then summarize the messages

# Initialize model
model_raw, model_turbo = init_model()
model = model_raw.bind_tools(chat_tools)
# Create graph
builder = StateGraph(state_schema=State)   

# 定义摘要逻辑
async def summarize_conversation(state: State):
    summary = state.get("summary", "")
    history = state.get("history", "")
    # Filter messages to avoid tool call issues - only include text content
    messages_to_summarize = state["messages"]
    print(f"all state messages count: {len(messages_to_summarize)}")
    
    # Build a text representation of the conversation from ALL messages
    # Note: state["messages"] contains ALL messages due to LangGraph checkpoint restoration
    conversation_text = ""
    for msg in messages_to_summarize:
        if hasattr(msg, 'content') and isinstance(msg.content, str) and msg.content.strip():
            if hasattr(msg, 'type'):
                if msg.type == "tool":
                    role = "Tool"
                    continue
                elif msg.type == "human":
                    role = "User"
                elif msg.type in ["assistant", "ai"]:
                    role = "Assistant"
                else:
                    role = "Unknown"
                #role = "User" if msg.type == "human" else "Assistant"
                conversation_text += f"{role}: {msg.content}\n\n"

    print(f"conversation_text length: {len(conversation_text)}, history length: {len(history)}")
    print(f"conversation_text preview: {conversation_text[:200]}...")

    # Since conversation_text contains ALL messages (due to checkpoint restoration),
    # we should REPLACE history with conversation_text, not append, to avoid duplicates
    if len(history) + len(conversation_text) < state['threshold']: # if the conversation text is not too long, then return the summary and history
        # Clear all messages after summarizing (using RemoveMessage for all messages)
        delete_messages = [RemoveMessage(id=msg.id) for msg in messages_to_summarize if hasattr(msg, 'id')]
        return {"summary": summary, "history": history + conversation_text, "messages": delete_messages}

    if summary:
        uptodate_message= (
            f"This is summary of the conversation to date: {summary}\n\n"
        )

        summary_message = (
            f"Extend the summary by keeping the information in the summary, and taking into account the new messages above:"
            "The summary message should in the format of user is interested in xxx, then ai response is xxx "
            "then user is interested in xxx, then ai response is xxx, ... etc."
            "Include as many specific details as you can."
            "Keep summary short and concise. you MUST summarize in Chinese."
        )
        #print(f"summary_message: {summary_message}")
    else:
        uptodate_message= ''
        summary_message = "Create a summary of the conversation above:"
       
   # if the conversation text is longer than threshold, then summarize it
    # conversation_text already contains ALL messages, so don't concatenate with history to avoid duplicates
    messages = [
        HumanMessage(content=f"{uptodate_message}\n\n{history} {conversation_text}\n\n{summary_message}")
    ]
    print(f"summary messages: {messages}")
    response = await model_raw.ainvoke(messages)
    print(f"summary response: {response.content}")
   
    # Clear all messages after summarizing (using RemoveMessage for all messages)
    delete_messages = [RemoveMessage(id=msg.id) for msg in messages_to_summarize if hasattr(msg, 'id')]
    return {"summary": response.content, "history": '', "messages": delete_messages}



async def chatbot(state: State):
    summary = state['summary'] 
    user_facts = state['user_facts']
    history = state['history']

    if True:
        system_message = SystemMessage(
        content=f"""You are the best product recommendation agent in the world. 
        Review information about the user and their prior conversation summary below and respond accordingly.
        You have knowledge about any product the customers asks you a recommendation for.
        Your recommendations are logical and can convince the people who are looking for the 
        product. Don't ask user what brand they want to buy. Suggest everything you know using the tools you have
        if user ask you a question, you should call tavily search tool to search the web for information about the user's question
        if you reply user without calling tavily search tool, you MUST tell user that you are pretty sure what user said is not related to the web, then you answer with your own knowledge.
        your response should be in Chinese. Keep responses short and concise.
        """
    )
    else:
        system_message = SystemMessage(
            content=f"""You are a helpful assistant. 
            Review information about the user and their prior conversation summary below and respond accordingly.
            if user ask you a question, you should call rag tool to search in the rag database even user's question is very easy.
            the dataset_id to search the RAG database is {state['dataset_id']}
            if you reply user without calling rag tool, you MUST tell user that you are pretty sure what user said is not related to the rag database, then you answer with your own knowledge.
            your response should be in Chinese.
            then you should call web search tool to search the web for information about the user's question, the topk of the web search is 5.
            generally, your response should contain two parts:
            part 1: based on the information you got from the rag tool, if the information is relevant to the user's question, you should answer the user's question based on the information you got from the rag tool start with "根据知识库返回的信息，," otherwise tell user you can not find related information in the database.
            part 2. based on your own knowledge, if you know something related to the user's question, you should answer the user's question start with "以下内容和知识库返回的信息无关，仅供参考，据我所知,"
            Keep responses short and concise.
            """
        )

    if user_facts != "":
        system_message.content += f"here is the facts about the user: {user_facts}\n\n"
    if summary != "":
        system_message.content += f"here is the historical conversation summary: {summary}\n\n"
    if history != "":
        system_message.content += f"here is the historical conversation history that is not summarized yet: {history}\n\n"
        
    print(f"system_message: {system_message.content}")
    message_updates = await model.ainvoke([system_message] + state['messages'])
    return {'messages': message_updates}


graph_builder = StateGraph(State)

# Define the function that determines whether to continue or not
async def should_continue(state: State):
    messages = state["messages"]
    # Check if last message has tool_calls
    last_msg = messages[-1] if messages else None
    if last_msg and hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        return 'tools'

    return 'summarize'


graph_builder.add_node('agent', chatbot)
graph_builder.add_node('tools', chat_tool_node)
graph_builder.add_node('summarize', summarize_conversation)

graph_builder.add_edge(START, 'agent')
graph_builder.add_conditional_edges('agent', should_continue, {'tools': 'tools', 'summarize': 'summarize'})
graph_builder.add_edge('tools', 'agent')
graph_builder.add_edge('summarize', END)

chat_app = graph_builder.compile()

async def run_with_monitoring_events(query: str, dataset_id: str, user_id: str, session_id: str, do_web_search: bool) -> State:
    """使用事件流监控运行Agent，返回事件流"""
    all_history = get_user_session_history(user_id, session_id)
    summary = all_history.get("summary", "")
    history = all_history.get("history", "")

    user_facts = get_user_global_info(user_id)
        
    initial_state = State(messages=[HumanMessage(content=query)], dataset_id=dataset_id, user_facts=user_facts, 
    summary=summary, history=history, threshold=1000, do_web_search=do_web_search)
    
    print(f"Chatbot Starting")
    # 返回事件流
    # No thread_id needed since we're not using checkpointer
    async for event in chat_app.astream_events(
        initial_state,
        RunnableConfig(recursion_limit=50),
        version="v2",
    ):
        if event["event"] == "on_chain_end":
            #if event.get("name") == "summarize":
            name = event.get("name")
            #print(f"name: {name}")
            agent_output = event.get("data", {}).get("output", {})
            #print(f"Agent output: {agent_output}")
            if name == "summarize":
                summary = event.get("data", {}).get("output", {}).get("summary", "")
                history = event.get("data", {}).get("output", {}).get("history", "")
                set_user_session_history(user_id, session_id, {"summary": summary, "history": history})
        yield event
        

if __name__ == "__main__":
    async def test_comfyui():
        # Test call_comfyui with missing required parameters to show error handling
        workflow_file = "/home/ubuntu/ucloud/workflows/video_upscale_cuda.json"
        
        # Override ComfyUI base URL if not set in environment
        # You can set COMFYUI_BASE_URL=http://localhost:8288 in .env file instead
        import os
        # Set environment variable before importing/using settings
        if not os.getenv("COMFYUI_BASE_URL"):
            os.environ["COMFYUI_BASE_URL"] = "http://localhost:8288"
        
        # Reload settings to pick up the new environment variable
        from settings import Settings
        # Create a new settings instance to pick up environment variable
        test_settings = Settings()
        # Update global settings
        from settings import settings
        settings.comfyui_base_url = test_settings.comfyui_base_url
        
        # Update the default client with new base URL
        from comfyui.facade import default_client
        default_client.base_url = settings.comfyui_base_url
        # Reset executor to force re-initialization with new base_url
        default_client._executor = None
        print(f"Using ComfyUI base URL: {settings.comfyui_base_url}")
        
        # First, try to get metadata to see required parameters
        try:
            metadata = get_workflow_metadata(workflow_file)
            if metadata:
                required_params = [name for name, param in metadata.params.items() if param.required and param.default is None]
                print(f"Required parameters for {workflow_file}: {required_params}")
                
                # Build params with required parameters (use default values if available)
                params = {"prompt": "/home/ubuntu/ucloud/ComfyUI/input/chexiaoxiong.mp4"}
                for param_name, param_info in metadata.params.items():
                    if param_name not in params:
                        if param_info.required and param_info.default is not None:
                            params[param_name] = param_info.default
                        elif param_name == "width" and param_name not in params:
                            params[param_name] = 720  # Default width
                        elif param_name == "height" and param_name not in params:
                            params[param_name] = 480  # Default height
                        elif param_name == "seed" and param_name not in params:
                            params[param_name] = -1  # Default seed (random)
                        elif param_name == "skip":
                            params[param_name] = 150
                
                print(f"Calling with params: {params}")
                # Use internal implementation function instead of tool wrapper
                result = await _call_comfyui_impl(workflow_file, params)
                print(f"call_comfyui result: {result}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    import asyncio
    asyncio.run(test_comfyui())



