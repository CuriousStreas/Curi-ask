# -*- coding: utf-8 -*-
"""
AI 辅助指派模块 v3 - 三阶段架构
阶段1: 专注分析报错,识别关键信息(报错行、命名空间、涉及模块)
阶段2: 使用PM Agent推荐指派人（简化版prompt）
阶段3: 验证指派人是否属于L50程序或CoreTech Team
"""

import requests
import json
import os
import time
from datetime import datetime
from pm_api.yixiezuo import L18YiXieZuoTool
from pm_api.pm_agent_client import pm_agent_chat


# AI指派结果保存目录
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AI_ASSIGN_DATA_DIR = os.path.join(_SCRIPT_DIR, "ai_assign_data")


def l50chat_completions(
    query: str,
    session_id: str,
    show_think_flag: bool,
    image_list=None,
    stream: bool = True,
    api_url: str = "https://links-l50-pro.apps-sl.danlu.netease.com/api/v1/mcp_rag"
):
    """
    发送对话请求到 L50 API，支持流式响应。
    :return: 生成器，逐步返回结构化内容，格式为 (type, content)
    """
    if image_list is None:
        image_list = []

    payload = {
        "query": query,
        "stream": stream,
        "task_type": "l50",
        "session_id": session_id,
        "show_think_flag": show_think_flag,
        "short_answer_flag": True,
        "image_list": image_list
    }

    headers = {
        "Content-Type": "application/json"
    }

    with requests.post(api_url, data=json.dumps(payload), headers=headers, stream=stream) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            # 处理think和data
            if line.startswith("think:"):
                content = line[len("think:"):]
                yield ("think", content)
            elif line.startswith("data:"):
                content = line[len("data:"):]
                try:
                    data = json.loads(content)
                    yield ("data", data)
                except Exception:
                    yield ("data", content)
            else:
                # 其他情况直接返回原始内容
                yield ("raw", line)


def l50chat_completions_sync(
    query: str,
    session_id: str,
    show_think_flag: bool = False,
    image_list=None,
    stream: bool = True,
    api_url: str = "https://links-l50-pro.apps-sl.danlu.netease.com/api/v1/mcp_rag"
):
    """
    同步版本的 L50 API 调用，收集所有响应并返回完整内容
    流式响应中每个data都是一个dict，包含content字段，需要拼接content
    :return: dict 包含 think 和 data 的完整响应
    """
    result = {
        "think": "",
        "data": "",  # 拼接后的完整文本内容
        "raw": ""
    }
    
    try:
        for response_type, content in l50chat_completions(
            query=query,
            session_id=session_id,
            show_think_flag=show_think_flag,
            image_list=image_list,
            stream=stream,
            api_url=api_url
        ):
            if response_type == "think":
                result["think"] += str(content)
            elif response_type == "data":
                if isinstance(content, dict):
                    # 流式响应中，每个chunk的content在dict的'content'字段中
                    chunk_content = content.get('content', '')
                    if chunk_content:
                        result["data"] += chunk_content
                elif content == "[DONE]":
                    # 流式结束标志
                    pass
                else:
                    result["data"] += str(content)
            else:
                result["raw"] += str(content)
    except Exception as e:
        result["error"] = str(e)
        import traceback
        traceback.print_exc()
    
    return result


