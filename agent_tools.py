from ragflow import Ragflow
from langchain_core.tools import tool
import os

from typing import Dict, Any
from search_web import search_web
from datetime import datetime
ragflow = Ragflow() 

@tool
async def search_web_using_bocha(query: str, topk: int = 5) -> str:
    """Search the web for information about the query
    Args:
        query: the query to search the web.
        topk: the number of top results to return.
    Returns:
        The results of the search.
    """
    return await search_web(query, topk, trigger_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@tool
async def get_rag_data(query: str, dataset_id: str) -> str:
    """Search the RAG database for information about the query
    Args:
        query: the query to search the RAG database.
        dataset_id: the dataset id to search the RAG database. 
    Returns:
        The results of the search.
    """
    print('ragflow retrieve data', dataset_id, query)
    results = ragflow.search_data(ds_id=dataset_id, top_k=5, question=query)
    print(f"ragflow results: {results}")
    return "\n".join(results)

