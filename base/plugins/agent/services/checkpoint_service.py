# base/plugins/agent/services/checkpoint_service.py
import logging
import uuid
from typing import Optional, List, Dict, Any, Union

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver

logger = logging.getLogger(__name__)


class CheckpointService:
    """检查点服务 - 管理 LangGraph 检查点的存储、恢复和查询"""
    
    _instance = None
    _checkpointer: Optional[BaseCheckpointSaver] = None
    _use_postgres: bool = False
    
    @classmethod
    def get_instance(cls, use_postgres: bool = False) -> 'CheckpointService':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls(use_postgres=use_postgres)
        return cls._instance
    
    def __init__(self, use_postgres: bool = False):
        """初始化检查点服务"""
        self._use_postgres = use_postgres
        
        if use_postgres:
            try:
                from langgraph.checkpoint.postgres import PostgresSaver
                import psycopg
                from base.common.setting import settings
                
                db_config = settings.TORTOISE_ORM['connections']['postgres']['credentials']
                conn_string = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
                
                self._checkpointer = PostgresSaver.from_conn_string(conn_string)
                logger.info("检查点服务初始化完成，使用PostgreSQL存储")
            except ImportError as e:
                logger.warning(f"无法导入PostgreSQL依赖，降级到内存存储: {e}")
                self._checkpointer = MemorySaver()
                self._use_postgres = False
            except Exception as e:
                logger.error(f"PostgreSQL检查点初始化失败，降级到内存存储: {e}")
                self._checkpointer = MemorySaver()
                self._use_postgres = False
        else:
            self._checkpointer = MemorySaver()
            logger.info("检查点服务初始化完成，使用内存存储（重启后会丢失）")
    
    @classmethod
    def reset_instance(cls):
        """重置单例实例（用于测试或切换存储后端）"""
        cls._instance = None
    
    def create_thread_id(self, user_id: str, session_id: Optional[str] = None) -> str:
        """
        创建线程ID
        :param user_id: 用户ID
        :param session_id: 会话ID（可选，不提供则自动生成）
        :return: thread_id 格式: user_id:session_id
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        return f"{user_id}:{session_id}"
    
    def get_checkpointer(self) -> BaseCheckpointSaver:
        """获取检查点存储实例"""
        return self._checkpointer
    
    def get_user_checkpoints(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户的所有检查点
        :param user_id: 用户ID
        :return: 检查点列表
        """
        try:
            all_checkpoints = list(self._checkpointer.list_checkpoints({}))
            user_checkpoints = []
            
            for cp in all_checkpoints:
                cp_thread_id = cp.get("configurable", {}).get("thread_id", "")
                if cp_thread_id.startswith(f"{user_id}:"):
                    session_id = cp_thread_id.split(":", 1)[1] if ":" in cp_thread_id else ""
                    
                    user_checkpoints.append({
                        "checkpoint_id": cp.get("checkpoint_id", ""),
                        "thread_id": cp_thread_id,
                        "session_id": session_id,
                        "user_id": user_id,
                        "metadata": cp.get("metadata", {}),
                        "created_at": cp.get("created_at"),
                        "state_summary": {
                            "node_results": len(cp.get("state", {}).get("node_results", {})),
                            "execution_trace": len(cp.get("state", {}).get("execution_trace", []))
                        }
                    })
            
            user_checkpoints.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return user_checkpoints
        
        except Exception as e:
            logger.error(f"获取用户检查点失败: {e}")
            return []
    
    def get_session_checkpoints(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """
        获取用户特定会话的检查点
        :param user_id: 用户ID
        :param session_id: 会话ID
        :return: 检查点列表
        """
        thread_id = self.create_thread_id(user_id, session_id)
        
        try:
            checkpoints = list(self._checkpointer.list_checkpoints(
                {"configurable": {"thread_id": thread_id}}
            ))
            
            return [{
                "checkpoint_id": cp.get("checkpoint_id", ""),
                "thread_id": thread_id,
                "session_id": session_id,
                "user_id": user_id,
                "metadata": cp.get("metadata", {}),
                "created_at": cp.get("created_at"),
                "parent_checkpoint_id": cp.get("parent_checkpoint_id")
            } for cp in checkpoints]
        
        except Exception as e:
            logger.error(f"获取会话检查点失败: {e}")
            return []
    
    def get_checkpoint(self, user_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个检查点详情
        :param user_id: 用户ID
        :param checkpoint_id: 检查点ID
        :return: 检查点详情
        """
        try:
            all_checkpoints = list(self._checkpointer.list_checkpoints({}))
            
            for cp in all_checkpoints:
                if cp.get("checkpoint_id") == checkpoint_id:
                    cp_thread_id = cp.get("configurable", {}).get("thread_id", "")
                    if cp_thread_id.startswith(f"{user_id}:"):
                        return {
                            "checkpoint_id": cp.get("checkpoint_id", ""),
                            "thread_id": cp_thread_id,
                            "user_id": user_id,
                            "session_id": cp_thread_id.split(":", 1)[1] if ":" in cp_thread_id else "",
                            "metadata": cp.get("metadata", {}),
                            "state": cp.get("state", {}),
                            "created_at": cp.get("created_at"),
                            "parent_checkpoint_id": cp.get("parent_checkpoint_id")
                        }
            
            return None
        
        except Exception as e:
            logger.error(f"获取检查点详情失败: {e}")
            return None
    
    def delete_checkpoint(self, user_id: str, checkpoint_id: str) -> bool:
        """
        删除检查点
        :param user_id: 用户ID
        :param checkpoint_id: 检查点ID
        :return: 是否删除成功
        """
        try:
            checkpoint = self.get_checkpoint(user_id, checkpoint_id)
            if not checkpoint:
                logger.warning(f"检查点不存在: {checkpoint_id}")
                return False
            
            self._checkpointer.delete_checkpoint({
                "configurable": {
                    "thread_id": checkpoint["thread_id"],
                    "checkpoint_id": checkpoint_id
                }
            })
            logger.info(f"检查点已删除: {checkpoint_id}")
            return True
        
        except Exception as e:
            logger.error(f"删除检查点失败: {e}")
            return False
    
    def delete_session_checkpoints(self, user_id: str, session_id: str) -> bool:
        """
        删除会话的所有检查点
        :param user_id: 用户ID
        :param session_id: 会话ID
        :return: 是否删除成功
        """
        try:
            thread_id = self.create_thread_id(user_id, session_id)
            self._checkpointer.delete_checkpoint({"configurable": {"thread_id": thread_id}})
            logger.info(f"会话检查点已删除: {thread_id}")
            return True
        
        except Exception as e:
            logger.error(f"删除会话检查点失败: {e}")
            return False
    
    def delete_user_checkpoints(self, user_id: str) -> bool:
        """
        删除用户的所有检查点
        :param user_id: 用户ID
        :return: 是否删除成功
        """
        try:
            checkpoints = self.get_user_checkpoints(user_id)
            for cp in checkpoints:
                self._checkpointer.delete_checkpoint({
                    "configurable": {
                        "thread_id": cp["thread_id"],
                        "checkpoint_id": cp["checkpoint_id"]
                    }
                })
            logger.info(f"用户所有检查点已删除: {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"删除用户检查点失败: {e}")
            return False
    
    def build_config(self, user_id: str, session_id: Optional[str] = None, 
                     checkpoint_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        构建执行配置
        :param user_id: 用户ID
        :param session_id: 会话ID（可选）
        :param checkpoint_id: 检查点ID（可选，用于恢复）
        :param kwargs: 额外的元数据
        :return: 配置字典
        """
        thread_id = self.create_thread_id(user_id, session_id)
        
        config: Dict[str, Any] = {
            "configurable": {"thread_id": thread_id}
        }
        
        if checkpoint_id:
            config["configurable"]["checkpoint_id"] = checkpoint_id
        
        metadata = {
            "user_id": user_id,
            "session_id": thread_id.split(":", 1)[1] if ":" in thread_id else "",
            **kwargs
        }
        config["metadata"] = metadata
        
        return config