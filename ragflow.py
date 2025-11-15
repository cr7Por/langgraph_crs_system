import uuid
from typing import List, Optional, Union

import numpy as np
import os
import requests

DEFAULT_COLLECTION_NAME = "deepsearcher"

TEXT_PAYLOAD_KEY = "text"
REFERENCE_PAYLOAD_KEY = "reference"
METADATA_PAYLOAD_KEY = "metadata"


class Ragflow(): 
    """Vector DB implementation powered by [Ragflow](https://ragflow.com/)"""
    
    def search_data(
        self,
        ds_id: str,
        top_k: int = 5,
        question: str = "Search query",
    ) -> List[str]:
        """
        Search for similar vectors in a Ragflow collection.

        Args:
            ds_id (Optional[str]): Dataset id.
            vector (Union[np.array, List[float]]): Query vector for similarity search.
            top_k (int, optional): Number of results to return. Defaults to 5.

        Returns:
            List[str]: List of retrieval results containing similar vectors.
        """
        try:
            
            if not ds_id:
                print(f"no dataset_id")
                return []
            
            address = "117.50.221.99:8080"
            api_key = os.getenv("RAGFlow_API_KEY", "ragflow-kzZTdhZDE2YjNjYTExZjA4ZTc4MjI3MT")
            url = f"http://{address}/api/v1/retrieval"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            payload = {
                "question": question,
                "dataset_ids": [ds_id],
                #"document_ids": ["77df9ef4759a11ef8bdd0242ac120004"]
            }
            #print(payload)
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise Exception(f"Ragflow search failed: {response.text}")
            
            response_data = response.json()
            #print(response_data)
            results = []
            
            if response_data.get("code") == 0 and "data" in response_data:
                data = response_data["data"]
                if "chunks" in data:
                    for chunk in data["chunks"]:
                        #print(chunk)
                        results.append(chunk.get("content", ""))
            #print(results)
            return results
        except Exception as e:
            print(f"Failed to search data, error info: {e}")
            return []

    def list_collections(self, *args, **kwargs) -> List[dict]:
        """
        List all collections in the Qdrant database.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            List[dict]: List of collection information objects.
        """

        try:
            address = "117.50.221.99:8080"
            page = 1
            page_size = 100
            orderby = "update_time"
            desc = "true"
            dataset_name = ""
            dataset_id = ""
            api_key = os.getenv("RAGFlow_API_KEY", "ragflow-kzZTdhZDE2YjNjYTExZjA4ZTc4MjI3MT")

            # Build URL with only non-empty parameters
            params = {
                "page": page,
                "page_size": page_size,
                "desc": desc
            }
            
            # Only add optional parameters if they are not empty
            if orderby:
                params["orderby"] = orderby
            if dataset_name:
                params["name"] = dataset_name
            if dataset_id:
                params["id"] = dataset_id
                
            # Build query string
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"http://{address}/api/v1/datasets?{query_string}"
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            response = requests.get(url, headers=headers)
            #print(response.status_code, response.text)
            if response.status_code == 200:
                datasets = response.json().get("data", [])
            else:
                log.critical(f"Failed to fetch collections, status code: {response.status_code}, response: {response.text}")
                datasets = []
            
            results = []
            for dataset in datasets:
                # Check if CollectionInfo accepts dataset_id parameter
                results.append({"name": dataset["name"], "id": dataset["id"], "description": dataset["description"]})
            return results
        except Exception as e:
            log.critical(f"Failed to list collections, error info: {e}")
            return []

if __name__ == "__main__":
    ragflow = Ragflow()
    #print(ragflow.list_collections())
    print(ragflow.search_data(ds_id="4b8c848eb31011f08b4c22715a4cef8f", top_k=5, question="需要确认的事项"))
    #print(ragflow.search_data(ds_id="25b4fb90b30d11f0bdca22715a4cef8f", top_k=5, question="有哪些机会"))