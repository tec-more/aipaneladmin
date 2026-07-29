"""
文档管理模块 API 测试脚本
测试 document 插件的全部 API 接口
"""
import requests
import json
import time
import os
import tempfile
from datetime import datetime

BASE_URL = "http://127.0.0.1:9998"
API_PREFIX = "/api"  # 如果有网关代理，使用 /api；否则留空
DOCUMENT_BASE = f"{API_PREFIX}/v1/document" if API_PREFIX else "/v1/document"
TEST_RESULTS = []

def log_result(test_id, test_name, status, message=""):
    result = {
        "test_id": test_id,
        "test_name": test_name,
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    TEST_RESULTS.append(result)
    status_icon = "✅" if status == "PASS" else "❌"
    print(f"{status_icon} {test_id}: {test_name} - {status}")
    if message:
        print(f"   {message}")

def login():
    print("\n" + "=" * 60)
    print("登录系统")
    print("=" * 60)
    data = {"username": "admin", "password": "admin123"}
    try:
        response = requests.post(f"{BASE_URL}/v1/auth/login", json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"登录成功")
            return result['data']['access_token']
        else:
            log_result("TC-AUTH-001", "系统登录", "FAIL", f"登录失败: {response.text}")
            return None
    except Exception as e:
        log_result("TC-AUTH-001", "系统登录", "FAIL", f"登录异常: {str(e)}")
        return None

def test_category_crud(token):
    """测试分类管理 CRUD"""
    print("\n" + "=" * 60)
    print("文档分类 CRUD 测试")
    print("=" * 60)
    headers = {"Authorization": f"Bearer {token}"}
    created_ids = []

    # TC-CAT-001: 创建根分类
    try:
        resp = requests.post(f"{BASE_URL}/v1/document/categories", headers=headers, json={
            "name": "测试分类",
            "sort": 1,
            "is_active": True
        })
        result = resp.json()
        if result.get("code") == 0:
            cat_id = result['data']['id']
            created_ids.append(cat_id)
            log_result("TC-CAT-001", "创建根分类", "PASS", f"分类ID: {cat_id}")
        else:
            log_result("TC-CAT-001", "创建根分类", "FAIL", result.get("msg", "未知错误"))
    except Exception as e:
        log_result("TC-CAT-001", "创建根分类", "FAIL", str(e))

    # TC-CAT-002: 创建子分类
    if created_ids:
        try:
            resp = requests.post(f"{BASE_URL}/v1/document/categories", headers=headers, json={
                "name": "测试子分类",
                "parent_id": created_ids[0],
                "sort": 1,
                "is_active": True
            })
            result = resp.json()
            if result.get("code") == 0:
                sub_id = result['data']['id']
                created_ids.append(sub_id)
                log_result("TC-CAT-002", "创建子分类", "PASS", f"分类ID: {sub_id}")
            else:
                log_result("TC-CAT-002", "创建子分类", "FAIL", result.get("msg", "未知错误"))
        except Exception as e:
            log_result("TC-CAT-002", "创建子分类", "FAIL", str(e))

    # TC-CAT-003: 获取分类树
    try:
        resp = requests.get(f"{BASE_URL}/v1/document/categories/tree", headers=headers)
        result = resp.json()
        if result.get("code") == 0:
            log_result("TC-CAT-003", "获取分类树", "PASS", f"分类数量: {len(result['data'])}")
        else:
            log_result("TC-CAT-003", "获取分类树", "FAIL", result.get("msg", "未知错误"))
    except Exception as e:
        log_result("TC-CAT-003", "获取分类树", "FAIL", str(e))

    # TC-CAT-004: 更新分类
    if created_ids:
        try:
            resp = requests.put(f"{BASE_URL}/v1/document/categories/{created_ids[0]}", headers=headers, json={
                "name": "测试分类-已更新"
            })
            result = resp.json()
            if result.get("code") == 0:
                log_result("TC-CAT-004", "更新分类", "PASS")
            else:
                log_result("TC-CAT-004", "更新分类", "FAIL", result.get("msg", "未知错误"))
        except Exception as e:
            log_result("TC-CAT-004", "更新分类", "FAIL", str(e))

    # TC-CAT-005: 获取分类详情
    if created_ids:
        try:
            resp = requests.get(f"{BASE_URL}/v1/document/categories/{created_ids[0]}", headers=headers)
            result = resp.json()
            if result.get("code") == 0:
                log_result("TC-CAT-005", "获取分类详情", "PASS")
            else:
                log_result("TC-CAT-005", "获取分类详情", "FAIL", result.get("msg", "未知错误"))
        except Exception as e:
            log_result("TC-CAT-005", "获取分类详情", "FAIL", str(e))

    return created_ids

def test_document_upload_and_crud(token, category_ids):
    """测试文档上传和 CRUD"""
    print("\n" + "=" * 60)
    print("文档上传与 CRUD 测试")
    print("=" * 60)
    headers = {"Authorization": f"Bearer {token}"}
    created_doc_ids = []
    test_file_content = b"Hello World! This is a test document for the document management module.\nIt has multiple lines.\nLine 3.\nLine 4."

    # TC-DOC-001: 上传文档
    try:
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            f.write(test_file_content)
            temp_file = f.name

        with open(temp_file, 'rb') as f:
            files = {'file': ('test_document.txt', f, 'text/plain')}
            data = {
                'title': '测试文档',
                'description': '这是一个测试文档',
                'visibility': 'private',
            }
            if category_ids:
                data['category_id'] = str(category_ids[0])

            resp = requests.post(f"{BASE_URL}/v1/document/documents/upload", headers=headers, files=files, data=data)
            result = resp.json()
            if result.get("code") == 0:
                doc_id = result['data']['id']
                created_doc_ids.append(doc_id)
                log_result("TC-DOC-001", "上传文档", "PASS", f"文档ID: {doc_id}")
            else:
                log_result("TC-DOC-001", "上传文档", "FAIL", f"{result.get('msg', '未知错误')} - {resp.text}")
        os.unlink(temp_file)
    except Exception as e:
        log_result("TC-DOC-001", "上传文档", "FAIL", str(e))

    # TC-DOC-002: 获取文档列表
    try:
        resp = requests.get(f"{BASE_URL}/v1/document/documents", headers=headers)
        result = resp.json()
        if result.get("code") == 0:
            log_result("TC-DOC-002", "获取文档列表", "PASS", f"总数: {result['data']['total']}")
        else:
            log_result("TC-DOC-002", "获取文档列表", "FAIL", result.get("msg", "未知错误"))
    except Exception as e:
        log_result("TC-DOC-002", "获取文档列表", "FAIL", str(e))

    # TC-DOC-003: 获取文档详情
    if created_doc_ids:
        try:
            resp = requests.get(f"{BASE_URL}/v1/document/documents/{created_doc_ids[0]}", headers=headers)
            result = resp.json()
            if result.get("code") == 0:
                log_result("TC-DOC-003", "获取文档详情", "PASS")
            else:
                log_result("TC-DOC-003", "获取文档详情", "FAIL", result.get("msg", "未知错误"))
        except Exception as e:
            log_result("TC-DOC-003", "获取文档详情", "FAIL", str(e))

    # TC-DOC-004: 更新文档
    if created_doc_ids:
        try:
            resp = requests.put(f"{BASE_URL}/v1/document/documents/{created_doc_ids[0]}", headers=headers, json={
                "title": "测试文档-已更新",
                "description": "文档描述已更新"
            })
            result = resp.json()
            if result.get("code") == 0:
                log_result("TC-DOC-004", "更新文档", "PASS")
            else:
                log_result("TC-DOC-004", "更新文档", "FAIL", result.get("msg", "未知错误"))
        except Exception as e:
            log_result("TC-DOC-004", "更新文档", "FAIL", str(e))

    # TC-DOC-005: 移动文档到其他分类
    if len(created_doc_ids) >= 1 and len(category_ids) >= 2:
        try:
            resp = requests.post(f"{BASE_URL}/v1/document/documents/{created_doc_ids[0]}/move", headers=headers, json={
                "target_category_id": category_ids[1]
            })
            result = resp.json()
            if result.get("code") == 0:
                log_result("TC-DOC-005", "移动文档分类", "PASS")
            else:
                log_result("TC-DOC-005", "移动文档分类", "FAIL", result.get("msg", "未知错误"))
        except Exception as e:
            log_result("TC-DOC-005", "移动文档分类", "FAIL", str(e))

    # TC-DOC-006: 获取文档统计
    try:
        resp = requests.get(f"{BASE_URL}/v1/document/documents/statistics", headers=headers)
        result = resp.json()
        if result.get("code") == 0:
            stats = result['data']
            log_result("TC-DOC-006", "获取文档统计", "PASS", f"总数: {stats.get('total_count')}, 分类数: {stats.get('categories_count')}")
        else:
            log_result("TC-DOC-006", "获取文档统计", "FAIL", result.get("msg", "未知错误"))
    except Exception as e:
        log_result("TC-DOC-006", "获取文档统计", "FAIL", str(e))

    # TC-DOC-007: 按标题搜索文档
    try:
        resp = requests.get(f"{BASE_URL}/v1/document/documents", headers=headers, params={"title": "测试"})
        result = resp.json()
        if result.get("code") == 0:
            log_result("TC-DOC-007", "按标题搜索文档", "PASS", f"搜索结果: {result['data']['total']}")
        else:
            log_result("TC-DOC-007", "按标题搜索文档", "FAIL", result.get("msg", "未知错误"))
    except Exception as e:
        log_result("TC-DOC-007", "按标题搜索文档", "FAIL", str(e))

    return created_doc_ids

def test_version_management(token, doc_ids):
    """测试版本管理"""
    print("\n" + "=" * 60)
    print("版本管理测试")
    print("=" * 60)
    headers = {"Authorization": f"Bearer {token}"}

    if not doc_ids:
        log_result("TC-VER-001", "获取版本列表", "SKIP", "没有测试文档")
        return

    doc_id = doc_ids[0]

    # TC-VER-001: 获取版本列表
    try:
        resp = requests.get(f"{BASE_URL}/v1/document/versions/document/{doc_id}", headers=headers)
        result = resp.json()
        if result.get("code") == 0:
            log_result("TC-VER-001", "获取版本列表", "PASS", f"版本数: {result['data']['total']}")
        else:
            log_result("TC-VER-001", "获取版本列表", "FAIL", result.get("msg", "未知错误"))
    except Exception as e:
        log_result("TC-VER-001", "获取版本列表", "FAIL", str(e))

    # TC-VER-002: 创建新版本
    try:
        file_path = None
        for d in doc_ids[:1]:
            resp_detail = requests.get(f"{BASE_URL}/v1/document/documents/{d}", headers=headers)
            if resp_detail.json().get("code") == 0:
                file_path = resp_detail.json()['data'].get('file_path')
                break

        if file_path and os.path.exists(file_path):
            resp = requests.post(f"{BASE_URL}/v1/document/versions/document/{doc_id}", headers=headers, json={
                "file_path": file_path,
                "file_size": os.path.getsize(file_path),
                "change_log": "添加新版本"
            })
            result = resp.json()
            if result.get("code") == 0:
                log_result("TC-VER-002", "创建新版本", "PASS", f"新版本号: {result['data']['version']}")
            else:
                log_result("TC-VER-002", "创建新版本", "FAIL", result.get("msg", "未知错误"))
        else:
            log_result("TC-VER-002", "创建新版本", "SKIP", "找不到文件路径")
    except Exception as e:
        log_result("TC-VER-002", "创建新版本", "FAIL", str(e))

def test_preview_and_download(token, doc_ids):
    """测试预览和下载"""
    print("\n" + "=" * 60)
    print("预览与下载测试")
    print("=" * 60)
    headers = {"Authorization": f"Bearer {token}"}

    if not doc_ids:
        log_result("TC-PRE-001", "检查文档可预览性", "SKIP", "没有测试文档")
        return

    doc_id = doc_ids[0]

    # TC-PRE-001: 检查可预览性
    try:
        resp = requests.get(f"{BASE_URL}/v1/document/preview/{doc_id}/check", headers=headers)
        result = resp.json()
        if result.get("code") == 0:
            data = result['data']
            log_result("TC-PRE-001", "检查文档可预览性", "PASS",
                       f"可预览: {data.get('is_previewable')}, 类型: {data.get('file_type')}")
        else:
            log_result("TC-PRE-001", "检查文档可预览性", "FAIL", result.get("msg", "未知错误"))
    except Exception as e:
        log_result("TC-PRE-001", "检查文档可预览性", "FAIL", str(e))

    # TC-PRE-002: 预览文档
    try:
        resp = requests.get(f"{BASE_URL}/v1/document/preview/{doc_id}", headers=headers)
        if resp.status_code == 200 and 'application/octet-stream' not in resp.headers.get('content-type', ''):
            log_result("TC-PRE-002", "在线预览文档", "PASS", f"Content-Type: {resp.headers.get('content-type')}")
        elif resp.status_code == 200:
            log_result("TC-PRE-002", "在线预览文档", "PASS", "文件流已返回")
        else:
            log_result("TC-PRE-002", "在线预览文档", "FAIL", f"状态码: {resp.status_code}")
    except Exception as e:
        log_result("TC-PRE-002", "在线预览文档", "FAIL", str(e))

    # TC-PRE-003: 下载文档
    try:
        resp = requests.get(f"{BASE_URL}/v1/document/preview/{doc_id}/download", headers=headers)
        if resp.status_code == 200 and len(resp.content) > 0:
            log_result("TC-PRE-003", "下载文档", "PASS", f"文件大小: {len(resp.content)} bytes")
        else:
            log_result("TC-PRE-003", "下载文档", "FAIL", f"状态码: {resp.status_code}")
    except Exception as e:
        log_result("TC-PRE-003", "下载文档", "FAIL", str(e))

def test_business_query(token, doc_ids):
    """测试业务关联查询"""
    print("\n" + "=" * 60)
    print("业务关联查询测试")
    print("=" * 60)
    headers = {"Authorization": f"Bearer {token}"}

    if not doc_ids:
        log_result("TC-BIZ-001", "按业务查询文档", "SKIP", "没有测试文档")
        return

    doc_id = doc_ids[0]

    # TC-BIZ-001: 先给文档设置业务关联
    try:
        resp = requests.put(f"{BASE_URL}/v1/document/documents/{doc_id}", headers=headers, json={
            "business_type": "product",
            "business_id": 1
        })
        result = resp.json()
        if result.get("code") == 0:
            log_result("TC-BIZ-001", "设置业务关联", "PASS")
        else:
            log_result("TC-BIZ-001", "设置业务关联", "FAIL", result.get("msg", "未知错误"))
    except Exception as e:
        log_result("TC-BIZ-001", "设置业务关联", "FAIL", str(e))

    # TC-BIZ-002: 按业务查询
    try:
        resp = requests.get(f"{BASE_URL}/v1/document/documents/business/product/1", headers=headers)
        result = resp.json()
        if result.get("code") == 0:
            log_result("TC-BIZ-002", "按业务查询文档", "PASS", f"关联文档数: {len(result['data'])}")
        else:
            log_result("TC-BIZ-002", "按业务查询文档", "FAIL", result.get("msg", "未知错误"))
    except Exception as e:
        log_result("TC-BIZ-002", "按业务查询文档", "FAIL", str(e))

def test_trash_and_restore(token, doc_ids):
    """测试回收站功能"""
    print("\n" + "=" * 60)
    print("回收站功能测试")
    print("=" * 60)
    headers = {"Authorization": f"Bearer {token}"}

    if not doc_ids:
        log_result("TC-TRASH-001", "软删除文档", "SKIP", "没有测试文档")
        return

    doc_id = doc_ids[0]

    # TC-TRASH-001: 软删除文档
    try:
        resp = requests.delete(f"{BASE_URL}/v1/document/documents/{doc_id}", headers=headers)
        result = resp.json()
        if result.get("code") == 0:
            log_result("TC-TRASH-001", "软删除文档", "PASS")
        else:
            log_result("TC-TRASH-001", "软删除文档", "FAIL", result.get("msg", "未知错误"))
    except Exception as e:
        log_result("TC-TRASH-001", "软删除文档", "FAIL", str(e))

    # TC-TRASH-002: 查看回收站
    try:
        resp = requests.get(f"{BASE_URL}/v1/document/documents/trash", headers=headers)
        result = resp.json()
        if result.get("code") == 0:
            log_result("TC-TRASH-002", "查看回收站", "PASS", f"回收站文档数: {result['data']['total']}")
        else:
            log_result("TC-TRASH-002", "查看回收站", "FAIL", result.get("msg", "未知错误"))
    except Exception as e:
        log_result("TC-TRASH-002", "查看回收站", "FAIL", str(e))

    # TC-TRASH-003: 恢复文档
    try:
        resp = requests.post(f"{BASE_URL}/v1/document/documents/batch-restore", headers=headers, json={
            "document_ids": [doc_id]
        })
        result = resp.json()
        if result.get("code") == 0 and result.get("data", {}).get("restored_count", 0) > 0:
            log_result("TC-TRASH-003", "恢复文档", "PASS")
        else:
            log_result("TC-TRASH-003", "恢复文档", "FAIL", result.get("msg", "未知错误"))
    except Exception as e:
        log_result("TC-TRASH-003", "恢复文档", "FAIL", str(e))

    # TC-TRASH-004: 批量软删除
    doc_id_2 = doc_ids[1] if len(doc_ids) > 1 else None
    if doc_id_2:
        try:
            resp = requests.post(f"{BASE_URL}/v1/document/documents/batch-delete", headers=headers, json={
                "document_ids": [doc_id_2]
            })
            result = resp.json()
            if result.get("code") == 0:
                log_result("TC-TRASH-004", "批量软删除", "PASS", f"删除数: {result['data']['deleted_count']}")
            else:
                log_result("TC-TRASH-004", "批量软删除", "FAIL", result.get("msg", "未知错误"))
        except Exception as e:
            log_result("TC-TRASH-004", "批量软删除", "FAIL", str(e))

def main():
    print("=" * 60)
    print("文档管理模块 API 测试")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API 地址: {BASE_URL}")
    print("=" * 60)

    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        print("✅ 服务器可达")
    except Exception:
        try:
            response = requests.get(f"{BASE_URL}/docs", timeout=5)
            print("✅ 服务器可达 (通过 /docs)")
        except Exception as e:
            print(f"❌ 服务器不可达: {e}")
            print("请确保后端服务已启动在 port 9998")
            return

    token = login()
    if not token:
        print("\n❌ 无法获取 token，测试终止")
        return

    category_ids = test_category_crud(token)
    doc_ids = test_document_upload_and_crud(token, category_ids)
    test_version_management(token, doc_ids)
    test_preview_and_download(token, doc_ids)
    test_business_query(token, doc_ids)
    test_trash_and_restore(token, doc_ids)

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for r in TEST_RESULTS if r["status"] == "PASS")
    failed = sum(1 for r in TEST_RESULTS if r["status"] == "FAIL")
    skipped = sum(1 for r in TEST_RESULTS if r["status"] == "SKIP")
    total = len(TEST_RESULTS)

    print(f"\n总计: {total} 项测试")
    print(f"  ✅ 通过: {passed}")
    print(f"  ❌ 失败: {failed}")
    print(f"  ⏭️  跳过: {skipped}")

    if failed > 0:
        print("\n失败详情:")
        for r in TEST_RESULTS:
            if r["status"] == "FAIL":
                print(f"  [{r['test_id']}] {r['test_name']}: {r['message']}")

    success_rate = (passed / (total - skipped) * 100) if (total - skipped) > 0 else 0
    print(f"\n通过率: {success_rate:.1f}%")

    # 清理测试数据
    if category_ids:
        print("\n清理测试分类...")
        headers = {"Authorization": f"Bearer {token}"}
        for cat_id in reversed(category_ids):
            try:
                requests.delete(f"{BASE_URL}/v1/document/categories/{cat_id}", headers=headers)
            except Exception:
                pass

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code or 0)
