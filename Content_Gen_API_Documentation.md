# RagFlow API 接口文档

## 1. List Datasets 获取现有数据集

**Request**
- **Method:** GET  
- **URL:** `/api/v1/datasets?page={page}&page_size={page_size}&orderby={orderby}&desc={desc}&name={dataset_name}&id={dataset_id}`  
- **Headers:**  
  `Authorization: Bearer <YOUR_API_KEY>`

**Example**
```bash
curl --request GET      --url http://117.50.221.99:8080/api/v1/datasets?page=1&page_size=100&orderby=update_time&desc=true      --header 'Authorization: Bearer ragflow-kzZTdhZDE2YjNjYTExZjA4ZTc4MjI3MT'
```

**失败响应**
```json
{
    "code": 102,
    "message": "The dataset doesn't exist"
}
```

**成功响应**
```json
{
    "code": 0,
    "data": [
        {
            "id": "6e211ee0723611efa10a0242ac120007",
            "name": "mysql",
            "chunk_count": 59,
            "document_count": 1,
            "embedding_model": "BAAI/bge-large-zh-v1.5",
            "update_date": "Thu, 10 Oct 2024 04:07:23 GMT"
        }
    ],
    "total": 1
}
```

> 关键字段：`name`, `id`

---

## 2. Upload Documents 上传文档

**Request**
- **Method:** POST  
- **URL:** `/api/v1/datasets/{dataset_id}/documents`  
- **Headers:**  
  `Content-Type: multipart/form-data`  
  `Authorization: Bearer <YOUR_API_KEY>`  
- **Form:**  
  `file=@{FILE_PATH}`

**Example**
```bash
curl --request POST      --url http://117.50.221.99:8080/api/v1/datasets/{dataset_id}/documents      --header 'Content-Type: multipart/form-data'      --header 'Authorization: Bearer ragflow-kzZTdhZDE2YjNjYTExZjA4ZTc4MjI3MT'      --form 'file=@./test1.txt'      --form 'file=@./test2.pdf'
```

**失败响应**
```json
{
    "code": 101,
    "message": "No file part!"
}
```

**成功响应**
```json
{
    "code": 0,
    "data": [
        {
            "id": "b330ec2e91ec11efbc510242ac120004",
            "dataset_id": "527fa74891e811ef9c650242ac120006",
            "name": "1.txt",
            "size": 17966,
            "type": "doc"
        }
    ]
}
```

> 关键字段：文档 `id`

---

## 3. Parse Documents 解析文档

**Request**
- **Method:** POST  
- **URL:** `/api/v1/datasets/{dataset_id}/chunks`  
- **Headers:**  
  `Content-Type: application/json`  
  `Authorization: Bearer <YOUR_API_KEY>`  
- **Body:**  
  `"document_ids": list[string]`

**Example**
```bash
curl --request POST      --url http://117.50.221.99:8080/api/v1/datasets/{dataset_id}/chunks      --header 'Content-Type: application/json'      --header 'Authorization: Bearer ragflow-kzZTdhZDE2YjNjYTExZjA4ZTc4MjI3MT'      --data '{
         "document_ids": ["97a5f1c2759811efaa500242ac120004","97ad64b6759811ef9fc30242ac120004"]
     }'
```

**失败响应**
```json
{
    "code": 102,
    "message": "`document_ids` is required"
}
```

**成功响应**
```json
{ "code": 0 }
```

---

## 4. Delete Documents 删除文档

**Request**
- **Method:** DELETE  
- **URL:** `/api/v1/datasets/{dataset_id}/documents`  
- **Headers:**  
  `Content-Type: application/json`  
  `Authorization: Bearer <YOUR_API_KEY>`  
- **Body:**  
  `"ids": list[string]`

**Example**
```bash
curl --request DELETE      --url http://117.50.221.99:8080/api/v1/datasets/{dataset_id}/documents      --header 'Content-Type: application/json'      --header 'Authorization: Bearer ragflow-kzZTdhZDE2YjNjYTExZjA4ZTc4MjI3MT'      --data '{
         "ids": ["id_1","id_2"]
     }'
```

---

## 5. List Documents 列出数据集中的所有文档

**Request**
- **Method:** GET  
- **URL:** `/api/v1/datasets/{dataset_id}/documents?page={page}&page_size={page_size}&orderby={orderby}&desc={desc}&keywords={keywords}&id={document_id}&name={document_name}`  
- **Headers:**  
  `Content-Type: application/json`  
  `Authorization: Bearer <YOUR_API_KEY>`

**Example**
```bash
curl --request GET      --url http://117.50.221.99:8080/api/v1/datasets/{dataset_id}/documents?page=1&page_size=10      --header 'Authorization: Bearer ragflow-kzZTdhZDE2YjNjYTExZjA4ZTc4MjI3MT'
```

**成功响应**
```json
{
    "code": 0,
    "data": {
        "docs": [
            {
                "id": "3bcfbf8a8a0c11ef8aba0242ac120006",
                "name": "Test_2.txt",
                "run": "UNSTART",
                "size": 7,
                "status": "1",
                "type": "doc"
            }
        ],
        "total_datasets": 1
    }
}
```

**失败响应**
```json
{
    "code": 102,
    "message": "You don't own the dataset 7898da028a0511efbf750242ac1220005."
}
```

---

## 6. Chat with Bot 与智能体聊天

