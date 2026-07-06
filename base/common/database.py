import shutil
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise.expressions import Q

from base.common.setting import settings, TORTOISE_ORM


def _patch_asyncpg_for_gaussdb():
    try:
        import asyncpg
        _original_reset = asyncpg.connection.Connection.reset

        async def _patched_reset(self, *, timeout=None):
            try:
                await _original_reset(self, timeout=timeout)
            except Exception:
                try:
                    await self.execute("ROLLBACK")
                except Exception:
                    pass

        asyncpg.connection.Connection.reset = _patched_reset
        print("[DB] asyncpg reset补丁已应用(GaussDB兼容)")
    except Exception as e:
        print(f"[DB] asyncpg补丁应用失败: {e}")


_patch_asyncpg_for_gaussdb()


def _split_sql_statements(sql: str) -> "list[str]":
    """按顶层分号切分 SQL，忽略 $$...$$ 美元引号块内的分号（asyncpg.execute 仅支持单条语句）。"""
    statements: "list[str]" = []
    buf: "list[str]" = []
    in_dollar = False
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        if ch == "$" and sql[i:i + 2] == "$$":
            in_dollar = not in_dollar
            buf.append("$$")
            i += 2
            continue
        if not in_dollar and ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


async def _run_sql_migrations() -> None:
    """执行 migrations/*.sql 幂等迁移（补齐 action 等列及默认数据）。

    这些 SQL 为 CREATE TABLE IF NOT EXISTS / ALTER ... IF NOT EXISTS / INSERT ... WHERE NOT EXISTS，
    可重复执行且对全新库与存量库均安全。需在 Tortoise.generate_schemas 之前执行，
    以确保 approval_instance.action 等列已存在。
    """
    from base.common.setting import settings

    migrations_dir = Path(__file__).resolve().parent.parent.parent / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))
    if not sql_files:
        print("未找到 migrations/*.sql，跳过自定义 SQL 迁移")
        return

    import asyncpg

    conn = await asyncpg.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
    )
    try:
        for sql_file in sql_files:
            sql = sql_file.read_text(encoding="utf-8")
            print(f"执行 SQL 迁移: {sql_file.name}")
            for stmt in _split_sql_statements(sql):
                await conn.execute(stmt)
        print("自定义 SQL 迁移执行完成")
    finally:
        await conn.close()


async def init_db():
    print("开始初始化数据库...")
    print(f"模型列表: {TORTOISE_ORM['apps']['models']['models']}")
    
    try:
        from aerich import Command
        command = Command(tortoise_config=TORTOISE_ORM)
        
        try:
            print("初始化aerich...")
            await command.init()
            print("aerich初始化完成")
        except Exception as e:
            print(f"初始化aerich时出错: {e}")
            import traceback
            traceback.print_exc()

        try:
            print("执行数据库迁移...")
            await command.upgrade(run_in_transaction=True)
            print("数据库迁移完成")
        except Exception as e:
            print(f"执行数据库迁移时出错: {e}")
            print("继续执行，可能是因为迁移已应用...")
            import traceback
            traceback.print_exc()

        # 执行自定义 SQL 迁移（补齐 action 等列及默认数据），需在 generate_schemas 之前
        try:
            await _run_sql_migrations()
        except Exception as e:
            print(f"执行自定义 SQL 迁移时出错（已忽略）: {e}")
            import traceback
            traceback.print_exc()

    except ImportError:
        print("aerich 未安装，跳过迁移")
    except Exception as e:
        print(f"数据库初始化流程出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("数据库初始化流程完成")
    
async def init_data():
    await init_db()
    
    from tortoise import Tortoise
    print("初始化 Tortoise ORM...")
    try:
        await Tortoise.init(config=TORTOISE_ORM)
        print("Tortoise ORM 初始化完成")
        
        import os
        is_main_worker = os.environ.get("UVICORN_WORKER_ID") is None
        if is_main_worker:
            print("生成数据库表（主进程）...")
            try:
                await Tortoise.generate_schemas(safe=True)
                print("数据库表生成完成")
            except Exception as schema_err:
                print(f"数据库表生成部分失败: {schema_err}")
                print("尝试逐表创建缺失的表...")
                try:
                    import asyncpg as _asyncpg
                    _raw_conn = await _asyncpg.connect(
                        host=settings.db_host, port=settings.db_port,
                        user=settings.db_user, password=settings.db_password,
                        database=settings.db_name
                    )
                    from tortoise.backends.asyncpg.schema_generator import AsyncpgSchemaGenerator
                    _conn = Tortoise.get_connection('postgres')
                    _generator = AsyncpgSchemaGenerator(_conn)
                    for _app_name, _app in Tortoise.apps.items():
                        for _model_name, _model in _app.items():
                            _tbl = _model._meta.db_table
                            try:
                                _exists = await _raw_conn.fetchval(
                                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=$1)",
                                    _tbl
                                )
                                if not _exists:
                                    _table_sql = _generator._get_table_sql(_model, True)
                                    # 正确处理 _get_table_sql 的返回值
                                    # 返回值可能是：dict（包含 table_creation_string）、tuple、或 str
                                    if isinstance(_table_sql, dict):
                                        _create_sql = _table_sql.get('table_creation_string', '')
                                    elif isinstance(_table_sql, tuple):
                                        _create_sql = _table_sql[0]
                                    else:
                                        _create_sql = str(_table_sql)
                                    
                                    try:
                                        await _raw_conn.execute(_create_sql)
                                        print(f"  创建表: {_tbl}")
                                    except Exception as exec_err:
                                        print(f"  创建表 {_tbl} 失败: {exec_err}")
                                        print(f"  SQL: {_create_sql[:300]}")
                                        raise
                            except Exception as e:
                                print(f"  跳过表 {_tbl}: {str(e)[:80]}")
                    await _raw_conn.close()
                except Exception as e2:
                    print(f"逐表创建也失败: {e2}")
                print("数据库表处理完成")
        else:
            worker_id = os.environ.get("UVICORN_WORKER_ID", "unknown")
            print(f"跳过数据库表生成（worker {worker_id}，由主进程已完成）")
        
    except Exception as e:
        print(f"初始化 Tortoise ORM 时出错: {e}")
        import traceback
        traceback.print_exc()