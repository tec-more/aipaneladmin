"""
ReAct 智能体执行服务
"""
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from base.plugins.agent.skills.registry import SkillRegistry

class ReActAgentService:
    """
    ReAct 智能体执行服务
    """
    
    @staticmethod
    def create_react_agent(skill_type: str, model_name: str = "gpt-3.5-turbo") -> CompiledStateGraph:
        """
        创建 ReAct 智能体
        
        Args:
            skill_type: 技能类型
            model_name: 大模型名称
            
        Returns:
            编译后的状态图
        """
        # 定义状态
        class State:
            input_text: str
            result: str
            error: str
            thoughts: List[str]
            actions: List[str]
            observations: List[str]
        
        # ReAct 提示词模板
        react_prompt = ChatPromptTemplate.from_template("""
        你是一个智能助手，使用 ReAct 模式来解决问题。
        
        请按照以下步骤处理用户的请求：
        1. 分析用户输入
        2. 思考如何解决问题
        3. 执行相应的操作
        4. 观察操作结果
        5. 总结最终答案
        
        输入：{input_text}
        
        思考历史：
        {thoughts}
        
        操作历史：
        {actions}
        
        观察历史：
        {observations}
        
        请输出你的思考，然后执行相应的操作。
        """)
        
        # 思考节点
        def think(state: Dict[str, Any]) -> Dict[str, Any]:
            try:
                input_text = state.get("input_text", "")
                thoughts = state.get("thoughts", [])
                
                # 创建模型
                model = ChatOpenAI(model=model_name)
                
                # 构建链
                chain = react_prompt | model
                
                # 执行思考
                result = chain.invoke({
                    "input_text": input_text,
                    "thoughts": "\n".join(thoughts),
                    "actions": "\n".join(state.get("actions", [])),
                    "observations": "\n".join(state.get("observations", []))
                })
                
                new_thought = result.content
                thoughts.append(new_thought)
                
                return {
                    "thoughts": thoughts
                }
            except Exception as e:
                return {
                    "error": f"思考过程失败: {str(e)}"
                }
        
        # 行动节点
        def act(state: Dict[str, Any]) -> Dict[str, Any]:
            try:
                input_text = state.get("input_text", "")
                actions = state.get("actions", [])
                
                # 获取技能类
                skill_class = SkillRegistry.get_skill(skill_type)
                if not skill_class:
                    return {
                        "error": f"技能类型 {skill_type} 未注册"
                    }
                
                # 执行技能
                result = skill_class.execute({"input_text": input_text})
                
                action = f"执行 {skill_type} 技能: {input_text}"
                actions.append(action)
                
                return {
                    "actions": actions,
                    "result": result.get("translation" if skill_type == "slang_translation" else "result", "") if result.get("success") else ""
                }
            except Exception as e:
                return {
                    "error": f"执行操作失败: {str(e)}"
                }
        
        # 观察节点
        def observe(state: Dict[str, Any]) -> Dict[str, Any]:
            try:
                result = state.get("result", "")
                observations = state.get("observations", [])
                
                # 观察执行结果
                observation = f"执行结果: {result}"
                observations.append(observation)
                
                return {
                    "observations": observations
                }
            except Exception as e:
                return {
                    "error": f"观察过程失败: {str(e)}"
                }
        
        # 总结节点
        def summarize(state: Dict[str, Any]) -> Dict[str, Any]:
            try:
                result = state.get("result", "")
                thoughts = state.get("thoughts", [])
                
                if not result:
                    return {
                        "error": "执行失败"
                    }
                
                return {
                    "result": result
                }
            except Exception as e:
                return {
                    "error": f"总结过程失败: {str(e)}"
                }
        
        # 创建状态图
        workflow = StateGraph(State)
        
        # 添加节点
        workflow.add_node("think", think)
        workflow.add_node("act", act)
        workflow.add_node("observe", observe)
        workflow.add_node("summarize", summarize)
        
        # 设置入口点
        workflow.set_entry_point("think")
        
        # 添加边
        workflow.add_edge("think", "act")
        workflow.add_edge("act", "observe")
        workflow.add_edge("observe", "summarize")
        workflow.add_edge("summarize", END)
        
        # 编译状态图
        return workflow.compile()
    
    @staticmethod
    async def execute_react_agent(skill_type: str, input_text: str, model_name: str = "gpt-3.5-turbo") -> Dict[str, Any]:
        """
        执行 ReAct 智能体
        
        Args:
            skill_type: 技能类型
            input_text: 输入文本
            model_name: 大模型名称
            
        Returns:
            执行结果
        """
        try:
            # 创建智能体
            agent = ReActAgentService.create_react_agent(skill_type, model_name)
            
            # 执行智能体
            result = await agent.ainvoke({
                "input_text": input_text,
                "thoughts": [],
                "actions": [],
                "observations": []
            })
            
            if result.get("error"):
                return {
                    "success": False,
                    "message": result.get("error")
                }
            else:
                return {
                    "success": True,
                    "result": result.get("result", "")
                }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