**Request**
- **Method:** GET  
- **URL:** `/query/`  
- **Params:**  
  - `original_query`: 用户输入（必需）
  - `dataset_id`: 知识库数据集 ID（必需，来自用户企业表格，用户属于什么企业，该企业可以访问哪些数据集id）
  - `user_id`: 用户 ID（可选，默认值：`User_A`）
  - `thread_id`: 会话 ID（必需）
  - `do_web_search`: 回答问题前是否调用网络搜索（可选，默认值：`True`）

**Example**
```bash
curl -N -H "Accept: text/event-stream" \
  -G "http://117.50.221.99:8190/query/" \
  --data-urlencode "original_query=给扫地机器人做个宣传文案" \
  --data-urlencode "dataset_id=4b8c848eb31011f08b4c22715a4cef8f" \
  --data-urlencode "user_id=User_A" \
  --data-urlencode "thread_id=333"

curl -N -H "Accept: text/event-stream" \
  -G "http://127.0.0.1:8190/query/" \
  --data-urlencode "original_query=名称是清芬牌吹风机，受众是家庭主妇，主要功能是负离子护发、快速干发，智能恒温" \
  --data-urlencode "dataset_id=4b8c848eb31011f08b4c22715a4cef8f" \
  --data-urlencode "user_id=User_A" \
  --data-urlencode "thread_id=333"

curl -N -H "Accept: text/event-stream" \
  -G "http://117.50.221.99:8190/query/" \
  --data-urlencode "original_query=小旋风扫地机器人，受众是家庭主妇，主要卖点是智能导航、大吸力，噪音小" \
  --data-urlencode "dataset_id=4b8c848eb31011f08b4c22715a4cef8f" \
  --data-urlencode "user_id=User_A" \
  --data-urlencode "thread_id=333"

```

**成功响应**
> 以 Server-Sent Events (SSE) 格式分段返回智能体的回复，媒体类型为 `text/event-stream`。

**失败响应**
```json
{
  "detail": "错误信息"
}
```

---

## 7. Upload User Fact 上传用户事实

**Request**
- **Method:** POST
- **URL:** `/upload_user_fact`
- **Params:**
  - `user_id`: 用户 ID（Query 参数，可选，默认值：`User_A`）
  - `user_fact`: 用户事实信息（Form 参数，必需）

**Example**
```bash
curl -X POST "http://127.0.0.1:8188/upload_user_fact?user_id=User_A" \
  -F "user_fact=一个37岁的女人，希望保持青春靓丽"
```

**成功响应**
```json
{
  "message": "User fact uploaded to global info successfully"
}
```

**说明**
- 用户事实信息会保存到 Redis（键名：`chat:user_fact:{user_id}`）
- 多条事实会追加保存，每条记录包含时间戳
- 如果 Redis 不可用，会回退到本地文件保存

---

## 8. Upload User Like or Not 上传用户喜欢/不喜欢反馈

**Request**
- **Method:** POST
- **URL:** `/upload_user_like_ornot`
- **Params:**
  - `user_id`: 用户 ID（Query 参数，必需）
  - `user_like_ornot_reason`: 上轮对话+喜欢/不喜欢的原因（Form 参数，必需）

**Example**
```bash
curl -X POST "http://127.0.0.1:8188/upload_user_like_ornot?user_id=User_A" \
  -F "user_like_ornot_reason=上轮对话：用户：我想咨询医美 AI回复：知识库里没查到。用户不喜欢回答，因为太简短了"
```

**成功响应**
```json
{
  "message": "User like or not feedback uploaded successfully"
}
```

**说明**
- 用户反馈会保存到 Redis（键名：`chat:user_like_ornot:{user_id}`）
- 多条反馈会追加保存，每条记录包含时间戳
- 如果 Redis 不可用，会回退到本地文件保存

---

## 9. Delete Session History 删除会话历史 ---慎用，可以暂时不弄

**Request**
- **Method:** POST
- **URL:** `/delete_session_history`
- **Params:**
  - `user_id`: 用户 ID（Query 参数，必需）
  - `session_id`: 会话 ID（Query 参数，必需）

**Example**
```bash
curl -X POST "http://127.0.0.1:8188/delete_session_history?user_id=User_A&session_id=333"
```

**成功响应**
```json
{
  "message": "History for session_id=333 and user_id=User_A deleted.",
  "result": {
    "redis": true,
    "file": true,
    "memory": true
  }
}
```

**说明**
- 会删除指定用户和会话的 Redis 数据（`chat:summary:{user_id}:{session_id}` 和 `chat:history:{user_id}:{session_id}`）
- 同时删除本地文件（如果存在）
- 清空内存中的会话数据

---

## 10. 查看 Redis 数据

以下命令可用于查看 Redis 中保存的数据：

**查看用户事实**
```bash
redis-cli --raw GET chat:user_fact:User_A
```

**查看用户反馈**
```bash
redis-cli --raw GET chat:user_like_ornot:User_A
```

**查看会话摘要**
```bash
redis-cli --raw GET chat:summary:User_A:333
```

**查看会话历史**
```bash
redis-cli --raw GET chat:history:User_A:333
```

**批量查看所有会话摘要**
```bash
redis-cli --raw KEYS chat:summary:User_A:*
```

**批量查看所有会话历史**
```bash
redis-cli --raw KEYS chat:history:User_A:*
```
