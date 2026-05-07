# 🎯 多AI智能会议系统

&gt; 会议级隔离 · Agent专属上下文 · 多LLM配置 · 可审计 · 流式输出 · OpenAI SDK · AI生成会议信息

---

## 📋 核心特性

### 一、会议级完全隔离
- **最高级隔离单元**：以「会议」为最高隔离级别
- **完全独立环境**：不同会议的主持人、Agent、LLM配置、上下文、日志完全隔离
- **禁止全局混存**：绝对禁止全局共享数据，确保数据安全

### 二、多LLM灵活配置
- **全局LLM客户端池**：全局复用LLM客户端实例，避免重复初始化
- **完全自定义配置**：每个LLM独立配置API Key/Base URL/Model/Temperature/Max Tokens
- **OpenAI兼容接口**：支持OpenAI/智谱/通义千问等所有OpenAI兼容接口
- **使用官方SDK**：采用openai库而非requests，更稳定可靠

### 三、AI智能生成会议信息
- **5个主题选择**：AI生成5个会议主题供选择
- **5个背景选择**：AI生成5个会议背景供选择
- **5个目标选择**：AI生成5个会议目标供选择
- **友好选择对话框**：可视化多选界面，操作简单

### 四、Agent专属上下文
- **独立上下文存储**：每个Agent拥有独立的上下文记忆，仅属于当前会议
- **自我观点记忆**：自动记录Agent的核心观点摘要（50字内）+ 关键发言记录（最多2条）
- **他人观点汇总**：保留主持人最新一轮的全场汇总，了解其他Agent的观点
- **观点一致性保证**：Agent发言前会看到自己之前的观点，避免前后矛盾
- **极致Token优化**：完全不传递原始聊天记录，只传递精简摘要信息

### 五、主持人汇总→分发精简信息
- **轮次汇总机制**：每轮讨论后可由主持人汇总核心观点
- **精简信息分发**：汇总内容自动同步到所有Agent的others_summary
- **降低Token消耗**：大幅减少Agent上下文长度，降低成本
- **提升讨论效率**：Agent聚焦关键观点，避免信息过载

### 六、完整可审计
- ✅ 所有对话/配置/操作完整保存
- ✅ 时间戳记录每一步
- ✅ 本地JSON文件存储（meetings/目录）
- ✅ 启动时自动加载已存在会议

### 七、流式逐字输出
- ✅ Flask SSE流式转发
- ✅ 前端打字机效果
- ✅ 实时显示Agent发言

---

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- npm 或 yarn

### 1. 启动后端

```bash
cd meeting-backend
pip install -r requirements.txt
python app.py
```

后端将运行在 `http://localhost:5000`

### 2. 启动前端

新开一个终端：

```bash
cd meeting-front
npm install
npm run dev
```

前端将运行在 `http://localhost:3000`

---

## 📖 完整会议流程

### 📝 完整流程示例

#### 第一步：创建会议
1. 点击页面右上角 **「+ 新建会议」** 按钮
2. 弹出创建会议对话框
3. 点击 **「下一步」** 进入会议设置

#### 第二步：设置会议（AI智能生成）
1. **选择主持人LLM**：从下拉列表中选择已配置的LLM
2. **设置主持人名称**：默认"主持人"，可修改
3. **AI生成会议信息**（推荐）：
   - 点击 **「🔮 AI生成上述会议信息」** 按钮
   - 在弹出的对话框中输入您的简单想法（比如：讨论新产品的上市策略）
   - 点击 **「🚀 开始生成」**
   - 等待AI生成5个主题、5个背景、5个目标
   - 从每个类别中选择一个您喜欢的选项
   - 点击 **「确认信息」** 按钮
   - 选中的信息会自动填到表单中
4. **手动填写**（可选）：也可以直接在表单中手动填写会议主题、背景、目标
5. 点击 **「保存设置」** 按钮

#### 第三步：配置专家
1. **配置LLM**（首次使用）：
   - 点击右上角齿轮图标 **「⚙️ 设置」**
   - 选择 **「LLM管理」** 标签
   - 点击 **「+ 新建LLM」**
   - 填写LLM信息：
     - LLM ID：唯一标识（如：openai_gpt4）
     - API Key：您的API密钥
     - Base URL：API地址（如：https://api.openai.com/v1）
     - 默认模型：模型名称（如：gpt-4）
     - 温度：0-1之间（数值越高越随机）
     - Max Tokens：最大输出长度
   - 点击 **「保存」**
