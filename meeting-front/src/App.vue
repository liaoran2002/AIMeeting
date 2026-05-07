<template>
  <div class="app-container">
    <el-container class="main-container">
      <!-- 左侧：会议列表 -->
      <el-aside :width="sidebarCollapsed ? '64px' : '280px'" class="sidebar" :class="{ collapsed: sidebarCollapsed }">
        <div class="sidebar-header">
          <h1 v-if="!sidebarCollapsed"><a style="color: #fff; text-decoration: none;"  href="/">🎯 多AI专家会议系统</a></h1>
          <h1 v-else><a style="color: #fff; text-decoration: none;"  href="/">🎯</a></h1>
        </div>
        
        <div class="sidebar-content">
          <!-- 新会议按钮 -->
          <div class="new-meeting-btn">
            <el-button 
              type="primary" 
              :size="sidebarCollapsed ? 'medium' : 'medium'" 
              :circle="sidebarCollapsed"
              :icon="sidebarCollapsed ? 'el-icon-plus' : 'el-icon-plus'"
              @click="createNewMeeting"
              :loading="creating"
              :style="sidebarCollapsed ? 'width: 100%; padding: 12px 0;' : 'width: 100%;'"
            >
              <span v-if="!sidebarCollapsed">新会议</span>
            </el-button>
          </div>
          
          <el-divider v-if="!sidebarCollapsed"></el-divider>
          
          <!-- 会议列表 -->
          <div class="meeting-list-section" v-if="!sidebarCollapsed">
            <div class="list-title">历史会议</div>
            <div class="meeting-list">
              <div 
                v-for="m in meetingList" 
                :key="m.meeting_id"
                :class="['meeting-item', { active: m.meeting_id === currentMeetingId }]"
              >
                <div class="meeting-item-main" @click="switchToMeeting(m.meeting_id)">
                  <div class="meeting-item-title" :title="m.topic">
                    {{ m.topic }}
                  </div>
                  <div class="meeting-item-meta">
                    <span class="meeting-item-time">{{ formatTime(m.create_time) }}</span>
                    <el-tag v-if="m.is_running" type="success" size="mini">进行中</el-tag>
                    <el-tag v-else-if="m.has_summary" type="info" size="mini">已结束</el-tag>
                  </div>
                </div>
                <div class="meeting-item-delete" @click.stop="openDeleteConfirm(m)">
                  <i class="el-icon-delete"></i>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 收缩状态的会议列表（只显示图标） -->
          <div class="meeting-list-section-collapsed" v-if="sidebarCollapsed">
            <div 
              v-for="m in meetingList" 
              :key="m.meeting_id"
              :class="['meeting-item-collapsed', { active: m.meeting_id === currentMeetingId }]"
              @click="switchToMeeting(m.meeting_id)"
              :title="m.topic"
            >
              <span v-if="m.is_running" class="status-dot running"></span>
              <span v-else-if="m.has_summary" class="status-dot ended"></span>
              <span v-else class="status-dot pending"></span>
            </div>
          </div>
        </div>
        
        <!-- 底部设置按钮 -->
        <div class="sidebar-footer">
          <div class="settings-btn" @click="openSettingsDialog">
            <i class="el-icon-setting"></i>
            <span v-if="!sidebarCollapsed">设置</span>
          </div>
        </div>
      </el-aside>
      
      <!-- 右侧：主内容区 -->
      <el-main class="main-content">
        <!-- 欢迎页面：没有选择会议时 -->
        <div v-if="!currentMeetingId" class="welcome-page">
          <div class="welcome-content">
            <div class="welcome-icon">💡</div>
            <h2>开始一场AI智能会议</h2>
            <p class="welcome-desc">多专家协同讨论 · 完整会议记录 · 自动总结</p>
            <el-button type="primary" size="large" @click="createNewMeeting" :loading="creating">
              创建新会议
            </el-button>
          </div>
        </div>
        
        <!-- 会议内容区 -->
        <div v-else class="meeting-page">
          <!-- 顶部：会议信息栏 -->
          <div class="meeting-header-bar">
            <div class="collapse-btn-meeting" @click="sidebarCollapsed = !sidebarCollapsed">
              <i :class="sidebarCollapsed ? 'el-icon-s-unfold' : 'el-icon-s-fold'"></i>
            </div>
            <div class="meeting-title">{{ currentMeeting?.topic || '会议' }}</div>
            <div class="meeting-status">
              <el-tag v-if="currentMeeting?.is_running" type="success">进行中</el-tag>
              <el-tag v-else-if="currentMeeting?.summary" type="info">已结束</el-tag>
              <el-tag v-else type="warning">待启动</el-tag>
            </div>
          </div>
          
          <div class="meeting-content-container">
            <!-- 会议前内容（步骤1-5） -->
            <div v-if="!currentMeeting?.is_running && !currentMeeting?.summary" class="pre-meeting-container">
              <!-- 步骤1：注册LLM -->
              <div v-if="currentStep === 1" class="panel-section-center">
                <div class="section-title">⚙️ 步骤1：{{ editingLLMId ? '编辑' : '注册' }}LLM</div>
                <el-form :model="llmForm" label-width="80px" size="small">
                  <el-form-item label="LLM ID">
                    <el-input v-model="llmForm.llm_id" placeholder="例如: openai_gpt4" :disabled="!!editingLLMId"></el-input>
                  </el-form-item>
                  <el-form-item label="API Key">
                    <input 
                      v-if="editingLLMId" 
                      type="text" 
                      :value="maskApiKeyFull(llmForm.api_key)" 
                      readonly 
                      class="readonly-input"
                    >
                    <el-input 
                      v-else 
                      v-model="llmForm.api_key" 
                      type="password" 
                      show-password 
                      placeholder="sk-..."
                    >
                    </el-input>
                  </el-form-item>
                  <el-form-item label="Base URL">
                    <el-input v-model="llmForm.base_url" placeholder="https://api.openai.com/v1"></el-input>
                  </el-form-item>
                  <el-form-item label="Model">
                    <el-input v-model="llmForm.default_model" placeholder="gpt-4"></el-input>
                  </el-form-item>
                  <el-form-item label="Temperature">
                    <div style="display: flex; align-items: center; gap: 10px;">
                      <el-slider v-model="llmForm.temperature" :min="0" :max="1" :step="0.1" :show-tooltip="false" style="flex: 1;"></el-slider>
                      <span style="min-width: 40px; font-family: Consolas, monospace; color: #667eea; font-weight: 600;">{{ llmForm.temperature.toFixed(1) }}</span>
                    </div>
                  </el-form-item>
                  <el-form-item label="Max Tokens">
                    <el-input-number v-model="llmForm.max_tokens" :min="100" :max="4000" :step="100" style="width:100%"></el-input-number>
                  </el-form-item>
                  <el-button v-if="editingLLMId" @click="cancelEditMeetingLLM" style="width:48%">取消</el-button>
                  <el-button :type="editingLLMId ? 'primary' : 'success'" @click="registerLLM" :loading="registering" :style="{ width: editingLLMId ? '48%' : '100%' }">{{ editingLLMId ? '更新' : '注册' }}LLM</el-button>
                </el-form>
                
                <div v-if="llmConfigs.length > 0" class="list-section">
                  <div class="section-title-small">已注册LLM ({{ llmConfigs.length }})</div>
                  <div v-for="llm in llmConfigs" :key="llm.llm_id" class="list-item-small">
                    <span class="item-name">{{ llm.llm_id }}</span>
                    <div>
                      <el-button type="primary" size="mini" @click="editLLM(llm)" style="margin-right: 8px;">编辑</el-button>
                      <el-button type="danger" size="mini" @click="removeLLM(llm.llm_id)">删除</el-button>
                    </div>
                  </div>
                </div>
                
                <el-divider v-if="llmConfigs.length > 0"></el-divider>
                
                <div v-if="llmConfigs.length > 0" class="control-buttons">
                  <el-button type="primary" @click="goToNextStep" style="width:100%">下一步</el-button>
                </div>
              </div>
              
              <!-- 步骤2：选择主持人和填写会议信息 -->
              <div v-else-if="currentStep === 2" class="panel-section-center">
                <div class="section-title">📝 步骤2：设置会议</div>
                <el-form :model="meetingForm" label-width="80px" size="small">
                  <el-form-item label="主持人LLM">
                    <el-select v-model="meetingForm.host_llm_id" placeholder="选择主持人LLM" style="width:100%">
                      <el-option v-for="llm in llmConfigs" :key="llm.llm_id" :label="llm.llm_id" :value="llm.llm_id"></el-option>
                    </el-select>
                  </el-form-item>
                  <el-form-item label="主持人名称">
                    <el-input v-model="meetingForm.host_name" placeholder="主持人"></el-input>
                  </el-form-item>
                  <el-form-item label="会议主题">
                    <el-input v-model="meetingForm.topic" placeholder="请输入会议主题"></el-input>
                  </el-form-item>
                  <el-form-item label="会议背景">
                    <el-input type="textarea" v-model="meetingForm.meeting_background" :rows="3" placeholder="请输入会议背景"></el-input>
                  </el-form-item>
                  <el-form-item label="会议目标">
                    <el-input type="textarea" v-model="meetingForm.meeting_goal" :rows="3" placeholder="请输入会议目标"></el-input>
                  </el-form-item>
                </el-form>
                
                <el-button 
                  type="primary" 
                  @click="openMeetingInfoDialog" 
                  :disabled="!meetingForm.host_llm_id"
                  style="width:100%; margin-bottom: 16px;"
                >
                  🔮 AI生成上述会议信息
                </el-button>
                
                <div class="control-buttons">
                  <el-button @click="goToPrevStep" style="width:48%">上一步</el-button>
                  <el-button type="primary" @click="updateMeetingInfo" :loading="updating" style="width:48%">保存设置</el-button>
                </div>
              </div>
              
              <!-- 步骤3：生成专家 -->
              <div v-else-if="currentStep === 3" class="panel-section-center">
                <div class="section-title">🤖 步骤3：生成与会专家</div>
                <el-alert
                  title="基于您的会议主题、背景和目标，AI将自动生成合适的专家角色。"
                  type="info"
                  :closable="false"
                  show-icon
                ></el-alert>
                <div class="control-buttons" style="margin-top: 16px;">
                  <el-button @click="goToPrevStep" style="width:48%">上一步</el-button>
                  <el-button type="primary" @click="generateExperts" :loading="generating" style="width:48%">生成专家</el-button>
                </div>
              </div>
              
              <!-- 步骤4：选择专家 -->
              <div v-else-if="currentStep === 4" class="panel-section-center">
                <div class="section-title">👥 步骤4：选择与会专家</div>
                <div class="expert-list">
                  <div v-for="(expert, index) in currentMeeting.generated_experts" :key="index" class="expert-item">
                    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                      <el-checkbox v-model="selectedExpertIndices" :label="index">
                        <strong>{{ expert.name }}</strong>
                      </el-checkbox>
                    </div>
                    <p class="expert-desc">{{ expert.role_desc }}</p>
                    <div style="display: flex; align-items: center; gap: 12px; margin-top: 12px;">
                      <el-button 
                        type="text" 
                        icon="el-icon-edit" 
                        size="small"
                        @click="openGeneratedExpertEditDialog(expert, index)"
                      >编辑专家描述</el-button>
                      <el-select 
                        v-if="selectedExpertIndices.includes(index)" 
                        v-model="expertLLMMap[index]" 
                        placeholder="选择LLM" 
                        size="small"
                        style="width: 150px;"
                      >
                        <el-option 
                          v-for="llm in llmConfigs" 
                          :key="llm.llm_id" 
                          :label="llm.llm_id" 
                          :value="llm.llm_id"
                        ></el-option>
                      </el-select>
                    </div>
                  </div>
                </div>
                <div class="control-buttons">
                  <el-button @click="goToPrevStep" style="width:48%">上一步</el-button>
                  <el-button type="primary" @click="selectExperts" :loading="selecting" style="width:48%">确认选择</el-button>
                </div>
              </div>
              
              <!-- 步骤5：启动会议 -->
              <div v-else-if="currentStep === 5" class="panel-section-center">
                <div class="section-title">🎬 步骤5：启动会议</div>
                <el-alert
                  title="会议准备就绪，点击启动开始讨论！"
                  type="success"
                  :closable="false"
                  show-icon
                ></el-alert>
                <div class="control-buttons" style="margin-top: 16px;">
                  <el-button @click="goToPrevStep" style="width:48%">上一步</el-button>
                  <el-button type="primary" @click="startMeetingWithConfirm" :loading="starting" style="width:48%">▶️ 启动会议</el-button>
                </div>
              </div>
            </div>
            
            <!-- 会议中 -->
            <div v-else class="in-meeting-container">
              <!-- 会议总结显示 -->
              <div v-if="currentMeeting?.summary" class="summary-section">
                <div class="summary-title">📄 会议总结</div>
                <div class="summary-content">{{ currentMeeting.summary }}</div>
              </div>
              
              <!-- 讨论日志 -->
              <div class="messages-container" ref="messagesContainer">
                <div v-for="(log, index) in displayLogs" :key="index" :class="['message-item', log.type]">
                  <div class="message-avatar">
                    <span v-if="log.type === 'system'">⚙️</span>
                    <span v-else-if="log.type === 'round_summary'">📝</span>
                    <span v-else-if="log.type === 'summary'">📄</span>
                    <div v-else class="message-avatar-circle">{{ getAvatarText(log.speaker) }}</div>
                  </div>
                  <div class="message-content">
                    <div class="message-header">
                      <span class="message-name">{{ log.speaker }}</span>
                      <span v-if="log.type === 'round_summary'" class="tag-round">轮次汇总</span>
                      <span v-if="log.type === 'summary'" class="tag-summary">会议总结</span>
                      <span class="message-time">{{ log.timestamp }}</span>
                    </div>
                    <div class="message-text markdown-body" v-html="renderMarkdown(log.content)"></div>
                  </div>
                </div>
                
                <!-- 流式输出显示 -->
                <div v-if="streamingContent" class="message-item agent streaming">
                  <div class="message-avatar">
                    <div class="message-avatar-circle">{{ getAvatarText(streamingAgentName) }}</div>
                  </div>
                  <div class="message-content">
                    <div class="message-header">
                      <span class="message-name">{{ streamingAgentName }}</span>
                      <span class="typing-indicator">
                        <span></span><span></span><span></span>
                      </span>
                    </div>
                    <div class="message-text markdown-body" v-html="renderMarkdown(streamingContent)"></div>
                  </div>
                </div>

                <!-- 避开控制面板 -->
                <div class="messages-container-footer" v-show="displayLogs.length > 0"></div>
              </div>
              
              <!-- 悬浮控制面板（会议中） -->
              <div v-if="currentMeeting?.is_running" class="floating-control-panel">
                <div class="floating-control-content">
                  <!-- 会议信息 -->
                  <div class="floating-section">
                    <div class="floating-info">会议第{{ currentMeeting.current_round+1 || 1 }}轮:{{ getPhaseDisplay(currentMeeting.round_phase, currentMeeting.current_speaker_agent_id) }}</div>
                  </div>
                  
                  <el-divider class="floating-divider"></el-divider>

                  <!-- 用户想法输入 -->
                  <div class="floating-section">
                    <el-input 
                      type="textarea" 
                      v-model="userInputContent" 
                      :rows="1" 
                      :autosize="{ minRows: 1, maxRows: 6 }"
                      placeholder="有想法随时输入"
                      size="small"
                    ></el-input>
                  </div>
                  <!-- 底部信息和按钮区 -->
                  <div class="floating-bottom-bar">
                    <!-- 左下角：与会者 -->
                    <div class="floating-bottom-left">
                      <div class="floating-experts-list">
                      <div class="floating-expert-item" title="我">
                        <div class="floating-avatar">我</div>
                      </div>
                      <div class="floating-expert-item" :title="`主持人\n${currentMeeting?.host_name || '主持人'}`">
                        <div class="floating-avatar host">{{ getAvatarText(currentMeeting?.host_name || '主持人') }}</div>
                      </div>
                      <div 
                        v-for="agent in agents" 
                        :key="agent.agent_id"
                        class="floating-expert-item"
                        @click="openAgentEditDialog(agent)"
                        :title="`${agent.name}\n${agent.role_desc}`"
                      >
                        <div class="floating-avatar">{{ getAvatarText(agent.name) }}</div>
                      </div>
                      <div 
                        class="floating-expert-item"
                        title="添加专家"
                        @click="openAddAgentDialog"
                      >
                        <div class="floating-avatar add">+</div>
                      </div>
                    </div>
                  </div>
                    
                    <!-- 右下角：按钮 -->
                    <div class="floating-bottom-right">
                      <template>
                        <el-button type="info" @click="loadMeeting" :loading="loadingMeeting" size="small">刷新</el-button>
                        <el-button type="warning" @click="openSettingsDialog" size="small">设置</el-button>
                        <el-button type="primary" @click="startNewRoundWithInput" :loading="startingRound" size="small">▶️ 开始新一轮</el-button>
                        <el-button type="danger" @click="endMeetingWithSummary" :loading="endingMeeting" size="small">🏁 结束会议</el-button>
                      </template>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-main>
    </el-container>
    
    <!-- 编辑专家对话框 -->
    <el-dialog
      :title="editDialogTitle"
      :visible.sync="editDialogVisible"
      width="500px"
      @close="resetEditForm"
    >
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="专家姓名">
          <el-input v-model="editForm.name" placeholder="请输入专家姓名"></el-input>
        </el-form-item>
        <el-form-item label="角色描述">
          <el-input type="textarea" v-model="editForm.role_desc" :rows="4" placeholder="请输入角色描述"></el-input>
        </el-form-item>
        <el-form-item v-if="editingAgentId" label="选择LLM">
          <el-select v-model="editForm.llm_id" placeholder="请选择LLM" style="width: 100%;">
            <el-option 
              v-for="llm in llmConfigs" 
              :key="llm.llm_id" 
              :label="llm.llm_id" 
              :value="llm.llm_id"
            ></el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveExpertEdit" :loading="savingEdit">保存</el-button>
      </span>
    </el-dialog>
    
    <!-- 添加专家对话框 -->
    <el-dialog
      title="添加专家"
      :visible.sync="addAgentDialogVisible"
      width="500px"
      @close="resetAddAgentForm"
    >
      <el-form :model="addAgentForm" label-width="80px">
        <el-form-item label="专家姓名">
          <el-input v-model="addAgentForm.name" placeholder="请输入专家姓名"></el-input>
        </el-form-item>
        <el-form-item label="角色描述">
          <el-input type="textarea" v-model="addAgentForm.role_desc" :rows="4" placeholder="请输入角色描述"></el-input>
        </el-form-item>
        <el-form-item label="选择LLM">
          <el-select v-model="addAgentForm.llm_id" placeholder="请选择LLM" style="width: 100%;">
            <el-option 
              v-for="llm in llmConfigs" 
              :key="llm.llm_id" 
              :label="llm.llm_id" 
              :value="llm.llm_id"
            ></el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="addAgentDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addAgent" :loading="addingAgent">添加</el-button>
      </span>
    </el-dialog>
    
    <!-- 会议信息选择对话框 -->
    <el-dialog
      title="AI生成会议信息"
      :visible.sync="meetingInfoDialogVisible"
      width="800px"
      @close="resetMeetingInfoDialog"
    >
      <div v-if="!generatedTopics.length">
        <div style="font-weight: 600; margin-bottom: 12px; color: #1f2937;">💡 输入您的想法</div>
        <el-input 
          type="textarea" 
          v-model="aiGenerateIdea" 
          :rows="3" 
          placeholder="输入您的简单想法，比如：讨论新产品的上市策略"
          style="margin-bottom: 16px;"
        ></el-input>
        <el-button 
          type="primary" 
          @click="generateMeetingInfoAI" 
          :loading="generatingMeetingInfo" 
          :disabled="!aiGenerateIdea"
          style="width:100%;"
        >
          🚀 开始生成
        </el-button>
      </div>
      
      <div v-else>
        <div style="margin-bottom: 24px;">
          <div style="font-weight: 600; margin-bottom: 12px; color: #1f2937;">📌 选择会议主题</div>
          <el-radio-group v-model="selectedTopic">
            <el-radio 
              v-for="(topic, index) in generatedTopics" 
              :key="`topic-${index}`" 
              :label="topic"
              style="display: flex; align-items: flex-start; margin-bottom: 12px; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb; word-break: break-word; white-space: pre-wrap;"
            >
              <span style="flex: 1; line-height: 1.6;">{{ topic }}</span>
            </el-radio>
          </el-radio-group>
        </div>
        
        <div style="margin-bottom: 24px;">
          <div style="font-weight: 600; margin-bottom: 12px; color: #1f2937;">📝 选择会议背景</div>
          <el-radio-group v-model="selectedBackground">
            <el-radio 
              v-for="(bg, index) in generatedBackgrounds" 
              :key="`bg-${index}`" 
              :label="bg"
              style="display: flex; align-items: flex-start; margin-bottom: 12px; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb; word-break: break-word; white-space: pre-wrap;"
            >
              <span style="flex: 1; line-height: 1.6;">{{ bg }}</span>
            </el-radio>
          </el-radio-group>
        </div>
        
        <div style="margin-bottom: 24px;">
          <div style="font-weight: 600; margin-bottom: 12px; color: #1f2937;">🎯 选择会议目标</div>
          <el-radio-group v-model="selectedGoal">
            <el-radio 
              v-for="(goal, index) in generatedGoals" 
              :key="`goal-${index}`" 
              :label="goal"
              style="display: flex; align-items: flex-start; margin-bottom: 12px; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb; word-break: break-word; white-space: pre-wrap;"
            >
              <span style="flex: 1; line-height: 1.6;">{{ goal }}</span>
            </el-radio>
          </el-radio-group>
        </div>
      </div>
      
      <span slot="footer" class="dialog-footer">
        <el-button @click="meetingInfoDialogVisible = false">取消</el-button>
        <el-button 
          v-if="generatedTopics.length" 
          type="primary" 
          @click="confirmMeetingInfo"
        >
          确认信息
        </el-button>
      </span>
    </el-dialog>
    
    <!-- 删除确认对话框 -->
    <el-dialog
      title="设置"
      :visible.sync="settingsDialogVisible"
      width="700px"
    >
      <el-tabs v-model="settingsActiveTab">
        <el-tab-pane label="LLM管理" name="llm">
          <div class="settings-llm-section">
            <div class="settings-header">
              <el-button type="primary" size="small" @click="createNewLLM" :disabled="!!editingLLMId">
                <i class="el-icon-plus"></i> 新建LLM
              </el-button>
            </div>
            
            <div v-if="settingsLLMs.length === 0 && !editingLLMId" class="empty-llm-hint">
              <div class="empty-icon">📝</div>
              <div class="empty-text">还没有配置LLM，点击"新建LLM"添加</div>
            </div>
            
            <div v-else-if="!editingLLMId" class="llm-list-settings">
              <div 
                v-for="llm in settingsLLMs" 
                :key="llm.llm_id" 
                class="llm-item-settings"
                @click="editLLMInSettings(llm)"
              >
                <div class="llm-info-settings">
                  <div class="llm-id-settings">{{ llm.llm_id }}</div>
                  <div class="llm-detail-settings">
                    <span class="llm-model">模型: {{ llm.default_model }}</span>
                    <span class="llm-api-key">API Key: {{ maskApiKey(llm.api_key) }}</span>
                    <span class="llm-temp">温度: {{ llm.temperature }}</span>
                    <span class="llm-tokens">Max: {{ llm.max_tokens }}</span>
                  </div>
                </div>
                <div class="llm-actions-settings">
                  <el-button type="text" size="small" @click.stop="removeLLMFromSettings(llm.llm_id)" style="color: #f56c6c">
                    <i class="el-icon-delete"></i>
                  </el-button>
                </div>
              </div>
            </div>
            
            <div v-else class="llm-edit-form">
              <el-form :model="settingsLLMForm" label-width="100px" size="small">
                <el-form-item label="LLM ID">
                  <el-input v-model="settingsLLMForm.llm_id" placeholder="例如：gpt-4, claude-3"></el-input>
                </el-form-item>
                <el-form-item label="API Key">
                  <input 
                    v-if="editingLLMId !== 'new'" 
                    type="text" 
                    :value="maskApiKeyFull(settingsLLMForm.api_key)" 
                    readonly 
                    class="readonly-input"
                  >
                  <el-input 
                    v-else 
                    v-model="settingsLLMForm.api_key" 
                    type="password" 
                    placeholder="输入API Key"
                  >
                  </el-input>
                </el-form-item>
                <el-form-item label="Base URL">
                  <el-input v-model="settingsLLMForm.base_url" placeholder="例如：https://api.openai.com/v1"></el-input>
                </el-form-item>
                <el-form-item label="默认模型">
                  <el-input v-model="settingsLLMForm.default_model" placeholder="例如：gpt-3.5-turbo"></el-input>
                </el-form-item>
                <el-form-item label="温度">
                  <div style="display: flex; align-items: center; gap: 10px;">
                    <el-slider v-model="settingsLLMForm.temperature" :min="0" :max="1" :step="0.1" :show-tooltip="false" style="flex: 1;"></el-slider>
                    <span style="min-width: 40px; font-family: Consolas, monospace; color: #667eea; font-weight: 600;">{{ settingsLLMForm.temperature.toFixed(1) }}</span>
                  </div>
                </el-form-item>
                <el-form-item label="Max Tokens">
                  <el-input-number v-model="settingsLLMForm.max_tokens" :min="100" :max="4000" :step="100" style="width:100%"></el-input-number>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="saveLLMToSettings" :loading="addingLLM">保存</el-button>
                  <el-button @click="cancelEditLLM">取消</el-button>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
    
    <el-dialog
      title="确认删除"
      :visible.sync="deleteDialogVisible"
      width="400px"
    >
      <p>确定要删除会议「{{ deletingMeeting?.topic }}」吗？此操作不可恢复！</p>
      <span slot="footer" class="dialog-footer">
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmDelete" :loading="deleting">确认删除</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import axios from 'axios'
import CryptoJS from 'crypto-js'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import xss from 'xss'
import 'github-markdown-css/github-markdown.css'
import './assets/style.css'

