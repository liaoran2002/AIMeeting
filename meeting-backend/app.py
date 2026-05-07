import os
import json
import uuid
import base64
import threading
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Generator, Any
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from openai import OpenAI
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

app = Flask(__name__)
CORS(app, resources=r'/*')

MEETINGS_DIR = os.path.join(os.path.dirname(__file__), 'meetings')
os.makedirs(MEETINGS_DIR, exist_ok=True)

ENCRYPT_KEY = 'liaoran'

def derive_key_and_iv(password: str, salt: bytes) -> tuple[bytes, bytes]:
    from hashlib import md5
    password_bytes = password.encode('utf-8')
    key = b''
    iv = b''
    prev = b''
    while len(key) < 32 or len(iv) < 16:
        prev = md5(prev + password_bytes + salt).digest()
        if len(key) < 32:
            key += prev[:min(32 - len(key), 16)]
        else:
            iv += prev[:min(16 - len(iv), 16)]
    return key, iv

def decrypt(ciphertext: str) -> str:
    try:
        encrypted_data = base64.b64decode(ciphertext)
        if encrypted_data[:8] != b'Salted__':
            return ciphertext
        
        salt = encrypted_data[8:16]
        ciphertext_bytes = encrypted_data[16:]
        
        key, iv = derive_key_and_iv(ENCRYPT_KEY, salt)
        
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        decrypted_padded = decryptor.update(ciphertext_bytes) + decryptor.finalize()
        
        unpadder = padding.PKCS7(128).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
        
        return decrypted.decode('utf-8')
    except Exception as e:
        print(f'Decrypt error: {e}')
        return ciphertext


@dataclass
class LLMConfig:
    llm_id: str
    api_key: str
    base_url: str
    default_model: str
    temperature: float = 0.7
    max_tokens: int = 2000


@dataclass
class AgentContext:
    core_summary: str = ""
    key_records: List[str] = field(default_factory=list)
    others_summary: str = ""


@dataclass
class Agent:
    agent_id: str
    name: str
    role_desc: str
    llm_id: str
    context: AgentContext = field(default_factory=AgentContext)
    speech_history: List[Dict] = field(default_factory=list)