2. **选择与会专家**：
   - 从左侧专家列表中勾选需要的专家
   - 可以添加新专家：
     - 点击 **「+ 添加新专家」** 按钮
     - 输入专家姓名和角色定位
     - 选择该专家使用的LLM
     - 点击 **「保存」**
   - 可以编辑已有专家：点击专家卡片上的编辑图标
3. 点击 **「下一步」**

#### 第四步：启动会议
1. 确认会议信息和专家列表无误
2. 点击 **「▶️ 启动会议」** 按钮

#### 第五步：会议进行中
1. **查看会议记录**：右侧显示实时会议记录
2. **让专家发言**：
   - 在右侧控制面板选择要发言的专家
   - 输入发言指令（可选）
   - 点击 **「让专家发言」** 按钮
   - 实时观看专家逐字发言
3. **查看当前发言**：当前发言的专家头像会高亮显示
4. **查看历史记录**：滚动查看之前的对话内容
5. **用户补充输入**：
   - 在用户输入框输入您的想法
   - 点击 **「提交」** 按钮
6. **轮次控制**：
   - 点击 **「开始下一轮」** 进入新一轮讨论

#### 第六步：结束会议
1. 点击 **「🏁 结束会议」** 按钮
2. 等待主持人自动生成会议总结
3. 查看完整的会议总结
4. 会议数据自动保存到本地

---

## 🔌 API接口文档

### 统一响应格式

```json
{
  "code": 200,
  "message": "操作说明",
  "data": {...}
}
```

### 接口列表

#### 1. POST /api/meeting/create
创建会议

**请求：**
```json
{
  "topic": "会议主题",
  "host_name": "主持人"
}
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

#### 2. GET /api/meeting/{meeting_id}
查询会议详情

**响应：**
```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "meeting_id": "...",
    "topic": "会议主题",
    "host_name": "主持人",
    "create_time": "2024-01-01 10:00:00",
    "is_running": true,
    "llm_configs": {...},
    "agents": {...},
    "discussion_log": [...],
    "summary": "",
    "round_summaries": [],
    "current_round": 0
  }
}
```

#### 3. POST /api/meeting/{meeting_id}/start
启动会议

**响应：**
```json
{
  "code": 200,
  "message": "会议已启动",
  "data": null
}
```

#### 4. POST /api/meeting/{meeting_id}/end
结束会议

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

#### 5. POST /api/meeting/{meeting_id}/llm/register
注册LLM配置

**请求：**
```json
{
  "llm_id": "openai_gpt4",
  "api_key": "sk-xxxxxxxxxxxx",
  "base_url": "https://api.openai.com/v1",
  "default_model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 2000
}
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

#### 6. POST /api/meeting/{meeting_id}/agent/create
创建Agent

**请求：**
```json
{
  "name": "产品经理",
  "role_desc": "从产品角度分析，关注用户体验",
  "llm_id": "openai_gpt4"
}
```

**响应：**
```json
{
  "code": 200,
  "message": "Agent创建成功",
  "data": {
    "agent_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "产品经理",
    "role_desc": "从产品角度分析，关注用户体验",
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

#### 7. PATCH /api/meeting/{meeting_id}/agent/{agent_id}/llm
切换Agent绑定的LLM

**请求：**
```json
{
  "llm_id": "new_llm_id"
}
```

**响应：**
```json
{
  "code": 200,
  "message": "切换成功",
  "data": null
}
```

#### 8. GET /api/meeting/{meeting_id}/agent/{agent_id}/speak
Agent流式发言（SSE接口）

**参数：**
- `instruction`: 发言指令（Query参数）

**SSE事件流：**
```
data: {"type": "start"}

data: {"type": "content", "content": "我"}

data: {"type": "content", "content": "认为"}

data: {"type": "end", "content": "我认为用户留存率低的主要原因是..."}
```

#### 9. GET /api/meeting/{meeting_id}/summary
获取会议总结

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

#### 10. POST /api/meeting/{meeting_id}/round-summary
提交轮次汇总

**请求：**
```json
{
  "summary": "本轮讨论达成以下共识：1. 优化登录流程；2. 增加个性化推荐..."
}
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

#### 11. POST /generate-meeting-info
AI生成会议信息（多选项）