const API_BASE = 'http://localhost:5000/api'
const STORAGE_KEY = 'aimeeting_llms'
const ENCRYPT_KEY = 'liaoran'

function encrypt(text) {
  return CryptoJS.AES.encrypt(text, ENCRYPT_KEY).toString()
}

function decrypt(ciphertext) {
  const bytes = CryptoJS.AES.decrypt(ciphertext, ENCRYPT_KEY)
  return bytes.toString(CryptoJS.enc.Utf8)
}

function saveLLMsToLocal(llms) {
  const encryptedLLMs = llms.map(llm => ({
    ...llm,
    api_key: llm.api_key ? encrypt(llm.api_key) : ''
  }))
  localStorage.setItem(STORAGE_KEY, JSON.stringify(encryptedLLMs))
}

function loadLLMsFromLocal() {
  const data = localStorage.getItem(STORAGE_KEY)
  if (!data) return []
  try {
    const llms = JSON.parse(data)
    return llms.map(llm => ({
      ...llm,
      api_key: llm.api_key ? decrypt(llm.api_key) : ''
    }))
  } catch (e) {
    console.error('Failed to load LLMs from local:', e)
    return []
  }
}

export default {
  name: 'App',
  data() {
    return {
      sidebarCollapsed: false,
      meetingList: [],
      currentMeetingId: '',
      currentMeeting: null,
      llmConfigs: [],
      agents: [],
      displayLogs: [],
      
      currentStep: 0,
      
      creating: false,
      registering: false,
      updating: false,
      generating: false,
      generatingMeetingInfo: false,
      aiGenerateIdea: '',
      selecting: false,
      starting: false,
      ending: false,
      speaking: false,
      summarizing: false,
      loadingMeeting: false,
      startingRound: false,
      gettingSpeaker: false,
      generatingSummary: false,
      submittingInput: false,
      checkingConsensus: false,
      endingMeeting: false,
      
      deleteDialogVisible: false,
      deletingMeeting: null,
      deleting: false,
      
      settingsDialogVisible: false,
      settingsActiveTab: 'llm',
      settingsLLMs: [],
      settingsLLMForm: {
        llm_id: '',
        api_key: '',
        base_url: '',
        default_model: 'gpt-3.5-turbo',
        temperature: 0.7,
        max_tokens: 2000
      },
      originalSettingsLLMForm: null,
      addingLLM: false,
      editingLLMId: null,
      
      userInputContent: '',
      consensusResult: null,
      
      llmForm: {
        llm_id: 'openai_gpt4',
        api_key: '',
        base_url: 'https://api.openai.com/v1',
        default_model: 'gpt-4',
        temperature: 0.7,
        max_tokens: 2000
      },
      originalLLMForm: null,
      editingLLMId: null,
      
      meetingForm: {
        host_llm_id: '',
        host_name: '主持人',
        topic: '',
        meeting_background: '',
        meeting_goal: ''
      },
      
      selectedExpertIndices: [],
      expertLLMMap: {},
      
      streamingContent: '',
      streamingAgentName: '',
      
      editDialogVisible: false,
      editDialogTitle: '编辑专家',
      editForm: {
        name: '',
        role_desc: '',
        llm_id: ''
      },
      editingAgentId: null,
      editingExpertIndex: null,
      savingEdit: false,
      currentAgentLLM: '',
      
      addAgentDialogVisible: false,
      addAgentForm: {
        name: '',
        role_desc: '',
        llm_id: ''
      },
      addingAgent: false,
      
      meetingInfoDialogVisible: false,
      generatedTopics: [],
      generatedBackgrounds: [],
      generatedGoals: [],
      selectedTopic: '',
      selectedBackground: '',
      selectedGoal: ''
    }
  },
  
  watch: {
    '$route.params.id': {
      immediate: true,
      handler(newId) {
        if (newId) {
          this.currentMeetingId = newId
          this.loadMeeting()
        } else {
          this.currentMeetingId = ''
        }
      }
    }
  },
  
  mounted() {
    this.loadMeetingList()
    
    if (this.$route.params.id) {
      this.currentMeetingId = this.$route.params.id
      this.loadMeeting()
    }
  },
  
  methods: {    
    renderMarkdown(text) {
      if (!text) return ''
      marked.setOptions({
        highlight: function(code, lang) {
          const language = hljs.getLanguage(lang) ? lang : 'plaintext'
          return hljs.highlight(code, { language }).value
        },
        breaks: true,
        gfm: true
      })
      const html = marked(text)
      return xss(html)
    },
    
    getPhaseDisplay(phase, speakerAgentId) {
      if (phase === 'host_intro') {
        return '主持人开场'
      } else if (phase === 'experts_first_speaking') {
        return this.getAgentName(speakerAgentId) + '发言'
      } else if (phase === 'round_summarizing') {
        return '轮次汇总中'
      } else if (phase === 'user_decision') {
        return '用户交互阶段'
      } else if (phase === 'experts_iteration') {
        return this.getAgentName(speakerAgentId) + '发言'
      } else if (phase === 'summarizing') {
        return '会议总结中'
      }
      return '会议进行中'
    },
    
    openDeleteConfirm(meeting) {
      this.deletingMeeting = meeting
      this.deleteDialogVisible = true
    },
    
    async confirmDelete() {
      if (!this.deletingMeeting) return
      
      this.deleting = true
      try {
        await axios.delete(`${API_BASE}/meeting/${this.deletingMeeting.meeting_id}/delete`)
        this.$message.success('删除成功！')
        this.deleteDialogVisible = false
        
        if (this.deletingMeeting.meeting_id === this.currentMeetingId) {
          this.$router.push('/')
        }
        
        await this.loadMeetingList()
      } catch (e) {
        this.$message.error('删除失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.deleting = false
        this.deletingMeeting = null
      }
    },
    
    openAgentEditDialog(agent) {
      this.editDialogTitle = '编辑专家'
      this.editingAgentId = agent.agent_id
      this.editingExpertIndex = null
      this.currentAgentLLM = agent.llm_id
      this.editForm = {
        name: agent.name,
        role_desc: agent.role_desc,
        llm_id: agent.llm_id
      }
      this.editDialogVisible = true
    },
    
    openGeneratedExpertEditDialog(expert, index) {
      this.editDialogTitle = '编辑专家'
      this.editingAgentId = null
      this.editingExpertIndex = index
      this.editForm = {
        name: expert.name,
        role_desc: expert.role_desc
      }
      this.editDialogVisible = true
    },
    
    resetEditForm() {
      this.editForm = { name: '', role_desc: '', llm_id: '' }
      this.editingAgentId = null
      this.editingExpertIndex = null
      this.currentAgentLLM = ''
    },
    
    openAddAgentDialog() {
      this.addAgentForm = { name: '', role_desc: '', llm_id: '' }
      this.addAgentDialogVisible = true
    },
    
    resetAddAgentForm() {
      this.addAgentForm = { name: '', role_desc: '', llm_id: '' }
    },
    
    async addAgent() {
      if (!this.addAgentForm.name) {
        this.$message.warning('请输入专家姓名')
        return
      }
      if (!this.addAgentForm.llm_id) {
        this.$message.warning('请选择LLM')
        return
      }
      
      this.addingAgent = true
      try {
        await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/agent/create`, this.addAgentForm)
        this.$message.success('专家添加成功！')
        this.addAgentDialogVisible = false
        await this.loadMeeting()
      } catch (e) {
        this.$message.error('添加失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.addingAgent = false
      }
    },
    
    async saveExpertEdit() {
      if (!this.editForm.name) {
        this.$message.warning('请输入专家姓名')
        return
      }
      
      this.savingEdit = true
      try {
        let url
        if (this.editingAgentId) {
          url = `${API_BASE}/meeting/${this.currentMeetingId}/agent/${this.editingAgentId}/update`
          await axios.put(url, { name: this.editForm.name, role_desc: this.editForm.role_desc })
          
          if (this.editForm.llm_id && this.editForm.llm_id !== this.currentAgentLLM) {
            await axios.patch(`${API_BASE}/meeting/${this.currentMeetingId}/agent/${this.editingAgentId}/llm`, { llm_id: this.editForm.llm_id })
          }
        } else if (this.editingExpertIndex !== null) {
          url = `${API_BASE}/meeting/${this.currentMeetingId}/expert/${this.editingExpertIndex}/update`
          await axios.put(url, this.editForm)
        } else {
          return
        }
        
        this.$message.success('保存成功！')
        this.editDialogVisible = false
        await this.loadMeeting()
      } catch (e) {
        this.$message.error('保存失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.savingEdit = false
      }
    },
    
    async loadMeetingList() {
      try {
        const res = await axios.get(`${API_BASE}/meetings`)
        if (res.data.code === 200) {
          this.meetingList = res.data.data || []
        }
      } catch (e) {
        console.error('Failed to load meeting list:', e)
      }
    },
    
    formatTime(timeStr) {
      if (!timeStr) return ''
      try {
        const date = new Date(timeStr)
        return date.toLocaleString('zh-CN', {
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        })
      } catch {
        return timeStr
      }
    },
    
    async createNewMeeting() {
      this.creating = true
      try {
        const res = await axios.post(`${API_BASE}/meeting/create`, {
          topic: '新会议',
          host_name: '主持人'
        })
        
        if (res.data.code === 200) {
          const newId = res.data.data.meeting_id
          this.$router.push(`/meeting/${newId}`)
          await this.loadMeetingList()
        }
      } catch (e) {
        this.$message.error('创建失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.creating = false
      }
    },
    
    switchToMeeting(meetingId) {
      if (meetingId !== this.currentMeetingId) {
        this.$router.push(`/meeting/${meetingId}`)
      }
    },
    
    async loadMeeting() {
      if (!this.currentMeetingId) return
      
      this.loadingMeeting = true
      try {
        const res = await axios.get(`${API_BASE}/meeting/${this.currentMeetingId}`)
        
        if (res.data.code === 200) {
          this.currentMeeting = res.data.data
          this.llmConfigs = Object.values(this.currentMeeting.llm_configs || {})
          this.agents = Object.values(this.currentMeeting.agents || {})
          this.displayLogs = this.currentMeeting.discussion_log || []
          
          this.currentStep = this.currentMeeting.current_step || 1
          
          this.meetingForm = {
            host_llm_id: this.currentMeeting.host_llm_id || '',
            host_name: this.currentMeeting.host_name || '主持人',
            topic: this.currentMeeting.topic || '',
            meeting_background: this.currentMeeting.meeting_background || '',
            meeting_goal: this.currentMeeting.meeting_goal || ''
          }
          
          const meetingHasLLMs = this.currentMeeting.llm_configs && Object.keys(this.currentMeeting.llm_configs).length > 0
          
          if (!meetingHasLLMs) {
            await this.syncLocalLLMsToMeeting()
            const res2 = await axios.get(`${API_BASE}/meeting/${this.currentMeetingId}`)
            if (res2.data.code === 200) {
              this.currentMeeting = res2.data.data
              this.llmConfigs = Object.values(this.currentMeeting.llm_configs || {})
            }
          }
          
          this.$nextTick(() => {
            this.scrollToBottom()
          })
        }
      } catch (e) {
        this.$message.error('加载失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.loadingMeeting = false
      }
    },
    
    scrollToBottom() {
      const container = this.$refs.messagesContainer
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    },
    
    async updateStepOnServer(step) {
      try {
        await axios.put(`${API_BASE}/meeting/${this.currentMeetingId}/step/update`, { step })
      } catch (e) {
        console.error('更新步骤失败:', e)
      }
    },

    async goToPrevStep() {
      this.cancelEditMeetingLLM()
      if (this.currentStep > 1) {
        this.currentStep -= 1
        await this.updateStepOnServer(this.currentStep)
      }
    },

    async goToNextStep() {
      this.cancelEditMeetingLLM()
      if (this.currentStep < 2) {
        this.currentStep = 2
        await this.updateStepOnServer(2)
      }
    },

    startMeetingWithConfirm() {
      this.$confirm('一旦会议开始不可更改会议信息，确定要开始吗？', '确认启动会议', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.startMeeting()
      }).catch(() => {})
    },
    
    editLLM(llm) {
      this.editingLLMId = llm.llm_id
      
      const localLLMs = loadLLMsFromLocal()
      const localLLM = localLLMs.find(l => l.llm_id === llm.llm_id)
      
      this.llmForm = {
        llm_id: llm.llm_id,
        api_key: localLLM?.api_key || llm.api_key || '',
        base_url: llm.base_url || '',
        default_model: llm.default_model || '',
        temperature: llm.temperature || 0.7,
        max_tokens: llm.max_tokens || 2000
      }
      
      this.originalLLMForm = { ...this.llmForm }
    },
    
    async registerLLM() {
      if (!this.llmForm.llm_id) {
        this.$message.warning('请填写LLM ID')
        return
      }
      
      if (!this.editingLLMId && !this.llmForm.api_key) {
        this.$message.warning('请填写API Key')
        return
      }
      
      if (this.editingLLMId && this.originalLLMForm) {
        const hasNoChange = 
          this.llmForm.llm_id === this.originalLLMForm.llm_id &&
          this.llmForm.api_key === this.originalLLMForm.api_key &&
          this.llmForm.base_url === this.originalLLMForm.base_url &&
          this.llmForm.default_model === this.originalLLMForm.default_model &&
          this.llmForm.temperature === this.originalLLMForm.temperature &&
          this.llmForm.max_tokens === this.originalLLMForm.max_tokens
        
        if (hasNoChange) {
          this.cancelEditMeetingLLM()
          return
        }
      }
      
      this.registering = true
      try {
        const encryptedForm = {
          ...this.llmForm
        }
        
        if (this.llmForm.api_key) {
          encryptedForm.api_key = encrypt(this.llmForm.api_key)
        } else if (this.editingLLMId) {
          delete encryptedForm.api_key
        }
        
        if (this.editingLLMId) {
          await axios.put(`${API_BASE}/meeting/${this.currentMeetingId}/llm/${this.editingLLMId}`, encryptedForm)
          this.$message.success('LLM更新成功！')
        } else {
          await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/llm/register`, encryptedForm)
          this.$message.success('LLM注册成功！')
        }
        
        const localLLMs = loadLLMsFromLocal()
        const existingIndex = localLLMs.findIndex(llm => llm.llm_id === this.llmForm.llm_id)
        
        if (existingIndex >= 0) {
          const oldLLM = localLLMs[existingIndex]
          if (!this.editingLLMId || this.llmForm.api_key) {
            localLLMs[existingIndex] = { ...this.llmForm }
          } else {
            localLLMs[existingIndex] = { 
              ...this.llmForm, 
              api_key: oldLLM.api_key 
            }
          }
        } else {
          localLLMs.push({ ...this.llmForm })
        }
        saveLLMsToLocal(localLLMs)
        
        await this.loadMeeting()
        this.cancelEditMeetingLLM()
      } catch (e) {
        this.$message.error((this.editingLLMId ? '更新' : '注册') + '失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.registering = false
      }
    },
    
    cancelEditMeetingLLM() {
      this.editingLLMId = null
      this.llmForm = {
        llm_id: 'openai_gpt4',
        api_key: '',
        base_url: 'https://api.openai.com/v1',
        default_model: 'gpt-4',
        temperature: 0.7,
        max_tokens: 2000
      }
    },
    
    async removeLLM(llmId) {
      this.$confirm(`确定要删除 LLM "${llmId}" 吗？`, '确认删除', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await axios.delete(`${API_BASE}/meeting/${this.currentMeetingId}/llm/${llmId}`)
          
          const localLLMs = loadLLMsFromLocal().filter(llm => llm.llm_id !== llmId)
          saveLLMsToLocal(localLLMs)
          
          this.$message.success('删除成功！')
          await this.loadMeeting()
        } catch (e) {
          this.$message.error('删除失败: ' + (e.response?.data?.message || e.message))
        }
      }).catch(() => {})
    },
    
    async syncLocalLLMsToMeeting() {
      if (!this.currentMeetingId) return
      
      const localLLMs = loadLLMsFromLocal()
      if (localLLMs.length === 0) return
      
      const meetingLLMIds = this.currentMeeting?.llm_configs ? Object.keys(this.currentMeeting.llm_configs) : []
      
      for (const llm of localLLMs) {
        if (meetingLLMIds.includes(llm.llm_id)) {
          console.log('LLM ' + llm.llm_id + ' 已存在于会议中，跳过同步')
          continue
        }
        
        try {
          console.log(`正在同步新LLM ${llm.llm_id} 到会议...`)
          const encryptedLLM = {
            ...llm,
            api_key: encrypt(llm.api_key)
          }
          await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/llm/register`, encryptedLLM)
        } catch (e) {
          if (e.response?.status !== 409) {
            console.error('Failed to sync LLM:', llm.llm_id, e)
          }
        }
      }
    },
    
    maskApiKey(apiKey) {
      if (!apiKey || apiKey.length <= 8) return '****'
      return apiKey.substring(0, 4) + '****' + apiKey.substring(apiKey.length - 4)
    },
    
    maskApiKeyFull(apiKey) {
      if (!apiKey || apiKey.length <= 6) return '******'
      return apiKey.substring(0, 3) + '****' + apiKey.substring(apiKey.length - 3)
    },
    
    openSettingsDialog() {
      if (this.currentMeetingId && this.currentMeeting) {
        this.settingsLLMs = Object.values(this.currentMeeting.llm_configs || {})
      } else {
        this.settingsLLMs = loadLLMsFromLocal()
      }
      this.settingsDialogVisible = true
      this.cancelEditLLM()
    },
    
    resetSettingsLLMForm() {
      this.settingsLLMForm = {
        llm_id: '',
        api_key: '',
        base_url: '',
        default_model: 'gpt-3.5-turbo',
        temperature: 0.7,
        max_tokens: 2000
      }
      this.editingLLMId = null
    },
    
    createNewLLM() {
      this.resetSettingsLLMForm()
      this.editingLLMId = 'new'
    },
    
    cancelEditLLM() {
      this.resetSettingsLLMForm()
    },
    
    async saveLLMToSettings() {
      if (!this.settingsLLMForm.llm_id || !this.settingsLLMForm.base_url) {
        this.$message.warning('请填写LLM ID和Base URL')
        return
      }
      if (!this.editingLLMId || this.editingLLMId === 'new') {
        if (!this.settingsLLMForm.api_key) {
          this.$message.warning('请填写API Key')
          return
        }
      }
      
      if (this.editingLLMId && this.editingLLMId !== 'new' && this.originalSettingsLLMForm) {
        const hasNoChange = 
          this.settingsLLMForm.llm_id === this.originalSettingsLLMForm.llm_id &&
          this.settingsLLMForm.api_key === this.originalSettingsLLMForm.api_key &&
          this.settingsLLMForm.base_url === this.originalSettingsLLMForm.base_url &&
          this.settingsLLMForm.default_model === this.originalSettingsLLMForm.default_model &&
          this.settingsLLMForm.temperature === this.originalSettingsLLMForm.temperature &&
          this.settingsLLMForm.max_tokens === this.originalSettingsLLMForm.max_tokens
        
        if (hasNoChange) {
          this.cancelEditLLM()
          return
        }
      }
      
      this.addingLLM = true
      
      try {
        const newLLM = { ...this.settingsLLMForm }
        
        if (this.currentMeetingId && this.currentMeeting) {
          if (this.editingLLMId && this.editingLLMId !== 'new') {
            await axios.put(`${API_BASE}/meeting/${this.currentMeetingId}/llm/${this.editingLLMId}`, newLLM)
          } else {
            await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/llm/register`, newLLM)
          }
          await this.loadMeeting()
          this.settingsLLMs = Object.values(this.currentMeeting.llm_configs || {})
        } else {
          const localLLMs = loadLLMsFromLocal()
          
          if (this.editingLLMId && this.editingLLMId !== 'new') {
            const index = localLLMs.findIndex(llm => llm.llm_id === this.editingLLMId)
            if (index >= 0) {
              if (newLLM.llm_id !== this.editingLLMId && localLLMs.find(llm => llm.llm_id === newLLM.llm_id)) {
                this.$message.warning('该LLM ID已存在')
                return
              }
              localLLMs[index] = newLLM
            }
          } else {
            if (localLLMs.find(llm => llm.llm_id === newLLM.llm_id)) {
              this.$message.warning('该LLM ID已存在')
              return
            }
            localLLMs.push(newLLM)
          }
          
          saveLLMsToLocal(localLLMs)
          this.settingsLLMs = localLLMs
        }
        
        this.$message.success(this.editingLLMId !== 'new' ? '更新成功' : '添加成功')
        this.cancelEditLLM()
      } catch (e) {
        this.$message.error('保存失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.addingLLM = false
      }
    },
    
    editLLMInSettings(llm) {
      this.settingsLLMForm = { ...llm }
      this.originalSettingsLLMForm = { ...llm }
      this.editingLLMId = llm.llm_id
    },
    
    removeLLMFromSettings(llmId) {
      this.$confirm(`确定要删除 LLM "${llmId}" 吗？`, '确认删除', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          if (this.currentMeetingId && this.currentMeeting) {
            await axios.delete(`${API_BASE}/meeting/${this.currentMeetingId}/llm/${llmId}`)
            await this.loadMeeting()
            this.settingsLLMs = Object.values(this.currentMeeting.llm_configs || {})
          } else {
            const localLLMs = loadLLMsFromLocal().filter(llm => llm.llm_id !== llmId)
            saveLLMsToLocal(localLLMs)
            this.settingsLLMs = localLLMs
          }
          this.$message.success('删除成功')
        } catch (e) {
          this.$message.error('删除失败: ' + (e.response?.data?.message || e.message))
        }
      }).catch(() => {})
    },
    
    async updateMeetingInfo() {
      if (!this.meetingForm.host_llm_id) {
        this.$message.warning('请选择主持人LLM')
        return
      }
      if (!this.meetingForm.topic) {
        this.$message.warning('请输入会议主题')
        return
      }
      
      const hasChanges = 
        this.meetingForm.host_llm_id !== this.currentMeeting.host_llm_id ||
        this.meetingForm.host_name !== this.currentMeeting.host_name ||
        this.meetingForm.topic !== this.currentMeeting.topic ||
        this.meetingForm.meeting_background !== this.currentMeeting.meeting_background ||
        this.meetingForm.meeting_goal !== this.currentMeeting.meeting_goal
      
      if (!hasChanges) {
        this.currentStep = 3
        await this.updateStepOnServer(3)
        return
      }
      
      this.updating = true
      try {
        await axios.put(`${API_BASE}/meeting/${this.currentMeetingId}/info`, this.meetingForm)
        
        this.$message.success('保存成功！')
        await this.loadMeeting()
      } catch (e) {
        this.$message.error('保存失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.updating = false
      }
    },
    
    async generateExperts() {
      if (this.currentMeeting.generated_experts && this.currentMeeting.generated_experts.length > 0) {
        this.currentStep = 4
        await this.updateStepOnServer(4)
        return
      }
      
      this.generating = true
      try {
        await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/experts/generate`)
        
        this.$message.success('专家生成成功！')
        await this.loadMeeting()
      } catch (e) {
        this.$message.error('生成失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.generating = false
      }
    },
    
    async selectExperts() {
      if (this.agents && this.agents.length > 0) {
        this.currentStep = 5
        await this.updateStepOnServer(5)
        return
      }
      
      if (this.selectedExpertIndices.length === 0) {
        this.$message.warning('请至少选择一位专家')
        return
      }
      
      for (let idx of this.selectedExpertIndices) {
        if (!this.expertLLMMap[idx]) {
          this.$message.warning('请为所有选中的专家选择LLM')
          return
        }
      }
      
      this.selecting = true
      try {
        const selections = this.selectedExpertIndices.map(idx => ({
          expert_index: idx,
          llm_id: this.expertLLMMap[idx]
        }))
        
        await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/experts/select`, {
          expert_selections: selections
        })
        
        this.$message.success('专家选择成功！')
        await this.loadMeeting()
      } catch (e) {
        this.$message.error('选择失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.selecting = false
      }
    },
    
    async startMeeting() {
      if (this.speaking) return
      
      this.starting = true
      this.speaking = true
      this.streamingContent = ''
      this.streamingAgentName = this.currentMeeting.host_name
      
      try {
        const res = await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/start`)
        if (res.data.code === 200) {
          this.$message.success('会议已启动！')
          await this.loadMeeting()
          
          const speech_type = 'opening'
          const url = `${API_BASE}/meeting/${this.currentMeetingId}/host/speak?speech_type=${encodeURIComponent(speech_type)}`
          const eventSource = new EventSource(url)
          
          eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data)
            if (data.type === 'content') {
              this.streamingContent += data.content
              this.$nextTick(() => this.scrollToBottom())
            } else if (data.type === 'end') {
              eventSource.close()
              this.streamingContent = ''
              this.speaking = false
              this.loadMeeting().then(() => {
                this.autoNextSpeaker()
              })
            }
          }
          
          eventSource.onerror = (error) => {
            console.error('EventSource error:', error)
            eventSource.close()
            this.speaking = false
            this.starting = false
            this.$message.error('主持人开场白失败')
          }
        }
      } catch (e) {
        this.speaking = false
        this.starting = false
        this.$message.error('启动失败: ' + (e.response?.data?.message || e.message))
      }
    },
    
    getAgentName(agentId) {
      const agent = this.agents.find(a => a.agent_id === agentId)
      return agent ? agent.name : '未知'
    },
    
    getAvatarText(speaker) {
      if (!speaker) return '🤖'
      let name = speaker.trim()
      if (!name) return '🤖'
      let firstChar = name.charAt(0)
      if (/[\u4e00-\u9fa5]/.test(firstChar)) {
        return firstChar
      }
      return firstChar.toUpperCase()
    },
    
    async startNewRound() {
      this.startingRound = true
      try {
        const res = await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/round/start`, {
          user_input: this.userInputContent
        })
        if (res.data.code === 200) {
          this.$message.success('新一轮会议开始！')
          this.userInputContent = ''
          await this.loadMeeting()
        }
      } catch (e) {
        this.$message.error('开始失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.startingRound = false
      }
    },
    
    async startNewRoundWithInput() {
      if (this.speaking) return
      
      this.startingRound = true
      this.speaking = true
      this.streamingContent = ''
      this.streamingAgentName = this.currentMeeting.host_name
      
      try {
        const speech_type = 'process_user_input'
        const additional_context = this.userInputContent
        
        this.userInputContent = ''
        
        const url = `${API_BASE}/meeting/${this.currentMeetingId}/host/speak?speech_type=${encodeURIComponent(speech_type)}&additional_context=${encodeURIComponent(additional_context)}`
        const eventSource = new EventSource(url)
        
        eventSource.onmessage = (event) => {
          const data = JSON.parse(event.data)
          if (data.type === 'content') {
            this.streamingContent += data.content
            this.$nextTick(() => this.scrollToBottom())
          } else if (data.type === 'end') {
            eventSource.close()
            this.streamingContent = ''
            this.speaking = false
            this.loadMeeting().then(() => {
              this.autoNextSpeaker()
            })
          }
        }
        
        eventSource.onerror = (error) => {
          console.error('EventSource error:', error)
          eventSource.close()
          this.speaking = false
          this.startingRound = false
          this.$message.error('主持人发言失败')
        }
      } catch (e) {
        this.speaking = false
        this.startingRound = false
        this.$message.error('开始失败: ' + (e.response?.data?.message || e.message))
      }
    },
    
    async hostRoundSummary() {
      this.generatingSummary = true
      try {
        const res = await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/host/summary`)
        if (res.data.code === 200) {
          this.$message.success('主持人汇总完成！')
          await this.loadMeeting()
        }
      } catch (e) {
        this.$message.error('汇总失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.generatingSummary = false
      }
    },
    
    async nextSpeaker() {
      this.gettingSpeaker = true
      try {
        const res = await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/speaker/next`)
        if (res.data.code === 200) {
          if (res.data.data.finished) {
            this.$message.info('本轮专家发言已结束')
            await this.loadMeeting()
          } else {
            this.$message.success(`请 ${res.data.data.agent_name} 发言`)
            await this.autoSpeak(res.data.data.agent_id)
          }
        }
      } catch (e) {
        this.$message.error('获取失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.gettingSpeaker = false
      }
    },
    
    async autoSpeak(agentId) {
      this.speaking = true
      this.streamingContent = ''
      const agent = this.agents.find(a => a.agent_id === agentId)
      this.streamingAgentName = agent?.name || 'Agent'
      
      try {
        const instruction = '请根据主持人的话，发表你的专业观点'
        const url = `${API_BASE}/meeting/${this.currentMeetingId}/agent/${agentId}/speak?instruction=${encodeURIComponent(instruction)}`
        const eventSource = new EventSource(url)
        
        eventSource.onmessage = (event) => {
          const data = JSON.parse(event.data)
          if (data.type === 'start') {
            this.streamingContent = ''
          } else if (data.type === 'content') {
            this.streamingContent += data.content
            this.$nextTick(() => this.scrollToBottom())
          } else if (data.type === 'end') {
            eventSource.close()
            this.streamingContent = ''
            this.speaking = false
            this.loadMeeting().then(() => {
              this.autoNextSpeaker()
            })
          }
        }
        
        eventSource.onerror = (error) => {
          console.error('EventSource error:', error)
          eventSource.close()
          this.speaking = false
          this.$message.error('发言失败')
        }
      } catch (e) {
        this.speaking = false
        this.$message.error('发言失败: ' + (e.response?.data?.message || e.message))
      }
    },
    
    async autoNextSpeaker() {
      if (this.gettingSpeaker || this.speaking) return
      
      try {
        const res = await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/speaker/next`)
        if (res.data.code === 200) {
          if (res.data.data.finished) {
            this.$message.info('本轮专家发言已结束，主持人推进中...')
            await this.loadMeeting()
            await this.autoHostSpeak()
          } else {
            await this.autoSpeak(res.data.data.agent_id)
          }
        }
      } catch (e) {
        console.error('自动请下一位失败:', e)
      }
    },
    
    async autoHostSpeak() {
      if (this.speaking) return
      
      this.speaking = true
      this.streamingContent = ''
      this.streamingAgentName = this.currentMeeting.host_name
      
      try {
        let speech_type = ''
        let additional_context = ''
        
        if (this.currentMeeting.round_phase === 'experts_first_speaking') {
          speech_type = 'first_proposal'
        } else if (this.currentMeeting.round_phase === 'experts_iteration') {
          speech_type = 'second_proposal'
        }
        
        if (!speech_type) {
          this.speaking = false
          return
        }
        
        const url = `${API_BASE}/meeting/${this.currentMeetingId}/host/speak?speech_type=${encodeURIComponent(speech_type)}&additional_context=${encodeURIComponent(additional_context)}`
        const eventSource = new EventSource(url)
        
        eventSource.onmessage = (event) => {
          const data = JSON.parse(event.data)
          if (data.type === 'content') {
            this.streamingContent += data.content
            this.$nextTick(() => this.scrollToBottom())
          } else if (data.type === 'end') {
            eventSource.close()
            this.streamingContent = ''
            this.speaking = false
            this.loadMeeting()
          }
        }
        
        eventSource.onerror = (error) => {
          console.error('EventSource error:', error)
          eventSource.close()
          this.speaking = false
          this.$message.error('主持人发言失败')
        }
      } catch (e) {
        this.speaking = false
        this.$message.error('主持人发言失败: ' + (e.response?.data?.message || e.message))
      }
    },
    
    async generateRoundSummary() {
      this.generatingSummary = true
      try {
        const res = await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/round/summary`)
        if (res.data.code === 200) {
          this.$message.success('轮次汇总生成成功！')
          await this.loadMeeting()
        }
      } catch (e) {
        this.$message.error('汇总失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.generatingSummary = false
      }
    },
    
    async submitUserInput() {
      this.submittingInput = true
      try {
        const res = await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/user/input`, {
          input: this.userInputContent
        })
        if (res.data.code === 200) {
          this.$message.success('补充成功！')
          this.userInputContent = ''
          this.consensusResult = null
          await this.loadMeeting()
        }
      } catch (e) {
        this.$message.error('补充失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.submittingInput = false
      }
    },
    
    async checkConsensus() {
      this.checkingConsensus = true
      try {
        const res = await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/consensus/check`)
        if (res.data.code === 200) {
          this.consensusResult = res.data.data
          this.$message.success('检查完成！')
        }
      } catch (e) {
        this.$message.error('检查失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.checkingConsensus = false
      }
    },
    
    async endMeetingWithSummary() {
      this.$confirm('确定要生成最终总结并结束会议吗？', '确认结束', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        this.endingMeeting = true
        try {
          const res = await axios.post(`${API_BASE}/meeting/${this.currentMeetingId}/final/summary`)
          
          if (res.data.code === 200) {
            this.$message.success('会议已结束！')
            await this.loadMeeting()
          }
        } catch (e) {
          this.$message.error('结束失败: ' + (e.response?.data?.message || e.message))
        } finally {
          this.endingMeeting = false
        }
      }).catch(() => {})
    },
    
    async loadSummary() {
      if (this.currentMeeting?.summary) {
        return
      }
      
      try {
        const res = await axios.get(`${API_BASE}/meeting/${this.currentMeetingId}/summary`)
        if (res.data.code === 200) {
          await this.loadMeeting()
        }
      } catch (e) {
        this.$message.error('加载失败: ' + (e.response?.data?.message || e.message))
      }
    },
    
    openMeetingInfoDialog() {
      this.aiGenerateIdea = ''
      this.generatedTopics = []
      this.generatedBackgrounds = []
      this.generatedGoals = []
      this.selectedTopic = ''
      this.selectedBackground = ''
      this.selectedGoal = ''
      this.meetingInfoDialogVisible = true
    },
    
    resetMeetingInfoDialog() {
      this.aiGenerateIdea = ''
      this.generatedTopics = []
      this.generatedBackgrounds = []
      this.generatedGoals = []
      this.selectedTopic = ''
      this.selectedBackground = ''
      this.selectedGoal = ''
    },
    
    async generateMeetingInfoAI() {
      if (!this.meetingForm.host_llm_id || !this.aiGenerateIdea) {
        this.$message.warning('请输入您的想法')
        return
      }
      
      this.generatingMeetingInfo = true
      try {
        const res = await axios.post(`${API_BASE}/generate-meeting-info`, {
          llm_id: this.meetingForm.host_llm_id,
          user_input: this.aiGenerateIdea
        })
        
        if (res.data.code === 200) {
          this.generatedTopics = res.data.data.topics || []
          this.generatedBackgrounds = res.data.data.backgrounds || []
          this.generatedGoals = res.data.data.goals || []
          
          if (this.generatedTopics.length > 0) {
            this.selectedTopic = this.generatedTopics[0]
          }
          if (this.generatedBackgrounds.length > 0) {
            this.selectedBackground = this.generatedBackgrounds[0]
          }
          if (this.generatedGoals.length > 0) {
            this.selectedGoal = this.generatedGoals[0]
          }
          
          this.$message.success('会议信息生成成功！')
        }
      } catch (e) {
        this.$message.error('生成失败: ' + (e.response?.data?.message || e.message))
      } finally {
        this.generatingMeetingInfo = false
      }
    },
    
    confirmMeetingInfo() {
      if (this.selectedTopic) {
        this.meetingForm.topic = this.selectedTopic
      }
      if (this.selectedBackground) {
        this.meetingForm.meeting_background = this.selectedBackground
      }
      if (this.selectedGoal) {
        this.meetingForm.meeting_goal = this.selectedGoal
      }
      this.meetingInfoDialogVisible = false
    }
  }
}
</script>

<style scoped>
/* 额外的样式会从 style.css 加载 */
</style>
