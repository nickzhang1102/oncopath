"""Agent配置加载器

从 back/agents 目录动态加载专家配置
"""
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class AgentLoader:
    """Agent配置加载器

    从 back/agents 目录读取 Markdown格式的专家配置文件
    """

    CACHE_TTL = 300  # 5分钟缓存过期

    def __init__(self, agents_dir: str = None):
        """初始化加载器

        Args:
            agents_dir: agents目录路径，默认为 back/agents
        """
        if agents_dir is None:
            # 后端根目录: Docker WORKDIR=/app (back/ 被复制到 /app), 本地为 back/
            # agent_loader.py 位于 back/app/utils/, parent.parent.parent = back/
            back_root = Path(__file__).resolve().parent.parent.parent
            agents_dir = back_root / "agents"

        self.agents_dir = Path(agents_dir)
        self._cache = None
        self._cache_time: float = 0.0

    def load_all_agents(self, use_cache: bool = True) -> Dict[str, dict]:
        """加载所有agent配置

        Args:
            use_cache: 是否使用缓存

        Returns:
            专家配置字典，格式兼容MEDICAL_EXPERTS
        """
        if use_cache and self._cache is not None and (time.monotonic() - self._cache_time) < self.CACHE_TTL:
            return self._cache

        agents = {}

        if not self.agents_dir.exists():
            logger.warning(f"agents目录不存在: {self.agents_dir}")
            return agents

        for md_file in self.agents_dir.glob("*-expert.md"):
            try:
                agent_config = self._parse_agent_file(md_file)
                if agent_config:
                    expert_name = agent_config.get("name")
                    if expert_name:
                        agents[expert_name] = agent_config
                        logger.debug(f"成功加载专家配置: {expert_name}")
            except Exception as e:
                logger.error(f"解析agent文件失败 {md_file}: {e}")

        if use_cache:
            self._cache = agents
            self._cache_time = time.monotonic()

        logger.info(f"共加载 {len(agents)} 个专家配置")
        return agents

    def _parse_agent_file(self, file_path: Path) -> Optional[dict]:
        """解析agent配置文件

        Args:
            file_path: 文件路径

        Returns:
            解析后的配置字典
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析YAML frontmatter
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
        if not frontmatter_match:
            logger.warning(f"文件格式错误，缺少frontmatter: {file_path}")
            return None

        frontmatter_text = frontmatter_match.group(1)
        body_text = frontmatter_match.group(2)

        # 解析YAML (简单实现)
        config = {}
        for line in frontmatter_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                # 处理列表
                if value.startswith('[') and value.endswith(']'):
                    # 提取列表项
                    items = re.findall(r'"([^"]+)"', value)
                    config[key] = items
                else:
                    # 去除引号
                    value = value.strip('"\'')
                    config[key] = value

        # 提取system_prompt (从Markdown body)
        config['system_prompt'] = body_text.strip()

        # 从文件名提取expert_type (例如: oncology-expert.md -> oncology)
        filename = file_path.stem  # 去除扩展名
        if filename.endswith('-expert'):
            expert_type = filename[:-7]  # 去除 -expert 后缀
            config['expert_type'] = expert_type
        else:
            config['expert_type'] = filename

        # 设置默认值
        if 'keywords' not in config:
            keywords = []

            # 1. 从description中提取关键词
            description = config.get('description', '')
            if description:
                # 提取"当需要...时使用"模式中的关键术语
                desc_keywords = re.findall(r'当需要([^时]+)时', description)
                if desc_keywords:
                    for phrase in desc_keywords:
                        # 按常见分隔符分割
                        terms = re.split(r'[、，,和与及]', phrase)
                        for term in terms:
                            term = term.strip()
                            # 只保留2-8个字符的词汇，并过滤句子片段
                            if (2 <= len(term) <= 8 and
                                not term.startswith(('和', '与', '及', '的', '了', '是')) and
                                not term.endswith(('的', '了', '是'))):
                                keywords.append(term)

            # 2. 从system_prompt中提取核心医学术语
            system_prompt = config.get('system_prompt', '')
            if system_prompt:
                # 提取疾病名称（癌症、肿瘤、炎症等）
                disease_keywords = re.findall(r'([\u4e00-\u9fa5]{1,4}(?:癌|肿瘤|瘤|炎|病|症|综合征))', system_prompt)
                keywords.extend(disease_keywords)

                # 提取治疗方式
                treatment_keywords = re.findall(r'(化疗|放疗|靶向治疗|免疫治疗|手术治疗|药物治疗|内分泌治疗|姑息治疗|综合治疗)', system_prompt)
                keywords.extend(treatment_keywords)

                # 提取器官名称（增加常见组合）
                organ_keywords = re.findall(r'(肺癌|胃癌|肝癌|胰腺癌|乳腺癌|结直肠癌|前列腺癌|膀胱癌|肾癌|卵巢癌|宫颈癌|小细胞肺癌|非小细胞肺癌)', system_prompt)
                keywords.extend(organ_keywords)

                # 提取诊断术语
                diag_keywords = re.findall(r'(EGFR|ALK|ROS1|HER2|PD-?1|PD-?L1|基因检测|分子分型|病理诊断|分期)', system_prompt)
                keywords.extend(diag_keywords)

                # 提取常见医学检查
                exam_keywords = re.findall(r'(CT|MRI|PET-?CT|影像学|病理|检验)', system_prompt)
                keywords.extend(exam_keywords)

            # 过滤：移除句子片段和无意义词汇
            filtered_keywords = []
            for keyword in keywords:
                # 跳过句子片段（以动词开头的短语）
                if any(keyword.startswith(prefix) for prefix in ['资深', '擅长', '各类', '床经', '和血液', '阳性乳']):
                    continue
                # 跳过太短或太长的关键词
                if not (2 <= len(keyword) <= 10):
                    continue
                # 添加到过滤后的列表
                filtered_keywords.append(keyword)

            # 去重并限制数量
            keywords = list(dict.fromkeys(filtered_keywords))[:25]  # 保持顺序去重，最多25个
            config['keywords'] = keywords

        if 'priority' not in config:
            config['priority'] = 99  # 默认优先级

        return config

    def get_expert_by_type(self, expert_type: str) -> Optional[dict]:
        """根据专家类型获取配置

        Args:
            expert_type: 专家类型标识（如 'oncology', 'cardiology'）

        Returns:
            专家配置字典
        """
        agents = self.load_all_agents()

        for expert_name, config in agents.items():
            if config.get("expert_type") == expert_type:
                return {
                    "expert_name": expert_name,
                    **config
                }

        logger.warning(f"未找到专家类型: {expert_type}")
        return None

    def get_all_expert_types(self) -> List[dict]:
        """获取所有专家类型列表

        Returns:
            专家类型列表
        """
        agents = self.load_all_agents()

        return [
            {
                "name": expert_name,
                "type": config.get("expert_type"),
                "priority": config.get("priority", 99)
            }
            for expert_name, config in agents.items()
        ]

    def get_expert_keywords(self, expert_type: str) -> List[str]:
        """获取指定专家的关键词列表

        Args:
            expert_type: 专家类型标识

        Returns:
            关键词列表
        """
        expert = self.get_expert_by_type(expert_type)
        return expert.get("keywords", []) if expert else []


# 全局实例
_agent_loader = None


def get_agent_loader() -> AgentLoader:
    """获取全局AgentLoader实例

    Returns:
        AgentLoader实例
    """
    global _agent_loader
    if _agent_loader is None:
        _agent_loader = AgentLoader()
    return _agent_loader