**请求：**
```json
{
  "llm_id": "openai_gpt4",
  "user_input": "讨论新产品的上市策略"
}
```

**响应：**
```json
{
  "code": 200,
  "message": "生成成功",
  "data": {
    "topics": [
      "2024年Q2新品上市战略规划",
      "新产品市场推广与用户增长方案",
      "产品发布会与营销活动策划",
      "竞品分析与差异化定位",
      "产品上市风险评估与应对策略"
    ],
    "backgrounds": [
      "公司将于2024年Q2推出一款全新的智能产品，为确保产品成功上市...",
      "当前市场竞争激烈，需要制定一套完整的上市策略来抢占市场份额...",
      ...
    ],
    "goals": [
      "明确产品定位和目标用户群体，制定差异化竞争策略",
      "制定详细的市场推广计划，确保产品上市首月达成销售目标...",
      ...
    ]
  }
}
```

---

## 📁 项目结构

```
AIMeeting/
├── meeting-backend/
│   ├── app.py              # Flask后端主文件
│   ├── requirements.txt    # Python依赖
│   ├── meetings/           # 会议JSON文件存储目录
│   └── API_EXAMPLES.md     # API示例文档
└── meeting-front/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── main.js
        ├── App.vue         # Vue主组件
        └── assets/style.css
        └── router/index.js
└── README.md
```

---

## 🎓 核心设计亮点

### 1. 数据结构设计（使用dataclasses）
- **Meeting**：会议隔离单元，包含所有会议相关数据
- **LLMConfig**：LLM配置，独立于会议
- **Agent**：Agent实体，包含专属上下文
- **AgentContext**：Agent专属上下文，包含核心摘要、关键记录、他人汇总
- **DiscussionLogEntry**：审计日志条目
- **MeetingSystemManager**：全局单例管理器

### 2. LLM客户端池
- 全局单例模式管理所有LLM客户端
- 避免重复初始化，节省资源
- 支持跨会议复用LLM配置

### 3. AI生成会议信息
- 智能生成5个主题、5个背景、5个目标
- 友好的多选对话框界面
- 用户选择后自动填充表单
- 支持手动修改

### 4. Agent上下文管理
- 发言后自动生成自我摘要（50字内）
- 保留最近2条关键发言记录
- 轮次汇总自动同步到所有Agent
- 观点一致性保证

### 5. 会议持久化
- 自动保存到meetings/目录
- JSON格式，便于审计和调试
- 启动时自动加载已存在会议

### 6. 异常处理和重试
- 30秒超时设置
- 完善的异常捕获和用户友好提示
- 使用openai官方SDK，更稳定可靠

---

## ⚠️ 注意事项

1. **API Key安全**：不要将API Key提交到代码仓库
2. **Base URL格式**：使用openai库时，base_url只需到v1级别（如https://api.openai.com/v1），无需包含chat/completions
3. **网络连接**：确保能访问配置的LLM API
4. **存储目录**：确保后端有write权限创建meetings目录
5. **浏览器兼容性**：建议使用Chrome/Edge/Firefox最新版本
6. **CORS配置**：后端已配置CORS，支持跨域请求

---

## 📝 更新日志

### v6.0 (最新)
- ✨ 新增AI生成会议信息功能（5个主题、5个背景、5个目标）
- ✨ 新增友好的多选对话框界面
- ✨ 重构创建会议流程，分为4个清晰步骤
- ✨ 优化用户体验，按钮位置和交互更合理

### v5.0
- 🔧 将LLM连接从requests库改为openai官方SDK
- 🔧 调整base_url格式要求，使用openai库标准格式
- ✨ 完全重构后端架构，采用dataclasses数据结构
- ✨ 实现会议级完全隔离
- ✨ 实现LLM客户端池全局管理
- ✨ 实现Agent专属上下文记忆功能
- ✨ 实现轮次汇总机制
- ✨ 重构前端UI，适配新API
- ✨ 完整的审计日志功能

---

## 🤝 技术栈

**后端：**
- Flask (Web框架)
- Flask-CORS (跨域支持)
- openai (LLM官方SDK)

**前端：**
- Vue 2 (选项式API)
- Element UI (组件库)
- Axios (HTTP客户端)
- Vite (构建工具)

---

**祝您使用愉快！如有问题请查看审计日志或后端控制台。** 🚀
