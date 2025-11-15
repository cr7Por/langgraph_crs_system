"""Utility functions used in our graph."""

from typing import Optional, Tuple, List
import os 
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage
from langchain_core.runnables import RunnableConfig
from langchain_community.chat_models import ChatTongyi
from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import ToolMessage
import re
from langchain_aws import ChatBedrockConverse
from langchain_google_genai import ChatGoogleGenerativeAI
from logger import logger

def get_message_text(msg: AnyMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()

def azure_openai():
    os.environ["OPENAI_API_VERSION"] = "2024-05-01-preview"
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://admin-m64josxc-westus3.cognitiveservices.azure.com"
    os.environ["AZURE_OPENAI_API_KEY"] = ""
    
    llm = AzureChatOpenAI(
        model_name="gpt-4o",
        temperature=0,
        api_version="2024-05-01-preview",
        azure_endpoint="https://admin-m64josxc-westus3.cognitiveservices.azure.com",
        azure_deployment="gpt-4o",
        openai_api_version="2024-05-01-preview"
    )
    logger.info(f"LLM Initiating azure_openai model")
    return llm

def gemini_openai():
    llm = ChatGoogleGenerativeAI(
        model='gemini-2.5-pro-preview-05-06',
        temperature=1.0,
        max_retries=2,
        api_key=os.environ["GEMINI_API_KEY"] #os.getenv("GEMINI_API_KEY"),
    )
    logger.info(f"LLM Initiating gemini_openai model")
    return llm

def qwen_turbo():
    # 初始化两个模型：一个用于普通对话，一个用于图像
    
    # ChatTongyi supports several models. Popular options include:
    # - "qwen-plus": enhanced Qwen with high performance (default)
    # - "qwen-max": for more powerful and larger context needs
    # - "qwen-turbo": cost-effective, faster, lighter
    # - "qwen-vl-max": for vision-language (multi-modal)
    # - "qwen-vl-7b": smaller vision-language model
    #
    # Example usage:
    model_plus = ChatTongyi(
        #model="deepseek-v3.2-exp", # You can also try "qwen-max", "qwen-turbo", etc.
        model="qwen-plus",
        streaming=False,
        temperature=0.0
    )
    
    model_turbo = ChatTongyi(
        model="qwen-turbo",
        streaming=False,
        temperature=0.0
    )


    logger.info(f"LLM Initiating qwen_turbo model")
    return model_plus, model_turbo

def openai_gpt():
    provider = 'openai'
    # 确保使用支持视觉的模型
    model = 'gpt-4o'  
    llm = init_chat_model(model, model_provider=provider,temperature=0.7)
    logger.info(f"LLM Initiating openai_gpt model")
    return llm


def init_model():
    # 使用通义千问模型
    #llm = azure_openai()
    #llm = openai_gpt()
    #llm = aws_claude()

    llm_plus, llm_turbo = qwen_turbo()
    return llm_plus, llm_turbo

def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }


def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )


def _print_event(event: dict, _printed: set, max_length=1500):
    current_state = event.get("dialog_state")
    if current_state:
        print("Currently in: ", current_state[-1])
    message = event.get("messages")
    if message:
        if isinstance(message, list):
            message = message[-1]
        if message.id not in _printed:
            msg_repr = message.pretty_repr(html=True)
            if len(msg_repr) > max_length:
                msg_repr = msg_repr[:max_length] + " ... (truncated)"
            print(msg_repr)
            _printed.add(message.id)

def _print_output(event: dict, _printed: set, max_length=1500):
    current_state = event.get("dialog_state")
    # if current_state:
    #     print("Currently in: ", current_state[-1])
    message = event.get("messages")
    if message:
        if isinstance(message, list):
            message = message[-1]
        if message.id not in _printed:
            msg_repr = message.pretty_repr(html=True)
            if len(msg_repr) > max_length:
                msg_repr = msg_repr[:max_length] + " ... (truncated)"
            
            print(msg_repr)
            _printed.add(message.id)

def display_arrangement(arrangement_text: str) -> None:
    """Display arrangement text in the Gradio chat interface.
    
    Args:
        arrangement_text (str): The text to display in the arrangement area
    """
    #print("abc: ", arrangement_text)
    if hasattr(display_arrangement, 'arrangement_area'):
        # 设置value后，Gradio会在下一个事件循环中自动更新界面
        # 不需要手动调用更新方法，Gradio会自动处理
        display_arrangement.arrangement_area.value = arrangement_text

if __name__ == "__main__":
    llm = init_model()
    print(llm.invoke("你好"))

    




