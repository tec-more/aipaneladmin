from __future__ import annotations
import importlib
import pkgutil
from fastapi import FastAPI , APIRouter
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable, Any
from functools import wraps
from typing import List, Optional
from base.common.log import log

def auto_discover_routers(
    app: FastAPI,
    base_package: str,
    router_variable_name: str = "router",
    skip_modules: Optional[List[str]] = None
) -> None:
    """
    自动发现并注册 FastAPI 路由
    
    Args:
        app: FastAPI 应用实例
        base_package: 要扫描的基础包名（如 "base.core.users.api.v1"）
        router_variable_name: 路由实例的变量名（默认为 "router"）
        skip_modules: 要跳过的模块名列表
    """
    if skip_modules is None:
        skip_modules = ["__pycache__","middleware", "models", "schemas", "tests"]
    
    try:
        base_module = importlib.import_module(base_package)
    except ImportError as e:
        print(f"❌ 无法导入基础包 {base_package}: {e}")
        return
    
    # 获取包的路径
    if not hasattr(base_module, "__path__"):
        print(f"❌ {base_package} 不是一个有效的包")
        return
    
    package_path = base_module.__path__[0]
    print(f"🔍 扫描包路径: {package_path}")
    
    routers_found = 0
    
    # 遍历包中的所有模块
    for finder, name, ispkg in pkgutil.iter_modules([package_path]):
        full_name = f"{base_package}.{name}"
        
        # 跳过指定的模块
        if any(skip in name for skip in skip_modules):
            continue
            
        try:
            module = importlib.import_module(full_name)
            
            # 查找路由实例
            router_instance = getattr(module, router_variable_name, None)
            
            if isinstance(router_instance, APIRouter):
                # 注册路由到主应用
                app.include_router(router_instance)
                routers_found += 1
                print(f"✅ 已注册路由: {full_name} -> {router_instance.prefix or '/'}")
            
            # 如果是包，递归扫描（支持子目录）
            if ispkg:
                num = _discover_in_subpackage(app, full_name, router_variable_name, routers_found,skip_modules)
                routers_found += num if num else 0
        except ImportError as e:
            print(f"⚠️ 导入模块失败 {full_name}: {e}")
        except Exception as e:
            print(f"❌ 处理模块 {full_name} 时出错: {e}")
    
    print(f"🎯 路由自动发现完成，共注册 {routers_found} 个路由")

def _discover_in_subpackage(app: FastAPI, package_name: str, router_var: str, routers_found: int, skip_modules: List[str]):
    """递归发现子包中的路由"""
    try:
        sub_module = importlib.import_module(package_name)
        
        if not hasattr(sub_module, "__path__"):
            return
            
        for finder, name, ispkg in pkgutil.iter_modules(sub_module.__path__):
            full_name = f"{package_name}.{name}"
            
            if any(skip in name for skip in skip_modules):
                continue
                
            try:
                module = importlib.import_module(full_name)
                router_instance = getattr(module, router_var, None)
                
                if isinstance(router_instance, APIRouter):
                    app.include_router(router_instance)
                    routers_found += 1
                    print(f"✅ 已注册子包路由: {full_name}")
                
                # 继续递归
                if ispkg:
                    num = _discover_in_subpackage(app, full_name, router_var,routers_found, skip_modules)
                    routers_found += num if num else 0
                    
            except ImportError as e:
                print(f"⚠️ 导入子模块失败 {full_name}: {e}")
        return routers_found   
    except ImportError:
        return

def register_routers(app: FastAPI):
    # 自动注册 core 和 plugins 目录下的所有路由
    auto_discover_routers(app, base_package="base.core")
    auto_discover_routers(app, base_package="base.plugins")