@dataclass
class DiscussionLogEntry:
    timestamp: str
    type: str
    speaker: str
    content: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class Meeting:
    meeting_id: str
    topic: str
    host_name: str
    create_time: str
    is_running: bool = False
    llm_configs: Dict[str, LLMConfig] = field(default_factory=dict)
    agents: Dict[str, Agent] = field(default_factory=dict)
    discussion_log: List[DiscussionLogEntry] = field(default_factory=list)
    summary: str = ""
    round_summaries: List[Dict] = field(default_factory=list)
    current_round: int = 0
    meeting_background: str = ""
    meeting_goal: str = ""
    host_llm_id: str = ""
    generated_experts: List[Dict] = field(default_factory=list)
    current_speaker_agent_id: str = ""
    round_speaker_order: List[str] = field(default_factory=list)
    waiting_for_user_input: bool = False
    user_input: str = ""
    current_step: int = 1
    round_phase: str = ""  # 'opening', 'experts_first_speaking', 'host_first_proposal', 'user_decision', 'host_process_user_input', 'experts_iteration', 'host_second_proposal', 'round_complete'


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
    
    def call_stream(self, prompt: str, model: Optional[str] = None) -> Generator[str, None, None]:
        stream = self.client.chat.completions.create(
            model=model or self.config.default_model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout=30
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def call_sync(self, prompt: str, model: Optional[str] = None) -> str:
        response = self.client.chat.completions.create(
            model=model or self.config.default_model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout=30
        )
        return response.choices[0].message.content


class MeetingSystemManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.meetings: Dict[str, Meeting] = {}
        self.llm_client_pool: Dict[str, LLMClient] = {}
        self._lock = threading.RLock()
        self._load_meetings_from_disk()
        self._initialized = True
    
    def _get_meeting_path(self, meeting_id: str) -> str:
        return os.path.join(MEETINGS_DIR, f"{meeting_id}.json")
    
    def _save_meeting_to_disk(self, meeting: Meeting):
        with self._lock:
            path = self._get_meeting_path(meeting.meeting_id)
            meeting_dict = asdict(meeting)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(meeting_dict, f, ensure_ascii=False, indent=2)
    
    def _load_meeting_from_dict(self, data: Dict) -> Meeting:
        llm_configs = {}
        for llm_id, llm_data in data.get('llm_configs', {}).items():
            llm_configs[llm_id] = LLMConfig(
                llm_id=llm_data.get('llm_id', llm_id),
                api_key=llm_data.get('api_key', ''),
                base_url=llm_data.get('base_url', ''),
                default_model=llm_data.get('default_model', 'gpt-3.5-turbo'),
                temperature=llm_data.get('temperature', 0.7),
                max_tokens=llm_data.get('max_tokens', 2000)
            )
        
        agents = {}
        for agent_id, agent_data in data.get('agents', {}).items():
            context_data = agent_data.get('context', {})
            context = AgentContext(
                core_summary=context_data.get('core_summary', ''),
                key_records=context_data.get('key_records', []),
                others_summary=context_data.get('others_summary', '')
            )
            agents[agent_id] = Agent(
                agent_id=agent_data.get('agent_id', agent_id),
                name=agent_data.get('name', ''),
                role_desc=agent_data.get('role_desc', ''),
                llm_id=agent_data.get('llm_id', ''),
                context=context,
                speech_history=agent_data.get('speech_history', [])
            )
        
        discussion_log = []
        for log_data in data.get('discussion_log', []):
            discussion_log.append(DiscussionLogEntry(
                timestamp=log_data.get('timestamp', ''),
                type=log_data.get('type', ''),
                speaker=log_data.get('speaker', ''),
                content=log_data.get('content', ''),
                metadata=log_data.get('metadata', {})
            ))
        
        return Meeting(
            meeting_id=data.get('meeting_id', ''),
            topic=data.get('topic', ''),
            host_name=data.get('host_name', '主持人'),
            create_time=data.get('create_time', ''),
            is_running=data.get('is_running', False),
            llm_configs=llm_configs,
            agents=agents,
            discussion_log=discussion_log,
            summary=data.get('summary', ''),
            round_summaries=data.get('round_summaries', []),
            current_round=data.get('current_round', 0),
            meeting_background=data.get('meeting_background', ''),
            meeting_goal=data.get('meeting_goal', ''),
            host_llm_id=data.get('host_llm_id', ''),
            generated_experts=data.get('generated_experts', []),
            current_speaker_agent_id=data.get('current_speaker_agent_id', ''),
            round_speaker_order=data.get('round_speaker_order', []),
            waiting_for_user_input=data.get('waiting_for_user_input', False),
            user_input=data.get('user_input', ''),
            current_step=data.get('current_step', 1),
            round_phase=data.get('round_phase', '')
        )
    
    def _load_meetings_from_disk(self):
        if not os.path.exists(MEETINGS_DIR):
            return
        for filename in os.listdir(MEETINGS_DIR):
            if filename.endswith('.json'):
                path = os.path.join(MEETINGS_DIR, filename)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        meeting = self._load_meeting_from_dict(data)
                        self.meetings[meeting.meeting_id] = meeting
                        for llm_id, llm_config in meeting.llm_configs.items():
                            if llm_id not in self.llm_client_pool:
                                self.llm_client_pool[llm_id] = LLMClient(llm_config)
                except Exception as e:
                    print(f"加载会议文件失败 {filename}: {e}")
    
    def get_llm_client(self, llm_id: str) -> Optional[LLMClient]:
        return self.llm_client_pool.get(llm_id)
    
    def create_meeting(self, topic: str, host_name: str = "主持人") -> Meeting:
        meeting_id = str(uuid.uuid4())
        meeting = Meeting(
            meeting_id=meeting_id,
            topic=topic,
            host_name=host_name,
            create_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        self.meetings[meeting_id] = meeting
        self._save_meeting_to_disk(meeting)
        return meeting
    
    def get_meeting(self, meeting_id: str) -> Optional[Meeting]:
        return self.meetings.get(meeting_id)
    
    def register_llm(self, meeting_id: str, llm_config: LLMConfig) -> bool:
        meeting = self.get_meeting(meeting_id)
        if not meeting:
            return False
        meeting.llm_configs[llm_config.llm_id] = llm_config
        if llm_config.llm_id not in self.llm_client_pool:
            self.llm_client_pool[llm_config.llm_id] = LLMClient(llm_config)
        self._save_meeting_to_disk(meeting)
        return True
    
    def remove_llm(self, meeting_id: str, llm_id: str) -> bool:
        meeting = self.get_meeting(meeting_id)
        if not meeting or llm_id not in meeting.llm_configs:
            return False
        del meeting.llm_configs[llm_id]
        if llm_id in self.llm_client_pool:
            del self.llm_client_pool[llm_id]
        self._save_meeting_to_disk(meeting)
        return True
    
    def update_llm(self, meeting_id: str, llm_id: str, llm_config: LLMConfig) -> bool:
        meeting = self.get_meeting(meeting_id)
        if not meeting or llm_id not in meeting.llm_configs:
            return False
        
        existing_config = meeting.llm_configs[llm_id]
        
        updated_config = LLMConfig(
            llm_id=llm_config.llm_id,
            api_key=llm_config.api_key if llm_config.api_key else existing_config.api_key,
            base_url=llm_config.base_url,
            default_model=llm_config.default_model,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens
        )
        
        meeting.llm_configs[llm_id] = updated_config
        if llm_id in self.llm_client_pool:
            del self.llm_client_pool[llm_id]
        self.llm_client_pool[llm_id] = LLMClient(updated_config)
        self._save_meeting_to_disk(meeting)
        return True
    
    def update_meeting_info(self, meeting_id: str, topic: str, meeting_background: str, meeting_goal: str, host_llm_id: str) -> bool:
        meeting = self.get_meeting(meeting_id)
        if not meeting:
            return False
        meeting.topic = topic
        meeting.meeting_background = meeting_background
        meeting.meeting_goal = meeting_goal
        meeting.host_llm_id = host_llm_id
        meeting.current_step = 3
        self._save_meeting_to_disk(meeting)
        return True
    
    def update_generated_expert(self, meeting_id: str, expert_index: int, name: str, role_desc: str) -> bool:
        meeting = self.get_meeting(meeting_id)
        if not meeting or expert_index >= len(meeting.generated_experts):
            return False
        meeting.generated_experts[expert_index]['name'] = name
        meeting.generated_experts[expert_index]['role_desc'] = role_desc
        self._save_meeting_to_disk(meeting)
        return True
    
    def update_agent_info(self, meeting_id: str, agent_id: str, name: str, role_desc: str) -> bool:
        meeting = self.get_meeting(meeting_id)
        if not meeting or agent_id not in meeting.agents:
            return False
        meeting.agents[agent_id].name = name
        meeting.agents[agent_id].role_desc = role_desc
        self._save_meeting_to_disk(meeting)
        return True
    
    def update_current_step(self, meeting_id: str, step: int) -> bool:
        meeting = self.get_meeting(meeting_id)
        if not meeting:
            return False
        meeting.current_step = step
        self._save_meeting_to_disk(meeting)
        return True
    
    def delete_meeting(self, meeting_id: str) -> bool:
        meeting = self.get_meeting(meeting_id)
        if not meeting:
            return False
        del self.meetings[meeting_id]
        path = self._get_meeting_path(meeting_id)
        if os.path.exists(path):
            os.remove(path)
        return True
    
    def generate_experts(self, meeting_id: str) -> Optional[List[Dict]]:
        meeting = self.get_meeting(meeting_id)
        if not meeting or not meeting.host_llm_id:
            return None
        
        llm_client = self.get_llm_client(meeting.host_llm_id)
        if not llm_client:
            return None
        
        prompt = f"""根据以下会议信息，生成5-8个合适的与会专家角色。

会议主题：{meeting.topic}
会议背景：{meeting.meeting_background}
会议目标：{meeting.meeting_goal}

请以JSON格式返回，格式如下：
[
  {{"name": "专家名称", "role_desc": "详细的角色描述和职责"}},
  ...
]

只返回JSON，不要其他文字。"""
        
        try:
            response = llm_client.call_sync(prompt)
            experts = json.loads(response)
            meeting.generated_experts = experts
            meeting.current_step = 4
            self._save_meeting_to_disk(meeting)
            return experts
        except Exception as e:
            print(f"生成专家失败: {e}")
            return None
    
    def select_experts(self, meeting_id: str, expert_selections: List[Dict]) -> bool:
        meeting = self.get_meeting(meeting_id)
        if not meeting or not meeting.generated_experts:
            return False
        
        for selection in expert_selections:
            idx = selection.get('expert_index')
            llm_id = selection.get('llm_id', meeting.host_llm_id)
            if idx < 0 or idx >= len(meeting.generated_experts):
                continue
            if llm_id not in meeting.llm_configs:
                continue
            expert = meeting.generated_experts[idx]
            agent_id = str(uuid.uuid4())
            agent = Agent(
                agent_id=agent_id,
                name=expert['name'],
                role_desc=expert['role_desc'],
                llm_id=llm_id
            )
            meeting.agents[agent_id] = agent
        
        meeting.current_step = 5
        self._save_meeting_to_disk(meeting)
        return True
    
    def create_agent(self, meeting_id: str, name: str, role_desc: str, llm_id: str) -> Optional[Agent]:
        meeting = self.get_meeting(meeting_id)
        if not meeting or llm_id not in meeting.llm_configs:
            return None
        agent_id = str(uuid.uuid4())
        agent = Agent(
            agent_id=agent_id,
            name=name,
            role_desc=role_desc,
            llm_id=llm_id
        )
        meeting.agents[agent_id] = agent
        self._save_meeting_to_disk(meeting)
        return agent
    
    def switch_agent_llm(self, meeting_id: str, agent_id: str, llm_id: str) -> bool:
        meeting = self.get_meeting(meeting_id)
        if not meeting or agent_id not in meeting.agents or llm_id not in meeting.llm_configs:
            return False
        meeting.agents[agent_id].llm_id = llm_id
        self._save_meeting_to_disk(meeting)
        return True
    
    def start_meeting(self, meeting_id: str) -> Optional[Dict]:
        meeting = self.get_meeting(meeting_id)
        if not meeting:
            return None
        meeting.is_running = True
        meeting.current_round = 1
        meeting.current_step = 5
        meeting.round_phase = 'experts_first_speaking'
        meeting.round_speaker_order = list(meeting.agents.keys())
        meeting.current_speaker_agent_id = ""
        
        self._save_meeting_to_disk(meeting)
        return {
            'success': True
        }
    
    def start_new_round(self, meeting_id: str, user_input: str = '') -> Optional[Dict]:
        meeting = self.get_meeting(meeting_id)
        if not meeting or not meeting.is_running:
            return None
        
        meeting.current_round += 1
        meeting.round_phase = 'host_intro'
        meeting.waiting_for_user_input = False
        if user_input.strip():
            meeting.user_input = user_input
        meeting.round_speaker_order = list(meeting.agents.keys())
        meeting.current_speaker_agent_id = ""
        
        additional_context = ''
        if user_input.strip():
            additional_context = f"\n用户补充意见：{user_input}"
            self._add_log_entry(meeting, 'user', '用户', user_input)
        
        host_intro = self.generate_host_speech(meeting_id, 'round_intro', additional_context)
        if host_intro:
            self._add_log_entry(meeting, 'host', meeting.host_name, host_intro)
        
        meeting.round_phase = 'agents_speaking'
        self._save_meeting_to_disk(meeting)
        
        return {
            'round': meeting.current_round,
            'host_intro': host_intro,
            'speaker_order': [meeting.agents[aid].name for aid in meeting.round_speaker_order]
        }
    
    def get_next_speaker(self, meeting_id: str) -> Optional[Dict]:
        meeting = self.get_meeting(meeting_id)
        if not meeting or not meeting.is_running:
            return None
        
        if not meeting.round_speaker_order:
            return {'finished': True}
        
        next_agent_id = meeting.round_speaker_order.pop(0)
        meeting.current_speaker_agent_id = next_agent_id
        self._save_meeting_to_disk(meeting)
        return {
            'finished': False,
            'agent_id': next_agent_id
        }
    

    
    def add_user_input(self, meeting_id: str, user_input: str) -> bool:
        meeting = self.get_meeting(meeting_id)
        if not meeting or not meeting.is_running or not meeting.waiting_for_user_input:
            return False
        
        if user_input.strip():
            meeting.user_input = user_input
            self._add_log_entry(meeting, 'user', '用户', user_input)
        
        meeting.waiting_for_user_input = False
        self._save_meeting_to_disk(meeting)
        return True
    
    def generate_final_summary(self, meeting_id: str) -> Optional[str]:
        meeting = self.get_meeting(meeting_id)
        if not meeting or meeting.host_llm_id not in meeting.llm_configs:
            return None
        
        llm_client = self.get_llm_client(meeting.host_llm_id)
        if not llm_client:
            return None
        
        all_speeches = '\n'.join([
            f"{agent.name}: {speech['content']}"
            for agent in meeting.agents.values()
            for speech in agent.speech_history
        ])
        
        round_summaries_text = '\n'.join([
            f"第{rs['round']}轮: {rs['summary']}"
            for rs in meeting.round_summaries
        ])
        
        prompt = f"""作为会议主持人，请生成最终的会议总结。

会议主题：{meeting.topic}
会议背景：{meeting.meeting_background}
会议目标：{meeting.meeting_goal}
会议轮次：{meeting.current_round}轮

各轮总结：
{round_summaries_text}

完整讨论内容：
{all_speeches}

请生成一份全面的会议总结，包括：
1. 会议概述
2. 主要讨论点
3. 达成的结论
4. 后续建议"""
        
        summary = llm_client.call_sync(prompt)
        meeting.summary = summary
        meeting.is_running = False
        self._save_meeting_to_disk(meeting)
        return summary
    
    def _add_log_entry(self, meeting: Meeting, entry_type: str, speaker: str, content: str, metadata: Optional[Dict] = None):
        entry = DiscussionLogEntry(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            type=entry_type,
            speaker=speaker,
            content=content,
            metadata=metadata or {}
        )
        meeting.discussion_log.append(entry)
    
    def _build_host_prompt(self, meeting: Meeting, speech_type: str, additional_context: str = '') -> Optional[str]:
        if speech_type == 'opening':
            return f"""你是本次会议的主持人{meeting.host_name}。

会议的主题是{meeting.topic}
背景是{meeting.meeting_background}
目标是{meeting.meeting_goal}

请以主持人的身份发表开场白，介绍会议的主题、背景和目标，并请各位专家开始讨论。
注意：
- 语气要友好、专业
- 如果用户给了资料，需要在输出的最后中包含资料并在前面加上“用户给出的XXX资料：”
- 直接说主持人的开场白，不要有其他说明"""
        
        elif speech_type == 'round_intro':
            return f"""你是本次会议的主持人{meeting.host_name}。

请以主持人的身份介绍本轮讨论的主题，请各位专家继续讨论。
注意：
- 语气要友好、专业
- 如果用户给了资料，需要在输出的最后中包含资料并在前面加上“用户给出的XXX资料：”
- 直接说主持人的话，不要有其他说明"""
        
        elif speech_type == 'first_proposal':
            round_logs = [
                log for log in meeting.discussion_log
                if log.type in ['agent']
            ]
            
            round_content = '\n'.join([
                f"{log.speaker}: {log.content}"
                for log in round_logs[-len(meeting.agents):]
            ])
            
            return f"""你是本次会议的主持人{meeting.host_name}。
会议主题：{meeting.topic}
会议目标：{meeting.meeting_goal}

专家发言内容：
{round_content}

请整合专家的意见，给出针对会议目标的初步方案。
注意：
- 语气要友好、专业
- 直接说主持人的话，不要有其他说明"""
        
        elif speech_type == 'process_user_input':
            return f"""你是本次会议的主持人{meeting.host_name}。
用户输入：{additional_context}

请梳理用户的核心诉求，并说明需要专家进一步优化。
请以固定格式输出：用户核心诉求：XXX，需专家进一步优化
注意：
- 语气要友好、专业
- 优化内容要和用户核心诉求和会议目标相关,如果有用户资料要和资料内容相关
- 如果用户给了资料，需要在输出的最后中包含资料并在前面加上“用户给出的XXX资料：”
- 必须严格按照固定格式输出"""
        
        elif speech_type == 'second_proposal':
            round_logs = [
                log for log in meeting.discussion_log
                if log.type in ['agent']
            ]
            
            round_content = '\n'.join([
                f"{log.speaker}: {log.content}"
                for log in round_logs[-len(meeting.agents):]
            ])
            
            return f"""你是本次会议的主持人{meeting.host_name}。
会议主题：{meeting.topic}
会议目标：{meeting.meeting_goal}

专家最新发言内容：
{round_content}

请整合专家的新建议，给出优化后的方案。
注意：
- 语气要友好、专业
- 直接说主持人的话，不要有其他说明"""
        
        return None
    
    def generate_host_speech(self, meeting_id: str, speech_type: str, additional_context: str = '') -> Optional[str]:
        meeting = self.get_meeting(meeting_id)
        if not meeting or not meeting.host_llm_id or meeting.host_llm_id not in meeting.llm_configs:
            return None
        
        llm_client = self.get_llm_client(meeting.host_llm_id)
        if not llm_client:
            return None
        
        prompt = self._build_host_prompt(meeting, speech_type, additional_context)
        if not prompt:
            return None
        
        try:
            return llm_client.call_sync(prompt)
        except Exception as e:
            print(f"主持人生成发言失败: {e}")
            return None
    
    def generate_host_speech_stream(self, meeting_id: str, speech_type: str, additional_context: str = '') -> Generator[str, None, None]:
        meeting = self.get_meeting(meeting_id)
        if not meeting or meeting.host_llm_id not in meeting.llm_configs:
            return
        
        if speech_type == 'opening':
            meeting.round_phase = 'opening'
        elif speech_type == 'first_proposal':
            meeting.round_phase = 'host_first_proposal'
        elif speech_type == 'process_user_input':
            meeting.round_phase = 'host_process_user_input'
            if additional_context.strip():
                self._add_log_entry(meeting, 'user', '用户', additional_context)
        elif speech_type == 'second_proposal':
            meeting.round_phase = 'host_second_proposal'
        
        llm_client = self.get_llm_client(meeting.host_llm_id)
        if not llm_client:
            return
        
        prompt = self._build_host_prompt(meeting, speech_type, additional_context)
        if not prompt:
            return
        
        full_content = []
        for text in llm_client.call_stream(prompt):
            full_content.append(text)
            yield text
        
        speech_text = ''.join(full_content)
        self._add_log_entry(meeting, 'host', meeting.host_name, speech_text)
        
        if speech_type == 'opening':
            meeting.round_phase = 'experts_first_speaking'
            meeting.round_speaker_order = list(meeting.agents.keys())
            meeting.current_speaker_agent_id = ""
        elif speech_type == 'first_proposal':
            meeting.round_phase = 'user_decision'
        elif speech_type == 'process_user_input':
            meeting.round_phase = 'experts_iteration'
            meeting.round_speaker_order = list(meeting.agents.keys())
            meeting.current_speaker_agent_id = ""
        elif speech_type == 'second_proposal':
            meeting.round_phase = 'user_decision'
        
        self._save_meeting_to_disk(meeting)
    
    def generate_agent_speech_stream(self, meeting_id: str, agent_id: str, instruction: str) -> Generator[str, None, None]:
        meeting = self.get_meeting(meeting_id)
        if not meeting or agent_id not in meeting.agents:
            return
        
        agent = meeting.agents[agent_id]
        llm_client = self.get_llm_client(agent.llm_id)
        if not llm_client:
            return
        
        prompt = self._build_agent_prompt(agent, meeting, instruction)
        
        full_content = []
        for text in llm_client.call_stream(prompt):
            full_content.append(text)
            yield text
        
        speech_text = ''.join(full_content)
        self._update_agent_context(agent, speech_text, llm_client)
        agent.speech_history.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'content': speech_text
        })
        self._add_log_entry(meeting, 'agent', agent.name, speech_text, {'agent_id': agent_id})
        self._save_meeting_to_disk(meeting)
    
    def _build_agent_prompt(self, agent: Agent, meeting: Meeting, instruction: str) -> str:
        prompt = f"""你是{agent.name}，你的角色定位：{agent.role_desc}。"""
        
        if agent.context.core_summary:
            prompt += f"""

【你之前的核心观点】：{agent.context.core_summary}"""
        
        if agent.context.key_records:
            prompt += f"""

【你的关键发言记录】：
"""
            for i, record in enumerate(agent.context.key_records, 1):
                prompt += f"{i}. {record}\n"
        
        if agent.context.others_summary:
            prompt += f"""

【本轮其他专家的观点汇总】：{agent.context.others_summary}"""
        
        prompt += f"""

【主持人的话】：{instruction}

请根据以上信息发表你的看法。"""
        
        return prompt
    
    def _update_agent_context(self, agent: Agent, speech_text: str, llm_client: LLMClient):
        try:
            prompt = f"""请为以下发言生成两条内容：
1. 核心观点摘要（不超过50字）
2. 关键发言记录（保留原内容的精简版本）

发言内容：
{speech_text}

请以JSON格式返回，格式如下：
{{
  "coreSummary": "核心观点摘要",
  "keyRecord": "关键发言记录"
}}
要求：
- coreSummary不超过50字
- keyRecord保留原发言的核心内容，控制在200字以内
- 只返回JSON，不要其他文字说明"""
            
            response = llm_client.call_sync(prompt)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                agent.context.core_summary = result.get('coreSummary', '')
                key_record = result.get('keyRecord', '')
                if key_record:
                    agent.context.key_records.append(key_record)
                    if len(agent.context.key_records) > 2:
                        agent.context.key_records = agent.context.key_records[-2:]
        except Exception as e:
            print(f"更新Agent上下文失败: {e}")
    
    def update_others_summary(self, meeting_id: str, summary: str):
        meeting = self.get_meeting(meeting_id)
        if not meeting:
            return
        for agent in meeting.agents.values():
            agent.context.others_summary = summary
        self._save_meeting_to_disk(meeting)
    
    def end_meeting(self, meeting_id: str) -> Optional[str]:
        meeting = self.get_meeting(meeting_id)
        if not meeting:
            return None
        
        meeting.is_running = False
        meeting.current_step = 6
        self._add_log_entry(meeting, 'system', meeting.host_name, '会议结束')
        
        if meeting.llm_configs:
            llm_id = next(iter(meeting.llm_configs.keys()))
            llm_client = self.get_llm_client(llm_id)
            if llm_client:
                summary = self._generate_meeting_summary(meeting, llm_client)
                meeting.summary = summary
                self._add_log_entry(meeting, 'summary', meeting.host_name, summary)
        
        self._save_meeting_to_disk(meeting)
        return meeting.summary
    
    def _generate_meeting_summary(self, meeting: Meeting, llm_client: LLMClient) -> str:
        log_text = "\n".join([
            f"[{entry.timestamp}] {entry.speaker}: {entry.content}"
            for entry in meeting.discussion_log
        ])
        
        prompt = f"""会议主题：{meeting.topic}

会议记录：
{log_text}

请生成一份详细的会议总结，包括：
1. 讨论要点
2. 达成的共识
3. 待办事项
4. 后续建议

请用简洁明了的语言进行总结。"""
        
        return llm_client.call_sync(prompt)
    
    def generate_meeting_info(self, llm_id: str, user_input: str) -> Optional[Dict]:
        llm_client = self.get_llm_client(llm_id)
        if not llm_client:
            return None
        
        prompt = f"""你是一位专业的会议策划专家。请仔细分析用户提供的简单想法，生成多个会议信息选项供用户选择。

用户的想法：{user_input}

请以JSON格式返回结果，包含以下字段：
- "topics": 5个会议主题的数组（每个主题简洁明了，不超过20字）
- "backgrounds": 5个会议背景的数组（描述会议召开的原因和环境）
- "goals": 5个会议目标的数组（明确本次会议要达成的具体目标）

只返回JSON，不要其他内容！"""
        
        try:
            response = llm_client.call_sync(prompt)
            import re
            json_match = re.search(r'({[\s\S]*})', response)
            if json_match:
                import json
                result = json.loads(json_match.group(1))
                return {
                    'topics': result.get('topics', []),
                    'backgrounds': result.get('backgrounds', []),
                    'goals': result.get('goals', [])
                }
            return None
        except Exception as e:
            print(f"生成会议信息失败: {e}")
            return None


