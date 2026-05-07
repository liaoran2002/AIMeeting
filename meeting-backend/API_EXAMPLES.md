# API示例调用文档

## 基础信息

- 后端地址：`http://localhost:5000`
- 统一响应格式：
```json
{
  "code": 200,
  "message": "操作说明",
  "data": {...}
}
```

---

## 完整流程示例

### 1. 创建会议

```bash
curl -X POST http://localhost:5000/api/meeting/create \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "如何提升用户留存率",
    "host_name": "主持人"
  }'
```

**响应：**
```json
{
  "code": 200,
  "message": "创建成功",
  "data": {
    "meeting_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

### 2. 注册LLM配置

```bash
curl -X POST http://localhost:5000/api/meeting/{meeting_id}/llm/register \
  -H "Content-Type: application/json" \
  -d '{
    "llm_id": "openai_gpt4",
    "api_key": "sk-xxxxxxxxxxxx",
    "base_url": "https://api.openai.com/v1",
    "default_model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
  }'
```

**响应：**
```json
{
  "code": 200,
  "message": "LLM注册成功",
  "data": {
    "llm_id": "openai_gpt4"
  }
}
```

---

### 3. 创建Agent

```bash
curl -X POST http://localhost:5000/api/meeting/{meeting_id}/agent/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "产品经理",
    "role_desc": "从产品角度分析，关注用户体验和功能完整性",
    "llm_id": "openai_gpt4"
  }'
```

**响应：**
```json
{
  "code": 200,
  "message": "Agent创建成功",
  "data": {
    "agent_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "产品经理",
    "role_desc": "从产品角度分析，关注用户体验和功能完整性",
    "llm_id": "openai_gpt4",
    "context": {
      "core_summary": "",
      "key_records": [],
      "others_summary": ""
    },
    "speech_history": []
  }
}
```

---

### 4. 启动会议

```bash
curl -X POST http://localhost:5000/api/meeting/{meeting_id}/start
```

**响应：**
```json
{
  "code": 200,
  "message": "会议已启动",
  "data": null
}
```

---

### 5. Agent流式发言（SSE）

```javascript
// 使用JavaScript调用示例
const eventSource = new EventSource(
  'http://localhost:5000/api/meeting/{meeting_id}/agent/{agent_id}/speak?instruction=请分析用户留存率低的原因'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'start') {
    console.log('开始发言...');
  } else if (data.type === 'content') {
    process.stdout.write(data.content);
  } else if (data.type === 'end') {
    console.log('\n发言结束');
    eventSource.close();
  }
};
```

**SSE事件格式：**
```
data: {"type": "start"}

data: {"type": "content", "content": "我认为"}

data: {"type": "content", "content": "用户留存率"}

data: {"type": "end", "content": "我认为用户留存率低的主要原因是..."}
```

---

### 6. 切换Agent绑定的LLM

```bash
curl -X PATCH http://localhost:5000/api/meeting/{meeting_id}/agent/{agent_id}/llm \
  -H "Content-Type: application/json" \
  -d '{
    "llm_id": "another_llm_id"
  }'
```

**响应：**
```json
{
  "code": 200,
  "message": "切换成功",
  "data": null
}
```

---

### 7. 提交轮次汇总

```bash
curl -X POST http://localhost:5000/api/meeting/{meeting_id}/round-summary \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "本轮讨论达成以下共识：1. 优化登录流程；2. 增加个性化推荐..."
  }'
```

**响应：**
```json
{
  "code": 200,
  "message": "汇总成功",
  "data": {
    "round_number": 1
  }
}
```

---

### 8. 查询会议详情

```bash
curl http://localhost:5000/api/meeting/{meeting_id}
```

**响应包含完整会议信息：**
```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "meeting_id": "...",
    "topic": "如何提升用户留存率",
    "host_name": "主持人",
    "create_time": "2024-01-01 10:00:00",
    "is_running": true,
    "llm_configs": {...},
    "agents": {...},
    "discussion_log": [...],
    "summary": "",
    "round_summaries": [],
    "current_round": 1
  }
}
```

---

### 9. 获取会议总结

```bash
curl http://localhost:5000/api/meeting/{meeting_id}/summary
```

**响应：**
```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "summary": "会议总结内容..."
  }
}
```

---

### 10. 结束会议

```bash
curl -X POST http://localhost:5000/api/meeting/{meeting_id}/end
```

**响应：**
```json
{
  "code": 200,
  "message": "会议已结束",
  "data": {
    "summary": "完整的会议总结..."
  }
}
```

---

## Python示例代码

```python
import requests
import json

BASE_URL = "http://localhost:5000"

# 1. 创建会议
response = requests.post(f"{BASE_URL}/api/meeting/create", json={
    "topic": "如何提升用户留存率",
    "host_name": "主持人"
})
meeting_id = response.json()["data"]["meeting_id"]
print(f"会议ID: {meeting_id}")

# 2. 注册LLM
requests.post(f"{BASE_URL}/api/meeting/{meeting_id}/llm/register", json={
    "llm_id": "my_llm",
    "api_key": "your-api-key",
    "base_url": "https://api.openai.com/v1",
    "default_model": "gpt-3.5-turbo"
})

# 3. 创建Agent
agent_response = requests.post(f"{BASE_URL}/api/meeting/{meeting_id}/agent/create", json={
    "name": "产品经理",
    "role_desc": "从产品角度分析",
    "llm_id": "my_llm"
})
agent_id = agent_response.json()["data"]["agent_id"]

# 4. 启动会议
requests.post(f"{BASE_URL}/api/meeting/{meeting_id}/start")

# 5. 查询会议
meeting = requests.get(f"{BASE_URL}/api/meeting/{meeting_id}").json()
print(json.dumps(meeting, indent=2, ensure_ascii=False))
```

---

## 注意事项

1. 所有接口中的 `{meeting_id}` 和 `{agent_id}` 需要替换为实际ID
2. SSE流式接口建议使用EventSource或类似的SSE客户端
3. LLM的base_url只需包含到v1级别（如 https://api.openai.com/v1），无需包含chat/completions路径
4. 会议数据自动保存到 `meetings/` 目录下的JSON文件
5. 系统启动时会自动加载已存在的会议数据
