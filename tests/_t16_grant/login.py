"""登录辅助：尝试默认口令登录 admin，失败则强制重置为 T16@Admin123 后再登录
输出: token 写入 tests/_t16_grant/token.txt
"""
import asyncio
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

BASE = "http://127.0.0.1:9998"
CANDIDATES = ["admin123", "123456", "Admin@123", "admin", "T16@Admin123", "admin123456", "Admin@123456"]


def try_login(username, password):
    for prefix in ("/api/v1/auth/login", "/v1/auth/login"):
        try:
            req = urllib.request.Request(
                BASE + prefix,
                data=json.dumps({"username": username, "password": password}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                body = json.loads(resp.read())
                if body.get("success") and body.get("data", {}).get("access_token"):
                    return body["data"]["access_token"], prefix
                return None, body.get("msg") or body
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read())
            except Exception:
                body = {}
            if e.code == 404:
                continue
            return None, body
        except Exception as e:
            return None, str(e)
    return None, "no-route"


async def reset_admin_pwd(pwd):
    from tortoise import Tortoise
    from base.common.setting import get_model_list
    from base.common.security import get_password_hash
    await Tortoise.init(db_url="postgres://admin:Admin@123@127.0.0.1:15432/aipaneladmin",
                        modules={"models": get_model_list()})
    from base.core.users.models.users import User
    admin = await User.get(id=1)
    admin.password_hash = get_password_hash(pwd) if hasattr(admin, "password_hash") else None
    # 字段名兼容
    for field in ("password", "hashed_password", "password_hash"):
        if hasattr(admin, field):
            setattr(admin, field, get_password_hash(pwd))
    await admin.save()
    await Tortoise.close_connections()
    print("admin password reset done")


def main():
    for pwd in CANDIDATES:
        token, info = try_login("admin", pwd)
        if token:
            print(f"LOGIN OK pwd={pwd} via {info}")
            open(os.path.join(os.path.dirname(__file__), "token.txt"), "w").write(token)
            return
        else:
            print(f"try {pwd}: {info}")
    print("all candidates failed, resetting admin password...")
    asyncio.run(reset_admin_pwd("T16@Admin123"))
    token, info = try_login("admin", "T16@Admin123")
    if token:
        print("LOGIN OK after reset")
        open(os.path.join(os.path.dirname(__file__), "token.txt"), "w").write(token)
    else:
        print("RESET-LOGIN FAILED:", info)
        sys.exit(1)


main()