class AIAssignHelperV3:
    """AI 辅助指派助手 v3 - 三阶段架构
    
    阶段1 (L50 Chat API): 
      - 专注于分析报错堆栈
      - 识别关键报错行
      - 识别关键命名空间/模块
      - 列出涉及的模块和功能
    
    阶段2 (PM Agent API):
      - 接收阶段1的分析结果（简化版prompt）
      - 推荐最合适的指派人
      - 返回姓名和邮箱
    
    阶段3 (PM Agent API):
      - 验证推荐的指派人是否属于L50程序或CoreTech Team
      - 返回部门信息和验证结果
    """
    
    # 阶段1: 分析报错堆栈，专注于提取关键技术信息
    ANALYZE_ERROR_PROMPT = """你是一个专业的代码分析助手。请分析以下报错堆栈信息，完成以下任务：

## 任务要求
1. **找出关键报错行**: 从堆栈信息中识别出最关键的报错行，通常是项目代码中出错的位置（排除系统库、第三方库的行）
   - 包含文件路径和行号
   - 如果有多个关键行，列出前3个最重要的
   
2. **识别关键命名空间/模块**: 识别出关键的命名空间或模块名称
   - 例如：`LX6.Units.Module.Interact.ColliderLayerModule`
   - 例如：`CTT3.Weather.WeatherController`
   - 命名空间通常比单个文件行更能反映报错所属的功能模块
   
3. **列出涉及的模块**: 根据报错堆栈，列出所有可能涉及的功能模块
   - 例如：碰撞检测模块、天气系统、AI行为树等
   - 按重要性排序

4. **报错类型分类**: 判断报错的类型
   - NullReferenceException（空引用）
   - IndexOutOfRangeException（索引越界）
   - ArgumentException（参数异常）
   - 其他（请说明）

## 报错堆栈信息
```
{error_content}
```

## 输出格式要求
请严格按照以下JSON格式输出（不要输出其他内容）：
```json
{{
    "key_error_lines": [
        "关键报错行1（文件路径:行号）",
        "关键报错行2（文件路径:行号）"
    ],
    "key_namespace": "关键命名空间或模块名称",
    "involved_modules": [
        "涉及的模块1",
        "涉及的模块2"
    ],
    "error_type": "报错类型",
    "error_summary": "报错的简要描述（1-2句话）"
}}
```

## 重要提示
- 专注于技术分析，不要推荐人员
- 确保输出的是有效的JSON格式
- key_error_lines 至少包含1个，最多3个
- involved_modules 至少包含1个
"""

    # 阶段2: 使用PM Agent推荐候选人列表（极简版）
    RECOMMEND_CANDIDATES_PROMPT = """查询命名空间 {key_namespace} 和模块 {involved_modules} 的负责人或开发者，推荐1-3个最合适的人选。

输出JSON格式：
{{"candidate_assignees": [{{"name": "人名", "priority": 1, "reason": "理由"}}]}}"""

    # 阶段3: 验证指派人是否属于L50程序或CoreTech Team（简化版prompt，参考阶段2成功模式）
    VERIFY_ASSIGNEE_PROMPT = """搜索POPO用户"{assignee_name}"，验证其是否属于L50程序组或CoreTech Team，返回部门信息和邮箱。

输出JSON格式：
{{"is_verified": true/false, "verified_department": "部门名", "email": "邮箱", "verification_result": "验证结果说明"}}"""

    def __init__(self, tool=None):
        """
        初始化 AI 指派助手
        
        Args:
            tool: L18YiXieZuoTool 实例，如果为 None 则自动创建
        """
        self.tool = tool if tool else L18YiXieZuoTool()
        
        # 确保数据目录存在
        if not os.path.exists(AI_ASSIGN_DATA_DIR):
            os.makedirs(AI_ASSIGN_DATA_DIR)
    
    def _get_result_file_path(self, date_str=None):
        """
        获取AI指派结果文件路径
        
        Args:
            date_str: 日期字符串，格式 YYYY-MM-DD，默认为今天
            
        Returns:
            str: 文件路径
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(AI_ASSIGN_DATA_DIR, f"ai_assign_result_v3_{date_str}.json")
    
    def _save_results(self, results, date_str=None):
        """
        保存AI指派结果到JSON文件
        
        Args:
            results: 结果列表
            date_str: 日期字符串
        """
        file_path = self._get_result_file_path(date_str)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"[AIAssignHelperV3] AI指派结果已保存到 {file_path}")
        except Exception as e:
            print(f"[AIAssignHelperV3] 保存AI指派结果失败: {e}")
    
    def _load_results(self, date_str=None):
        """
        加载AI指派结果
        
        Args:
            date_str: 日期字符串
            
        Returns:
            list: 结果列表，如果文件不存在则返回空列表
        """
        file_path = self._get_result_file_path(date_str)
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[AIAssignHelperV3] 加载AI指派结果失败: {e}")
            return []
    
    def get_issues_by_assigned_user(self, assigned_to_id="2378", subject_filter="报错】", status_id="1"):
        """
        查询指派给特定用户的报错单
        
        Args:
            assigned_to_id: 指派人ID，默认为2378
            subject_filter: 标题过滤关键字，默认为"报错】"
            status_id: 状态ID，默认为1（新建）
            
        Returns:
            list: issue 列表
        """
        payload = {
            "c": ["id", "tracker_category", "tracker", "parent", "status", "priority", 
                  "subject", "assigned_to", "cf_30", "created_on", "cf_205", 
                  "description", "due_date", "closed_on"],
            "combination_filters": {
                "conditions": [
                    {
                        "filter_groups": [
                            {"assigned_to_id": {"operator": "=", "values": [assigned_to_id]}},
                            {"status_id": {"operator": "=", "values": [status_id]}}
                        ],
                        "filter_type": "filter",
                        "join_type": "and"
                    },
                    {
                        "filter_groups": [
                            {"subject": {"operator": "~", "values": [subject_filter]}}
                        ],
                        "filter_type": "filter_group",
                        "join_type": "or"
                    }
                ],
                "global_filters": {},
                "join_type": "and"
            },
            "custom_filters": {},
            "filter_mode": "combination",
            "filters": {},
            "page": 1,
            "set_filter": 1,
            "node_node_display": -1,
            "project_id": 50,
            "sort": "created_on:desc,sno:desc",
            "mode": "list"
        }
        
        print(f"[AIAssignHelperV3] 查询指派给 {assigned_to_id} 的报错单...")
        issues = self.tool.get_issues_v6_data(payload, 50)
        print(f"[AIAssignHelperV3] 查询完成，共找到 {len(issues)} 条 issue")
        return issues
    
    def get_issue_detail(self, issue_id):
        """
        获取单个issue的详细信息（包含完整的description）
        
        Args:
            issue_id: issue ID
            
        Returns:
            dict: issue详细信息
        """
        issue_info = self.tool.get_issue(issue_id)
        if issue_info and 'data' in issue_info:
            return issue_info['data'].get('res', {})
        return None
    
    def _extract_issue_content(self, issue):
        """
        提取issue的内容（报错堆栈信息）
        
        Args:
            issue: issue数据
            
        Returns:
            tuple: (subject, content)
        """
        # 提取标题
        subject = issue.get('subject', {})
        if isinstance(subject, dict):
            subject_value = subject.get('value', '')
        else:
            subject_value = str(subject)
        
        # 提取描述（报错内容）
        description = issue.get('description', '')
        if isinstance(description, dict):
            content = description.get('value', '')
        else:
            content = str(description) if description else ''
        
        # 过滤掉 pagedown 信息
        content = self._filter_pagedown_info(content)
        
        return subject_value, content
    
    def _filter_pagedown_info(self, content):
        """
        过滤掉content中的pagedown信息
        
        Args:
            content: 原始报错内容
            
        Returns:
            str: 过滤后的内容
        """
        if not content:
            return content
        
        # 查找 "======以下为pagedown信息======" 标记
        # 如果找到，直接截断后面的所有内容
        pagedown_delimiter = "======以下为pagedown信息======"
        if pagedown_delimiter in content:
            content = content.split(pagedown_delimiter)[0]
        
        # 常见的pagedown标记（作为备用过滤）
        pagedown_markers = [
            '<!-- Exported from Trello',
            '<!-- Exported from',
            '<!-- pagedown',
            '<!-- Page Down',
            '<!-- BEGIN PAGEDOWN',
            '<!-- END PAGEDOWN'
        ]
        
        lines = content.split('\n')
        filtered_lines = []
        skip_mode = False
        
        for line in lines:
            # 检查是否是pagedown开始标记
            if any(marker.lower() in line.lower() for marker in pagedown_markers):
                skip_mode = True
                continue
            
            # 检查是否是pagedown结束标记
            if skip_mode and '-->' in line:
                skip_mode = False
                continue
            
            # 非skip模式下保留行
            if not skip_mode:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def analyze_error_stage1(self, error_content, session_id=None):
        """
        阶段1: 使用L50 Chat API分析报错堆栈，提取关键技术信息
        
        Args:
            error_content: 报错堆栈内容
            session_id: AI会话ID，如果为None则自动生成
            
        Returns:
            dict: 分析结果
        """
        if session_id is None:
            session_id = f"ai_analyze_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 构建prompt
        prompt = self.ANALYZE_ERROR_PROMPT.format(
            error_content=error_content[:8000]  # 限制长度，避免token过多
        )
        
        print(f"[AIAssignHelperV3] 阶段1: 正在分析报错堆栈...")
        
        try:
            # 调用L50 API
            response = l50chat_completions_sync(
                query=prompt,
                session_id=session_id,
                show_think_flag=True,
                stream=True
            )
            
            # 保存AI原始输出和思考过程
            ai_raw_output = response.get("data", "")
            ai_think_process = response.get("think", "")
            
            # 尝试从响应中提取JSON
            ai_response_str = str(ai_raw_output)
            json_start = ai_response_str.find('{')
            json_end = ai_response_str.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = ai_response_str[json_start:json_end]
                try:
                    result = json.loads(json_str)
                    result["ai_raw_output_stage1"] = ai_response_str
                    result["ai_think_process_stage1"] = ai_think_process
                    return result
                except json.JSONDecodeError as e:
                    print(f"[AIAssignHelperV3] JSON解析失败: {e}")
            
            # 如果无法解析JSON，返回默认结果
            return {
                "key_error_lines": [],
                "key_namespace": "",
                "involved_modules": [],
                "error_type": "未知",
                "error_summary": "",
                "ai_raw_output_stage1": ai_response_str,
                "ai_think_process_stage1": ai_think_process,
                "parse_error": True
            }
            
        except Exception as e:
            print(f"[AIAssignHelperV3] 阶段1失败: {e}")
            return {
                "key_error_lines": [],
                "key_namespace": "",
                "involved_modules": [],
                "error_type": "未知",
                "error_summary": "",
                "error": str(e)
            }
    
    def recommend_candidates_stage2(self, stage1_result, session_id=None, timeout=120):
        """
        阶段2: 使用PM Agent推荐候选人列表（参考v2模式）
        
        Args:
            stage1_result: 阶段1的分析结果
            session_id: AI会话ID，如果为None则自动生成
            timeout: PM Agent超时时间（秒），默认120秒
            
        Returns:
            dict: 包含候选人列表的结果
        """
        if session_id is None:
            session_id = f"ai_recommend_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 构建prompt（简化版，不包含报错详情和报错行）
        involved_modules = ", ".join(stage1_result.get("involved_modules", []))
        
        prompt = self.RECOMMEND_CANDIDATES_PROMPT.format(
            error_type=stage1_result.get("error_type", "未知"),
            error_summary=stage1_result.get("error_summary", ""),
            key_namespace=stage1_result.get("key_namespace", ""),
            involved_modules=involved_modules
        )
        
        print(f"[AIAssignHelperV3] 阶段2: 正在推荐候选人列表 (简化版, timeout={timeout}秒)...")
        print(f"[AIAssignHelperV3] 阶段2输入长度: {len(prompt)} 字符")
        
        try:
            # 调用PM Agent API
            response = pm_agent_chat(
                message=prompt,
                user_id="ai_assign_helper",
                session_id=session_id,
                timeout=timeout
            )
            
            # 保存PM Agent原始输出
            pm_agent_thought = response.get("thought", "")
            pm_agent_answer = response.get("answer", "")
            is_completed = response.get("is_completed", False)
            is_error = response.get("is_error", False)
            
            print(f"[AIAssignHelperV3] 阶段2状态: is_completed={is_completed}, is_error={is_error}")
            print(f"[AIAssignHelperV3] 阶段2输出长度: thought={len(pm_agent_thought)}, answer={len(pm_agent_answer)}")
            
            if is_error:
                print(f"[AIAssignHelperV3] PM Agent返回错误: {pm_agent_answer}")
                return {
                    "candidate_assignees": [],
                    "pm_agent_thought": pm_agent_thought,
                    "pm_agent_answer": pm_agent_answer,
                    "pm_agent_raw_input": prompt,
                    "pm_agent_is_completed": is_completed,
                    "pm_agent_is_error": is_error,
                    "error": pm_agent_answer
                }
            
            # 尝试从响应中提取JSON (优先从answer, 然后从thought)
            # 先尝试从answer提取
            answer_str = str(pm_agent_answer)
            json_start = answer_str.find('{')
            json_end = answer_str.rfind('}') + 1
            
            result = None
            if json_start != -1 and json_end > json_start:
                json_str = answer_str[json_start:json_end]
                try:
                    result = json.loads(json_str)
                    print(f"[AIAssignHelperV3] ✓ 从answer成功解析JSON")
                except json.JSONDecodeError as e:
                    print(f"[AIAssignHelperV3] ✗ answer JSON解析失败: {e}")
            
            # 如果answer中未找到,尝试从thought提取
            if not result:
                print(f"[AIAssignHelperV3] 尝试从thought中提取JSON...")
                thought_str = str(pm_agent_thought)
                json_start = thought_str.find('{')
                json_end = thought_str.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = thought_str[json_start:json_end]
                    try:
                        result = json.loads(json_str)
                        print(f"[AIAssignHelperV3] ✓ 从thought成功解析JSON")
                    except json.JSONDecodeError as e:
                        print(f"[AIAssignHelperV3] ✗ thought JSON解析失败: {e}")
            
            # 成功解析到JSON
            if result:
                result["pm_agent_thought"] = pm_agent_thought
                result["pm_agent_answer"] = pm_agent_answer
                result["pm_agent_raw_input"] = prompt
                result["pm_agent_is_completed"] = is_completed
                result["pm_agent_is_error"] = is_error
                result["pm_agent_raw_events"] = response.get("raw_events", [])  # 保存原始事件流
                return result
            else:
                print(f"[AIAssignHelperV3] ✗ 未找到JSON格式的响应")
                print(f"[AIAssignHelperV3] Answer preview: {answer_str[:200]}...")
            
            # 如果无法解析JSON，返回默认结果
            return {
                "candidate_assignees": [],
                "pm_agent_thought": pm_agent_thought,
                "pm_agent_answer": pm_agent_answer,
                "pm_agent_raw_input": prompt,
                "pm_agent_is_completed": is_completed,
                "pm_agent_is_error": is_error,
                "pm_agent_raw_events": response.get("raw_events", []),  # 保存原始事件流
                "parse_error": True
            }
            
        except Exception as e:
            print(f"[AIAssignHelperV3] 阶段2异常: {e}")
            import traceback
            traceback.print_exc()
            return {
                "candidate_assignees": [],
                "pm_agent_raw_input": prompt if 'prompt' in locals() else "",
                "pm_agent_raw_events": [],
                "error": str(e)
            }
    
    def validate_single_candidate(self, candidate_name, session_id=None, timeout=120):
        """
        验证单个候选人是否属于L50程序或CoreTech Team
        
        Args:
            candidate_name: 候选人姓名
            session_id: AI会话ID
            timeout: PM Agent超时时间（秒）
            
        Returns:
            dict: 验证结果
        """
        if session_id is None:
            session_id = f"ai_verify_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 构建prompt (简化版，不需要邮箱)
        prompt = self.VERIFY_ASSIGNEE_PROMPT.format(
            assignee_name=candidate_name,
            assignee_email=""  # 邮箱由POPO搜索工具查询
        )
        
        print(f"[AIAssignHelperV3] 验证候选人 {candidate_name} (timeout={timeout}秒)...")
        
        try:
            # 调用PM Agent API
            response = pm_agent_chat(
                message=prompt,
                user_id="ai_assign_helper",
                session_id=session_id,
                timeout=timeout
            )
            
            # 保存PM Agent原始输出
            pm_agent_thought = response.get("thought", "")
            pm_agent_answer = response.get("answer", "")
            is_completed = response.get("is_completed", False)
            is_error = response.get("is_error", False)
            
            print(f"[AIAssignHelperV3] 验证状态: is_completed={is_completed}, is_error={is_error}")
            
            if is_error:
                print(f"[AIAssignHelperV3] PM Agent返回错误: {pm_agent_answer}")
                return {
                    "name": candidate_name,
                    "email": None,
                    "department": "",
                    "is_verified": False,
                    "verification_result": f"验证失败：PM Agent调用错误",
                    "pm_agent_thought": pm_agent_thought,
                    "pm_agent_answer": pm_agent_answer,
                    "pm_agent_raw_input": prompt,
                    "pm_agent_is_completed": is_completed,
                    "pm_agent_is_error": is_error
                }
            
            # 尝试从响应中提取JSON
            answer_str = str(pm_agent_answer)
            json_start = answer_str.find('{')
            json_end = answer_str.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = answer_str[json_start:json_end]
                try:
                    result = json.loads(json_str)
                    # 添加候选人姓名和调试信息
                    result["name"] = candidate_name
                    result["email"] = result.get("verified_department", "")  # 邮箱从验证结果提取
                    result["department"] = result.get("verified_department", "")
                    result["pm_agent_thought"] = pm_agent_thought
                    result["pm_agent_answer"] = pm_agent_answer
                    result["pm_agent_raw_input"] = prompt
                    result["pm_agent_is_completed"] = is_completed
                    result["pm_agent_is_error"] = is_error
                    print(f"[AIAssignHelperV3] ✓ 验证成功解析JSON")
                    return result
                except json.JSONDecodeError as e:
                    print(f"[AIAssignHelperV3] ✗ JSON解析失败: {e}")
            
            # 如果无法解析JSON，返回默认结果
            return {
                "name": candidate_name,
                "email": None,
                "department": "",
                "is_verified": False,
                "verification_result": "验证失败：PM Agent响应无法解析为JSON格式",
                "pm_agent_thought": pm_agent_thought,
                "pm_agent_answer": pm_agent_answer,
                "pm_agent_raw_input": prompt,
                "pm_agent_is_completed": is_completed,
                "pm_agent_is_error": is_error,
                "parse_error": True
            }
            
        except Exception as e:
            print(f"[AIAssignHelperV3] 验证异常: {e}")
            import traceback
            traceback.print_exc()
            return {
                "name": candidate_name,
                "email": None,
                "department": "",
                "is_verified": False,
                "verification_result": f"验证失败：PM Agent调用异常",
                "pm_agent_raw_input": prompt if 'prompt' in locals() else "",
                "pm_agent_raw_events": [],
                "error": str(e)
            }
    
    def cascade_validate_candidates_stage3(self, stage2_result, session_id=None, max_candidates=3):
        """
        阶段3: 级联验证候选人列表（参考v2模式）
        
        Args:
            stage2_result: 阶段2的候选人列表
            session_id: AI会话ID前缀
            max_candidates: 最多验证几个候选人
            
        Returns:
            dict: 包含验证结果和最终推荐人的字典
        """
        if session_id is None:
            session_id = f"ai_cascade_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        candidate_assignees = stage2_result.get("candidate_assignees", [])
        
        # 如果没有候选人，直接返回
        if not candidate_assignees:
            print(f"[AIAssignHelperV3] 阶段3: 阶段2未推荐任何候选人")
            return {
                "candidate_assignees": [],
                "validation_results": [],
                "recommended_assignee": "未知",
                "recommended_assignee_email": None,
                "verified_department": "",
                "confidence": "低",
                "reason": "阶段2未找到任何候选人"
            }
        
        print(f"[AIAssignHelperV3] 阶段3: 开始级联验证 {len(candidate_assignees)} 个候选人...")
        
        # 级联验证：逐个验证，找到第一个符合条件的
        validation_results = []
        recommended_candidate = None
        
        # 只验证前 max_candidates 个
        candidates_to_check = candidate_assignees[:max_candidates]
        
        for i, candidate in enumerate(candidates_to_check, 1):
            candidate_name = candidate.get("name", "")
            print(f"[AIAssignHelperV3] 验证候选人 {i}/{len(candidates_to_check)}: {candidate_name}")
            
            # 验证该候选人
            validation = self.validate_single_candidate(
                candidate_name, 
                f"{session_id}_validate_{i}"
            )
            
            validation_results.append({
                "candidate": candidate,
                "validation": validation
            })
            
            # 检查是否符合要求
            if validation.get("is_verified") and validation.get("verified_department"):
                print(f"[AIAssignHelperV3] ✓ 找到符合条件的候选人: {candidate_name}")
                recommended_candidate = {
                    "candidate": candidate,
                    "validation": validation
                }
                break
            else:
                print(f"[AIAssignHelperV3] ✗ 候选人 '{candidate_name}' 不符合要求")
        
        # 构建最终结果
        if recommended_candidate:
            candidate_info = recommended_candidate["candidate"]
            validation_info = recommended_candidate["validation"]
            
            return {
                "candidate_assignees": candidate_assignees,
                "validation_results": validation_results,
                "recommended_assignee": validation_info.get("name", ""),
                "recommended_assignee_email": validation_info.get("email"),
                "verified_department": validation_info.get("verified_department", ""),
                "is_verified": True,
                "confidence": "高" if candidate_info.get("priority", 3) == 1 else "中",
                "reason": f"【候选{candidate_info.get('priority')}】{candidate_info.get('reason', '')} 【验证通过】{validation_info.get('verification_result', '')}"
            }
        else:
            # 所有候选人都不符合要求
            return {
                "candidate_assignees": candidate_assignees,
                "validation_results": validation_results,
                "recommended_assignee": "未知",
                "recommended_assignee_email": None,
                "verified_department": "",
                "is_verified": False,
                "confidence": "低",
                "reason": f"找到 {len(candidate_assignees)} 个候选人，但验证后均不符合L50程序组/CoreTech Team要求"
            }
    
    def analyze_error_with_ai(self, issue_subject, error_content, session_id=None):
        """
        完整的三阶段分析流程
        
        Args:
            issue_subject: issue标题（不传给AI，仅用于记录）
            error_content: 报错堆栈内容
            session_id: AI会话ID，如果为None则自动生成
            
        Returns:
            dict: 完整的分析结果
        """
        if session_id is None:
            session_id = f"ai_assign_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 阶段1: 分析报错堆栈
        stage1_result = self.analyze_error_stage1(error_content, f"{session_id}_stage1")
        
        print(f"[AIAssignHelperV3] 阶段1完成:")
        print(f"  - 关键报错行: {stage1_result.get('key_error_lines', [])}")
        print(f"  - 关键命名空间: {stage1_result.get('key_namespace', '')}")
        print(f"  - 涉及模块: {stage1_result.get('involved_modules', [])}")
        print(f"  - 报错类型: {stage1_result.get('error_type', '')}")
        
        # 阶段2: 推荐候选人列表（简化版）
        stage2_result = self.recommend_candidates_stage2(stage1_result, f"{session_id}_stage2", timeout=300)
        
        candidates = stage2_result.get("candidate_assignees", [])
        print(f"[AIAssignHelperV3] 阶段2完成:")
        print(f"  - 找到候选人数量: {len(candidates)}")
        for i, candidate in enumerate(candidates[:3], 1):
            print(f"    [{i}] {candidate.get('name', '')} (priority={candidate.get('priority')})")
        
        # 阶段3: 级联验证候选人
        stage3_result = self.cascade_validate_candidates_stage3(stage2_result, f"{session_id}_stage3", max_candidates=3)
        
        print(f"[AIAssignHelperV3] 阶段3完成:")
        print(f"  - 验证结果: {stage3_result.get('verification_result', 'N/A')}")
        print(f"  - 最终推荐: {stage3_result.get('recommended_assignee', '未知')}")
        print(f"  - 验证通过: {stage3_result.get('is_verified', False)}")
        print(f"  - 验证后的部门: {stage3_result.get('verified_department', 'N/A')}")
        
        # 合并结果
        final_result = {
            # 阶段1结果
            "key_error_lines": stage1_result.get("key_error_lines", []),
            "key_namespace": stage1_result.get("key_namespace", ""),
            "involved_modules": stage1_result.get("involved_modules", []),
            "error_type": stage1_result.get("error_type", ""),
            "error_summary": stage1_result.get("error_summary", ""),
            
            # 阶段2结果 - 候选人列表
            "candidate_assignees": stage3_result.get("candidate_assignees", []),
            "validation_results": stage3_result.get("validation_results", []),
            
            # 阶段3结果 - 最终推荐
            "recommended_assignee": stage3_result.get("recommended_assignee", "未知"),
            "recommended_assignee_email": stage3_result.get("recommended_assignee_email"),
            "confidence": stage3_result.get("confidence", "低"),
            "reason": stage3_result.get("reason", ""),
            "knowledge_source": stage3_result.get("knowledge_source", ""),
            "candidate_score": stage3_result.get("candidate_score", 0),
            
            # 验证结果
            "is_verified": stage3_result.get("is_verified", False),
            "verified_department": stage3_result.get("verified_department", ""),
            
            # AI原始输出
            "ai_raw_output_stage1": stage1_result.get("ai_raw_output_stage1", ""),
            "ai_think_process_stage1": stage1_result.get("ai_think_process_stage1", ""),
            "pm_agent_thought_stage2": stage2_result.get("pm_agent_thought", ""),
            "pm_agent_answer_stage2": stage2_result.get("pm_agent_answer", ""),
            "pm_agent_raw_input_stage2": stage2_result.get("pm_agent_raw_input", ""),
            "pm_agent_raw_events_stage2": stage2_result.get("pm_agent_raw_events", [])  # 保存阶段2的原始SSE事件流
        }
        
        return final_result
    
    def process_issues_batch(self, issues, max_count=None, delay_seconds=2):
        """
        批量处理issues，使用AI分析并推荐指派人
        
        Args:
            issues: issue列表
            max_count: 最大处理数量，None表示处理全部
            delay_seconds: 每次AI调用之间的延迟秒数，避免请求过快
            
        Returns:
            list: 处理结果列表
        """
        results = []
        process_count = len(issues) if max_count is None else min(max_count, len(issues))
        
        print(f"[AIAssignHelperV3] 开始批量处理 {process_count} 个issues...")
        
        for i, issue in enumerate(issues[:process_count]):
            issue_id = issue.get('id')
            print(f"\n[AIAssignHelperV3] 处理 issue {i+1}/{process_count}, ID: {issue_id}")
            
            # 提取issue内容
            subject, content = self._extract_issue_content(issue)
            
            # 如果描述内容为空，尝试获取详细信息
            if not content:
                print(f"[AIAssignHelperV3] 描述为空，获取issue详细信息...")
                detail = self.get_issue_detail(issue_id)
                if detail:
                    content = detail.get('description', '')
            
            if not content:
                print(f"[AIAssignHelperV3] issue {issue_id} 无报错内容，跳过")
                results.append({
                    "issue_id": issue_id,
                    "subject": subject,
                    "status": "skipped",
                    "reason": "无报错内容",
                    "ai_result": None,
                    "current_assignee": issue.get('assigned_to', {}).get('value', '') if isinstance(issue.get('assigned_to'), dict) else str(issue.get('assigned_to', ''))
                })
                continue
            
            # 使用AI分析
            session_id = f"ai_assign_{issue_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            ai_result = self.analyze_error_with_ai(subject, content, session_id)
            
            # 获取当前指派人
            current_assignee = issue.get('assigned_to', {})
            if isinstance(current_assignee, dict):
                current_assignee_name = current_assignee.get('value', '')
            else:
                current_assignee_name = str(current_assignee)
            
            result = {
                "issue_id": issue_id,
                "issue_url": f"https://l18.pm.netease.com/v6/issues/{issue_id}",
                "subject": subject,
                "status": "processed",
                "current_assignee": current_assignee_name,
                "ai_result": ai_result,
                "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            results.append(result)
            
            # 打印结果摘要
            if ai_result:
                print(f"  - 关键报错行: {ai_result.get('key_error_lines', [])}")
                print(f"  - 关键命名空间: {ai_result.get('key_namespace', 'N/A')}")
                print(f"  - 涉及模块: {ai_result.get('involved_modules', [])}")
                print(f"  - 报错类型: {ai_result.get('error_type', 'N/A')}")
                print(f"  - 推荐指派人: {ai_result.get('recommended_assignee', '未知')}")
                print(f"  - 邮箱: {ai_result.get('recommended_assignee_email', 'N/A')}")
                print(f"  - 验证结果: {ai_result.get('verification_result', 'N/A')}")
                print(f"  - 验证后的部门: {ai_result.get('verified_department', 'N/A')}")
                print(f"  - 置信度: {ai_result.get('confidence', 'N/A')}")
                print(f"  - 理由: {ai_result.get('reason', 'N/A')[:100]}...")
            
            # 延迟，避免请求过快
            if i < process_count - 1:
                print(f"[AIAssignHelperV3] 等待 {delay_seconds} 秒...")
                time.sleep(delay_seconds)
        
        # 保存结果
        self._save_results(results)
        
        return results
    
    def run_ai_assign_analysis(self, assigned_to_id="2378", subject_filter="报错】", 
                                status_id="1", max_count=None):
        """
        运行AI指派分析的主入口
        
        Args:
            assigned_to_id: 当前指派人ID
            subject_filter: 标题过滤关键字
            status_id: 状态ID
            max_count: 最大处理数量
            
        Returns:
            list: 分析结果列表
        """
        print("=" * 60)
        print("[AIAssignHelperV3] 开始AI指派分析 (v3 - 三阶段架构)")
        print("=" * 60)
        
        # 1. 查询issues
        issues = self.get_issues_by_assigned_user(
            assigned_to_id=assigned_to_id,
            subject_filter=subject_filter,
            status_id=status_id
        )
        
        if not issues:
            print("[AIAssignHelperV3] 未找到符合条件的issue")
            return []
        
        # 2. 批量处理
        results = self.process_issues_batch(issues, max_count=max_count)
        
        # 3. 打印统计信息
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results):
        """
        打印结果统计摘要
        
        Args:
            results: 结果列表
        """
        print("\n" + "=" * 60)
        print("[AIAssignHelperV3] 分析结果统计")
        print("=" * 60)
        
        total = len(results)
        processed = len([r for r in results if r.get('status') == 'processed'])
        skipped = len([r for r in results if r.get('status') == 'skipped'])
        
        # 统计推荐指派人
        assignee_stats = {}
        confidence_stats = {"高": 0, "中": 0, "低": 0}
        
        for r in results:
            ai_result = r.get('ai_result')
            if ai_result:
                assignee = ai_result.get('recommended_assignee', '未知')
                assignee_stats[assignee] = assignee_stats.get(assignee, 0) + 1
                
                confidence = ai_result.get('confidence', '低')
                if confidence in confidence_stats:
                    confidence_stats[confidence] += 1
        
        print(f"总数: {total}")
        print(f"已处理: {processed}")
        print(f"已跳过: {skipped}")
        print(f"\n推荐指派人分布:")
        for assignee, count in sorted(assignee_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {assignee}: {count}")
        print(f"\n置信度分布:")
        for confidence, count in confidence_stats.items():
            print(f"  - {confidence}: {count}")


def generate_ai_assign_report(results):
    """
    生成AI指派分析报告
    
    Args:
        results: AI分析结果列表
        
    Returns:
        str: 报告文本
    """
    report = []
    report.append("=" * 70)
    report.append("AI 报错单指派分析报告 (v3 - 三阶段架构)")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 70)
    report.append("")
    
    for i, r in enumerate(results, 1):
        issue_id = r.get('issue_id')
        subject = r.get('subject', '')
        status = r.get('status', '')
        current_assignee = r.get('current_assignee', '')
        ai_result = r.get('ai_result')
        
        report.append(f"[{i}] Issue #{issue_id}")
        report.append(f"    标题: {subject[:60]}...")
        report.append(f"    当前指派人: {current_assignee}")
        
        if status == 'skipped':
            report.append(f"    状态: 已跳过 - {r.get('reason', '')}")
        elif ai_result:
            report.append(f"    AI分析结果:")
            report.append(f"      阶段1 - 报错分析:")
            report.append(f"        - 关键报错行: {ai_result.get('key_error_lines', [])}")
            report.append(f"        - 关键命名空间: {ai_result.get('key_namespace', 'N/A')}")
            report.append(f"        - 涉及模块: {ai_result.get('involved_modules', [])}")
            report.append(f"        - 报错类型: {ai_result.get('error_type', 'N/A')}")
            report.append(f"        - 报错摘要: {ai_result.get('error_summary', 'N/A')}")
            report.append(f"      阶段2 - 指派人推荐:")
            report.append(f"        - 推荐指派人: {ai_result.get('recommended_assignee', '未知')}")
            report.append(f"        - 推荐邮箱: {ai_result.get('recommended_assignee_email', 'N/A')}")
            report.append(f"        - 置信度: {ai_result.get('confidence', 'N/A')}")
            report.append(f"        - 知识来源: {ai_result.get('knowledge_source', 'N/A')}")
            report.append(f"        - 推荐理由: {ai_result.get('reason', 'N/A')}")
            report.append(f"      阶段3 - 指派人验证:")
            report.append(f"        - 验证结果: {ai_result.get('verification_result', 'N/A')}")
            report.append(f"        - 验证通过: {ai_result.get('is_verified', False)}")
            report.append(f"        - 验证后的部门: {ai_result.get('verified_department', 'N/A')}")
        
        report.append("-" * 70)
    
    return "\n".join(report)


# 测试代码 - 交互式对话
if __name__ == "__main__":
    import uuid
    
    print("=" * 60)
    print("L50 Chat 交互式对话测试")
    print("=" * 60)
    print("输入 'exit' 或 'quit' 退出对话")
    print("输入 'clear' 清除会话历史（新建session）")
    print("输入 'think on' 开启思考过程显示")
    print("输入 'think off' 关闭思考过程显示")
    print("=" * 60)
    
    # 生成唯一会话ID
    session_id = f"chat_{uuid.uuid4().hex[:8]}"
    show_think = False
    
    print(f"[系统] 会话ID: {session_id}")
    print(f"[系统] 思考过程显示: {'开启' if show_think else '关闭'}")
    print("-" * 60)
    
    while True:
        try:
            # 获取用户输入
            user_input = input("\n你: ").strip()
            
            # 处理特殊命令
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', '退出']:
                print("[系统] 再见！")
                break
            
            if user_input.lower() == 'clear':
                session_id = f"chat_{uuid.uuid4().hex[:8]}"
                print(f"[系统] 已清除会话历史，新会话ID: {session_id}")
                continue
            
            if user_input.lower() == 'think on':
                show_think = True
                print("[系统] 已开启思考过程显示")
                continue
            
            if user_input.lower() == 'think off':
                show_think = False
                print("[系统] 已关闭思考过程显示")
                continue
            
            # 调用L50 Chat API（流式输出）
            print("\nAI: ", end="", flush=True)
            
            think_buffer = ""
            data_buffer = ""
            
            for response_type, content in l50chat_completions(
                query=user_input,
                session_id=session_id,
                show_think_flag=show_think,
                stream=True
            ):
                if response_type == "think":
                    if show_think:
                        think_buffer += str(content)
                        # 实时打印思考内容（灰色）
                        print(f"\033[90m{content}\033[0m", end="", flush=True)
                
                elif response_type == "data":
                    if isinstance(content, dict):
                        # 流式响应中的内容块
                        chunk = content.get('content', '')
                        if chunk:
                            data_buffer += chunk
                            print(chunk, end="", flush=True)
                    elif content == "[DONE]":
                        # 流式结束
                        pass
                    else:
                        print(str(content), end="", flush=True)
                
                elif response_type == "raw":
                    # 其他原始内容
                    if content.strip():
                        print(f"\n[RAW] {content}")
            
            # 换行
            print()
            
        except KeyboardInterrupt:
            print("\n[系统] 检测到中断，再见！")
            break
        except Exception as e:
            print(f"\n[错误] {e}")
            import traceback
            traceback.print_exc()