manager = MeetingSystemManager()


def json_response(code: int, message: str, data: Any = None):
    return jsonify({
        'code': code,
        'message': message,
        'data': data
    })


@app.route('/api/generate-meeting-info', methods=['POST'])
def generate_meeting_info():
    try:
        data = request.get_json() or {}
        llm_id = data.get('llm_id', '')
        user_input = data.get('user_input', '')
        if not llm_id or not user_input:
            return json_response(400, '参数错误'), 400
        result = manager.generate_meeting_info(llm_id, user_input)
        if result:
            return json_response(200, '成功', result)
        return json_response(400, '生成失败'), 400
    except Exception as e:
        return json_response(500, f'失败: {str(e)}'), 500


@app.route('/api/health', methods=['GET'])
def health():
    return json_response(200, 'ok')


@app.route('/api/meetings', methods=['GET'])
def list_meetings():
    meetings = []
    if os.path.exists(MEETINGS_DIR):
        for filename in os.listdir(MEETINGS_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(MEETINGS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        meetings.append({
                            'meeting_id': data.get('meeting_id', ''),
                            'topic': data.get('topic', '未命名会议'),
                            'create_time': data.get('create_time', ''),
                            'is_running': data.get('is_running', False),
                            'has_summary': bool(data.get('summary', ''))
                        })
                except Exception as e:
                    print(f'Error reading {filename}: {e}')
                    continue
    
    meetings.sort(key=lambda x: x['create_time'], reverse=True)
    return jsonify({'code': 200, 'data': meetings})


@app.route('/api/meeting/create', methods=['POST'])
def create_meeting():
    try:
        data = request.get_json()
        topic = data.get('topic', '')
        host_name = data.get('host_name', '主持人')
        
        if not topic:
            return json_response(400, '请输入会议主题'), 400
        
        meeting = manager.create_meeting(topic, host_name)
        return json_response(200, '创建成功', {'meeting_id': meeting.meeting_id})
    except Exception as e:
        return json_response(500, f'创建失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>', methods=['GET'])
def get_meeting(meeting_id):
    meeting = manager.get_meeting(meeting_id)
    if not meeting:
        return json_response(404, '会议不存在'), 404
    
    meeting_dict = asdict(meeting)
    for llm_id in meeting_dict.get('llm_configs', {}):
        if 'api_key' in meeting_dict['llm_configs'][llm_id]:
            del meeting_dict['llm_configs'][llm_id]['api_key']
    
    return json_response(200, '查询成功', meeting_dict)


@app.route('/api/meeting/<meeting_id>/start', methods=['POST'])
def start_meeting(meeting_id):
    result = manager.start_meeting(meeting_id)
    if result:
        return json_response(200, '会议已启动', result)
    return json_response(404, '会议不存在'), 404


@app.route('/api/meeting/<meeting_id>/end', methods=['POST'])
def end_meeting(meeting_id):
    summary = manager.end_meeting(meeting_id)
    if summary is not None:
        return json_response(200, '会议已结束', {'summary': summary})
    return json_response(404, '会议不存在'), 404


@app.route('/api/meeting/<meeting_id>/llm/register', methods=['POST'])
def register_llm(meeting_id):
    try:
        data = request.get_json()
        
        llm_id = data.get('llm_id', str(uuid.uuid4()))
        
        meeting = manager.get_meeting(meeting_id)
        if not meeting:
            return json_response(404, '会议不存在'), 404
        
        if llm_id in meeting.llm_configs:
            return json_response(409, 'LLM已存在'), 409
        
        llm_config = LLMConfig(
            llm_id=llm_id,
            api_key=decrypt(data['api_key']),
            base_url=data['base_url'],
            default_model=data.get('default_model', 'gpt-3.5-turbo'),
            temperature=data.get('temperature', 0.7),
            max_tokens=data.get('max_tokens', 2000)
        )
        
        if manager.register_llm(meeting_id, llm_config):
            return json_response(200, 'LLM注册成功', {'llm_id': llm_config.llm_id})
        return json_response(404, '会议不存在'), 404
    except Exception as e:
        return json_response(500, f'注册失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/llm/<llm_id>', methods=['DELETE'])
def remove_llm(meeting_id, llm_id):
    try:
        if manager.remove_llm(meeting_id, llm_id):
            return json_response(200, 'LLM删除成功')
        return json_response(404, '会议或LLM不存在'), 404
    except Exception as e:
        return json_response(500, f'删除失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/llm/<llm_id>', methods=['PUT'])
def update_llm(meeting_id, llm_id):
    try:
        data = request.get_json()
        
        meeting = manager.get_meeting(meeting_id)
        if not meeting:
            return json_response(404, '会议不存在'), 404
        
        if llm_id not in meeting.llm_configs:
            return json_response(404, 'LLM不存在'), 404
        
        api_key = data.get('api_key')
        if api_key:
            api_key = decrypt(api_key)
        else:
            api_key = meeting.llm_configs[llm_id].api_key
        
        llm_config = LLMConfig(
            llm_id=llm_id,
            api_key=api_key,
            base_url=data.get('base_url', meeting.llm_configs[llm_id].base_url),
            default_model=data.get('default_model', meeting.llm_configs[llm_id].default_model),
            temperature=data.get('temperature', meeting.llm_configs[llm_id].temperature),
            max_tokens=data.get('max_tokens', meeting.llm_configs[llm_id].max_tokens)
        )
        
        if manager.update_llm(meeting_id, llm_id, llm_config):
            return json_response(200, 'LLM更新成功')
        return json_response(404, '会议或LLM不存在'), 404
    except Exception as e:
        return json_response(500, f'更新失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/info', methods=['PUT'])
def update_meeting_info(meeting_id):
    try:
        data = request.get_json()
        if manager.update_meeting_info(
            meeting_id,
            data.get('topic', ''),
            data.get('meeting_background', ''),
            data.get('meeting_goal', ''),
            data.get('host_llm_id', '')
        ):
            return json_response(200, '会议信息更新成功')
        return json_response(404, '会议不存在'), 404
    except Exception as e:
        return json_response(500, f'更新失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/experts/generate', methods=['POST'])
def generate_experts(meeting_id):
    try:
        experts = manager.generate_experts(meeting_id)
        if experts is not None:
            return json_response(200, '专家生成成功', {'experts': experts})
        return json_response(400, '生成失败，请确保已选择主持人LLM'), 400
    except Exception as e:
        return json_response(500, f'生成失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/experts/select', methods=['POST'])
def select_experts(meeting_id):
    try:
        data = request.get_json()
        expert_selections = data.get('expert_selections', [])
        if manager.select_experts(meeting_id, expert_selections):
            return json_response(200, '专家选择成功')
        return json_response(400, '选择失败'), 400
    except Exception as e:
        return json_response(500, f'选择失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/expert/<int:expert_index>/update', methods=['PUT'])
def update_generated_expert(meeting_id, expert_index):
    try:
        data = request.get_json()
        name = data.get('name', '')
        role_desc = data.get('role_desc', '')
        if manager.update_generated_expert(meeting_id, expert_index, name, role_desc):
            return json_response(200, '更新成功')
        return json_response(400, '更新失败'), 400
    except Exception as e:
        return json_response(500, f'更新失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/agent/<agent_id>/update', methods=['PUT'])
def update_agent_info(meeting_id, agent_id):
    try:
        data = request.get_json()
        name = data.get('name', '')
        role_desc = data.get('role_desc', '')
        if manager.update_agent_info(meeting_id, agent_id, name, role_desc):
            return json_response(200, '更新成功')
        return json_response(400, '更新失败'), 400
    except Exception as e:
        return json_response(500, f'更新失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/step/update', methods=['PUT'])
def update_step(meeting_id):
    try:
        data = request.get_json()
        step = data.get('step', 1)
        if manager.update_current_step(meeting_id, step):
            return json_response(200, '更新成功')
        return json_response(400, '更新失败'), 400
    except Exception as e:
        return json_response(500, f'更新失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/delete', methods=['DELETE'])
def delete_meeting(meeting_id):
    try:
        if manager.delete_meeting(meeting_id):
            return json_response(200, '删除成功')
        return json_response(404, '会议不存在'), 404
    except Exception as e:
        return json_response(500, f'删除失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/agent/create', methods=['POST'])
def create_agent(meeting_id):
    try:
        data = request.get_json()
        
        agent = manager.create_agent(
            meeting_id,
            data['name'],
            data['role_desc'],
            data['llm_id']
        )
        
        if agent:
            return json_response(200, 'Agent创建成功', asdict(agent))
        return json_response(404, '会议不存在或LLM未注册'), 404
    except Exception as e:
        return json_response(500, f'创建失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/agent/<agent_id>/llm', methods=['PATCH'])
def switch_agent_llm(meeting_id, agent_id):
    try:
        data = request.get_json()
        
        if manager.switch_agent_llm(meeting_id, agent_id, data['llm_id']):
            return json_response(200, '切换成功')
        return json_response(404, '会议/Agent/LLM不存在'), 404
    except Exception as e:
        return json_response(500, f'切换失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/agent/<agent_id>/speak', methods=['GET'])
def agent_speak(meeting_id, agent_id):
    instruction = request.args.get('instruction', '请发表你的看法')
    
    def generate():
        yield f"data: {json.dumps({'type': 'start'}, ensure_ascii=False)}\n\n"
        
        full_content = []
        for text in manager.generate_agent_speech_stream(meeting_id, agent_id, instruction):
            full_content.append(text)
            yield f"data: {json.dumps({'type': 'content', 'content': text}, ensure_ascii=False)}\n\n"
        
        yield f"data: {json.dumps({'type': 'end', 'content': ''.join(full_content)}, ensure_ascii=False)}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/meeting/<meeting_id>/summary', methods=['GET'])
def get_summary(meeting_id):
    meeting = manager.get_meeting(meeting_id)
    if not meeting:
        return json_response(404, '会议不存在'), 404
    return json_response(200, '查询成功', {'summary': meeting.summary})


@app.route('/api/meeting/<meeting_id>/round-summary', methods=['POST'])
def round_summary(meeting_id):
    try:
        data = request.get_json()
        summary = data.get('summary', '')
        
        meeting = manager.get_meeting(meeting_id)
        if not meeting:
            return json_response(404, '会议不存在'), 404
        
        meeting.current_round += 1
        meeting.round_summaries.append({
            'round_number': meeting.current_round,
            'content': summary,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        manager.update_others_summary(meeting_id, summary)
        manager._add_log_entry(meeting, 'round_summary', meeting.host_name, summary, {'round': meeting.current_round})
        manager._save_meeting_to_disk(meeting)
        
        return json_response(200, '汇总成功', {'round_number': meeting.current_round})
    except Exception as e:
        return json_response(500, f'汇总失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/round/start', methods=['POST'])
def start_new_round(meeting_id):
    try:
        data = request.get_json() or {}
        user_input = data.get('user_input', '')
        result = manager.start_new_round(meeting_id, user_input)
        if result:
            return json_response(200, '新一轮开始', result)
        return json_response(400, '开始失败'), 400
    except Exception as e:
        return json_response(500, f'开始失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/speaker/next', methods=['POST'])
def get_next_speaker(meeting_id):
    try:
        result = manager.get_next_speaker(meeting_id)
        if result:
            if result['finished']:
                return json_response(200, '本轮已结束', {'finished': True})
            else:
                meeting = manager.get_meeting(meeting_id)
                agent = meeting.agents[result['agent_id']]
                return json_response(200, '获取成功', {
                    'agent_id': result['agent_id'],
                    'agent_name': agent.name,
                    'finished': False
                })
        return json_response(400, '获取失败'), 400
    except Exception as e:
        return json_response(500, f'获取失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/round/summary', methods=['POST'])
def generate_round_summary(meeting_id):
    try:
        summary = manager.generate_round_summary(meeting_id)
        if summary:
            return json_response(200, '汇总成功', {'summary': summary})
        return json_response(400, '汇总失败'), 400
    except Exception as e:
        return json_response(500, f'汇总失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/user/input', methods=['POST'])
def add_user_input(meeting_id):
    try:
        data = request.get_json()
        user_input = data.get('input', '')
        if manager.add_user_input(meeting_id, user_input):
            return json_response(200, '补充成功')
        return json_response(400, '补充失败'), 400
    except Exception as e:
        return json_response(500, f'补充失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/final/summary', methods=['POST'])
def generate_final_summary(meeting_id):
    try:
        summary = manager.generate_final_summary(meeting_id)
        if summary:
            return json_response(200, '总结成功', {'summary': summary})
        return json_response(400, '总结失败'), 400
    except Exception as e:
        return json_response(500, f'总结失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/host/summary', methods=['POST'])
def host_round_summary(meeting_id):
    try:
        summary = manager.host_round_summary(meeting_id)
        if summary:
            return json_response(200, '汇总成功', {'summary': summary})
        return json_response(400, '汇总失败'), 400
    except Exception as e:
        return json_response(500, f'汇总失败: {str(e)}'), 500


@app.route('/api/meeting/<meeting_id>/host/speak', methods=['GET'])
def host_speak(meeting_id):
    speech_type = request.args.get('speech_type', '')
    additional_context = request.args.get('additional_context', '')
    
    def generate():
        try:
            for text in manager.generate_host_speech_stream(meeting_id, speech_type, additional_context):
                yield f"data: {json.dumps({'type': 'content', 'content': text}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'end'}, ensure_ascii=False)}\n\n"
        except Exception as e:
            print(f"主持人流式发言错误: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
