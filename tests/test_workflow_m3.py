"""
T5 / M3 工作流定义与版本 单元测试

覆盖（对应任务验证要求）：
A. Schema v2 服务端校验器（纯函数 + 注入式异步校验）
   - E-100 结构（schema_version/start/end 唯一/孤立节点）
   - E-101 变量类型不兼容（含 integer→number 兼容反例）
   - E-102 必填端口未连接
   - E-103 环检测与自连
   - E-104 重复连线 / E-105 输入端占用 / E-106 输出悬空（warning 不阻断）
   - E-107 引用不存在变量/节点输出（from 引用与模板插值）
   - E-108 子工作流引用失效（注入 checker）
   - E-109 用户域节点开关（code 拒绝 R-10 / http 白名单空=拒绝/内网/不在白名单/命中放行）
   - E-110 未授权资源引用（含授权服务异常按未授权处理的安全侧语义）
   - E-111 loop 边界 / E-112 HITL 配置
   - 后台域（admin）兼容：code/http 不做用户域拦截
B. 工作流服务（sqlite 内存库）
   - 空白新建骨架可直接发布
   - 草稿乐观锁 409（DraftConflictError）、校验错误不阻断保存
   - 发布幂等（同 Idempotency-Key 重放返回原响应）、版本不可变（version_no 递增、旧快照不变）
   - 发布校验阻断（用户域 code 节点）
   - 回滚＝以旧版本图生成新版本
   - 归属隔离（cus 交叉访问 404）、usr 超管 data_scope=all 全量可见
   - 删除保护（active 需先停用）

运行：.venv/Scripts/python.exe -m unittest tests.test_workflow_m3 -v
"""
import unittest
from typing import Any, Dict, List, Optional

from tortoise import Tortoise

from base.common.setting import get_model_list
from base.common.authz import OwnerContext, OwnedResourceNotFound
from base.plugins.agent.models.workflow import Workflow
from base.plugins.agent.models.workflow_version import WorkflowVersion
from base.plugins.agent.services.graph_validator import (
    DOMAIN_ADMIN,
    DOMAIN_USER,
    has_blocking_errors,
    validate_graph,
    validate_graph_structure,
)
from base.plugins.agent.services.workflow_service import (
    DraftConflictError,
    ValidationBlockedError,
    WorkflowService,
    WorkflowStateError,
    _IdempotencyStore,
)

TEST_MODULES = get_model_list()


# ============================================================
# 图构造辅助
# ============================================================
def _node(nid: str, ntype: str, *, inputs=None, outputs=None, config=None) -> Dict[str, Any]:
    data: Dict[str, Any] = {"label": nid, "config": config or {}}
    if inputs is not None:
        data["inputs"] = inputs
    if outputs is not None:
        data["outputs"] = outputs
    return {"id": nid, "type": ntype, "position": {"x": 0, "y": 0}, "data": data}


def _edge(eid: str, src: str, tgt: str, sh: str = "out", th: str = "in") -> Dict[str, Any]:
    return {"id": eid, "source": src, "sourceHandle": sh, "target": tgt, "targetHandle": th}


def _graph(nodes, edges, *, variables=None, schema_version=2) -> Dict[str, Any]:
    return {
        "schema_version": schema_version,
        "meta": {"name": "t"},
        "variables": variables if variables is not None else [],
        "nodes": nodes,
        "edges": edges,
        "settings": {"timeout_s": 300},
    }


def minimal_graph() -> Dict[str, Any]:
    """最小合法图：start(query:string) → end(answer:any from start.query)，0 issue"""
    return _graph(
        nodes=[
            _node("n_start", "start", outputs=[{"name": "query", "type": "string"}]),
            _node("n_end", "end",
                  inputs=[{"name": "answer", "type": "any", "from": "n_start.query"}],
                  outputs=[]),
        ],
        edges=[_edge("e1", "n_start", "n_end")],
        variables=[{"name": "query", "type": "string"}],
    )


def codes(issues: List[Dict[str, Any]]) -> set:
    return {i["code"] for i in issues}


# ============================================================
# A1. 校验器：结构 / 图语义（纯函数）
# ============================================================
class ValidatorStructureTest(unittest.TestCase):

    def test_valid_minimal_graph_passes(self):
        self.assertEqual(validate_graph_structure(minimal_graph(), domain=DOMAIN_USER), [])

    def test_empty_v2_graph_skeleton_passes(self):
        issues = validate_graph_structure(
            WorkflowService.empty_v2_graph("骨架"), domain=DOMAIN_USER
        )
        self.assertEqual(issues, [])

    def test_e100_schema_version(self):
        g = minimal_graph()
        g["schema_version"] = 1
        self.assertIn("E-100", codes(validate_graph_structure(g)))

    def test_e100_start_end_uniqueness(self):
        g = minimal_graph()
        g["nodes"].append(_node("n_start2", "start", outputs=[]))
        issues = validate_graph_structure(g)
        self.assertIn("E-100", codes(issues))

    def test_e100_orphan_node_unreachable(self):
        g = minimal_graph()
        g["nodes"].append(_node("n_orphan", "template", config={"template": "x"}))
        issues = validate_graph_structure(g)
        self.assertIn("E-100", codes(issues))
        self.assertTrue(any("不可达" in i["message"] for i in issues))

    def test_e101_type_incompatible(self):
        g = minimal_graph()
        g["nodes"][1]["data"]["inputs"][0]["type"] = "number"  # string → number 不兼容
        issues = validate_graph_structure(g)
        self.assertIn("E-101", codes(issues))

    def test_integer_to_number_is_compatible(self):
        g = minimal_graph()
        g["nodes"][0]["data"]["outputs"][0]["type"] = "integer"
        g["nodes"][1]["data"]["inputs"][0]["type"] = "number"  # integer → number 兼容（PRD §4.3）
        issues = validate_graph_structure(g)
        self.assertNotIn("E-101", codes(issues))

    def test_e102_required_input_unbound(self):
        g = _graph(
            nodes=[
                _node("n_start", "start", outputs=[{"name": "query", "type": "string"}]),
                _node("n_rag", "rag_retrieval",
                      inputs=[],  # query 必填未连接
                      outputs=[{"name": "chunks", "type": "array<chunk>"}],
                      config={"knowledge_base_refs": ["3"], "top_k": 5}),
                _node("n_end", "end",
                      inputs=[{"name": "answer", "type": "any", "from": "n_rag.chunks"}],
                      outputs=[]),
            ],
            edges=[_edge("e1", "n_start", "n_rag"), _edge("e2", "n_rag", "n_end")],
        )
        issues = validate_graph_structure(g)
        e102 = [i for i in issues if i["code"] == "E-102"]
        self.assertTrue(e102 and e102[0]["node_id"] == "n_rag")

    def test_e103_cycle_detected(self):
        g = _graph(
            nodes=[
                _node("n_start", "start", outputs=[]),
                _node("n_a", "template", config={"template": "a"}),
                _node("n_b", "template", config={"template": "b"}),
                _node("n_end", "end", inputs=[], outputs=[]),
            ],
            edges=[
                _edge("e1", "n_start", "n_a"),
                _edge("e2", "n_a", "n_b"),
                _edge("e3", "n_b", "n_a"),   # a ↔ b 环
                _edge("e4", "n_b", "n_end"),
            ],
        )
        issues = validate_graph_structure(g)
        self.assertIn("E-103", codes(issues))

    def test_e103_self_loop(self):
        g = minimal_graph()
        g["edges"].append(_edge("e_self", "n_end", "n_end"))
        issues = validate_graph_structure(g)
        self.assertIn("E-103", codes(issues))

    def test_e104_duplicate_edge(self):
        g = minimal_graph()
        g["edges"].append(_edge("e_dup", "n_start", "n_end"))  # 与 e1 完全相同的四元组
        self.assertIn("E-104", codes(validate_graph_structure(g)))

    def test_e105_input_handle_occupied(self):
        g = _graph(
            nodes=[
                _node("n_start", "start", outputs=[{"name": "query", "type": "string"}]),
                _node("n_t", "template", config={"template": "x"}),
                _node("n_end", "end",
                      inputs=[{"name": "answer", "type": "any", "from": "n_start.query"}],
                      outputs=[]),
            ],
            edges=[
                _edge("e1", "n_start", "n_t"),
                _edge("e2", "n_start", "n_end"),
                _edge("e3", "n_t", "n_end"),   # end.in 第二次被占用
            ],
        )
        issues = validate_graph_structure(g)
        self.assertIn("E-105", codes(issues))

    def test_e106_dangling_outputs_is_warning_only(self):
        g = _graph(
            nodes=[
                _node("n_start", "start", outputs=[{"name": "query", "type": "string"}]),
                _node("n_llm", "llm",
                      outputs=[{"name": "answer", "type": "string"}],  # 悬空输出
                      config={"model_ref": "m1", "user_prompt": "hi"}),
                _node("n_end", "end",
                      inputs=[{"name": "answer", "type": "any", "from": "n_start.query"}],
                      outputs=[]),
            ],
            edges=[_edge("e1", "n_start", "n_llm"), _edge("e2", "n_llm", "n_end")],
        )
        issues = validate_graph_structure(g)
        e106 = [i for i in issues if i["code"] == "E-106"]
        self.assertTrue(e106 and e106[0]["level"] == "warning")
        self.assertFalse(has_blocking_errors(issues))  # warning 不阻断发布

    def test_e107_from_ref_not_dotted(self):
        g = minimal_graph()
        g["nodes"][1]["data"]["inputs"][0]["from"] = "query"  # 非法 bare 引用
        self.assertIn("E-107", codes(validate_graph_structure(g)))

    def test_e107_from_ref_missing_node(self):
        g = minimal_graph()
        g["nodes"][1]["data"]["inputs"][0]["from"] = "n_ghost.out"
        self.assertIn("E-107", codes(validate_graph_structure(g)))

    def test_e107_template_interpolation_ref(self):
        g = _graph(
            nodes=[
                _node("n_start", "start", outputs=[{"name": "query", "type": "string"}]),
                _node("n_llm", "llm",
                      outputs=[{"name": "answer", "type": "string"}],
                      config={"model_ref": "m1", "user_prompt": "{{vars.missing}}"}),
                _node("n_end", "end",
                      inputs=[{"name": "answer", "type": "any", "from": "n_llm.answer"}],
                      outputs=[]),
            ],
            edges=[_edge("e1", "n_start", "n_llm"), _edge("e2", "n_llm", "n_end")],
        )
        issues = validate_graph_structure(g)
        self.assertIn("E-107", codes(issues))

    def test_e111_loop_max_iterations(self):
        g = _graph(
            nodes=[
                _node("n_start", "start", outputs=[{"name": "items", "type": "array<string>"}]),
                _node("n_loop", "loop",
                      inputs=[{"name": "body_in", "type": "any", "from": "n_start.items"},
                              {"name": "items", "type": "any", "from": "n_start.items"}],
                      outputs=[{"name": "result", "type": "any"}],
                      config={"loop_type": "fixed", "fixed_count": 3, "max_iterations": 101}),
                _node("n_end", "end",
                      inputs=[{"name": "answer", "type": "any", "from": "n_loop.result"}],
                      outputs=[]),
            ],
            edges=[_edge("e1", "n_start", "n_loop"), _edge("e2", "n_loop", "n_end")],
        )
        self.assertIn("E-111", codes(validate_graph_structure(g)))

    def test_e111_loop_while_missing_condition(self):
        g = _graph(
            nodes=[
                _node("n_start", "start", outputs=[{"name": "q", "type": "string"}]),
                _node("n_loop", "loop",
                      inputs=[{"name": "body_in", "type": "any", "from": "n_start.q"}],
                      outputs=[{"name": "result", "type": "any"}],
                      config={"loop_type": "while", "max_iterations": 5}),
                _node("n_end", "end",
                      inputs=[{"name": "answer", "type": "any", "from": "n_loop.result"}],
                      outputs=[]),
            ],
            edges=[_edge("e1", "n_start", "n_loop"), _edge("e2", "n_loop", "n_end")],
        )
        self.assertIn("E-111", codes(validate_graph_structure(g)))

    def test_e112_hitl_incomplete(self):
        g = _graph(
            nodes=[
                _node("n_start", "start", outputs=[{"name": "q", "type": "string"}]),
                _node("n_hitl", "hitl",
                      inputs=[{"name": "context", "type": "any", "from": "n_start.q"}],
                      outputs=[{"name": "approved", "type": "boolean"}],
                      config={"assignee_mode": "org_role",  # 缺 assignee_refs
                              "timeout_minutes": 30, "on_timeout": "reject"}),
                _node("n_end", "end",
                      inputs=[{"name": "answer", "type": "any", "from": "n_hitl.approved"}],
                      outputs=[]),
            ],
            edges=[_edge("e1", "n_start", "n_hitl"), _edge("e2", "n_hitl", "n_end")],
        )
        self.assertIn("E-112", codes(validate_graph_structure(g)))


# ============================================================
# A2. 校验器：节点域开关（E-109）
# ============================================================
class ValidatorDomainSwitchTest(unittest.TestCase):

    def _graph_with(self, node) -> Dict[str, Any]:
        return _graph(
            nodes=[
                _node("n_start", "start", outputs=[{"name": "query", "type": "string"}]),
                node,
                _node("n_end", "end",
                      inputs=[{"name": "answer", "type": "any", "from": f"{node['id']}.out"}],
                      outputs=[]),
            ],
            edges=[_edge("e1", "n_start", node["id"]), _edge("e2", node["id"], "n_end")],
        )

    def test_e109_code_forbidden_in_user_domain(self):
        node = _node("n_code", "code", outputs=[{"name": "out", "type": "any"}],
                     config={"code": "return 1"})
        issues = validate_graph_structure(self._graph_with(node), domain=DOMAIN_USER)
        e109 = [i for i in issues if i["code"] == "E-109"]
        self.assertTrue(e109 and e109[0]["node_id"] == "n_code")
        self.assertIn("R-10", e109[0]["message"])

    def test_admin_domain_allows_code(self):
        node = _node("n_code", "code", outputs=[{"name": "out", "type": "any"}],
                     config={"code": "return 1"})
        issues = validate_graph_structure(self._graph_with(node), domain=DOMAIN_ADMIN)
        self.assertNotIn("E-109", codes(issues))

    def test_e109_http_empty_whitelist_rejects(self):
        node = _node("n_http", "http", outputs=[{"name": "out", "type": "string"}],
                     config={"url": "https://api.example.com/x", "method": "GET"})
        issues = validate_graph_structure(
            self._graph_with(node), domain=DOMAIN_USER, http_allowed_domains=[]
        )
        self.assertIn("E-109", codes(issues))

    def test_e109_http_internal_host_rejected(self):
        node = _node("n_http", "http", outputs=[{"name": "out", "type": "string"}],
                     config={"url": "http://192.168.1.10/x", "method": "GET"})
        issues = validate_graph_structure(
            self._graph_with(node), domain=DOMAIN_USER, http_allowed_domains=["192.168.1.10"]
        )
        self.assertIn("E-109", codes(issues))

    def test_e109_http_domain_not_in_whitelist(self):
        node = _node("n_http", "http", outputs=[{"name": "out", "type": "string"}],
                     config={"url": "https://evil.com/x", "method": "GET"})
        issues = validate_graph_structure(
            self._graph_with(node), domain=DOMAIN_USER, http_allowed_domains=["example.com"]
        )
        self.assertIn("E-109", codes(issues))

    def test_http_whitelist_hit_passes(self):
        node = _node("n_http", "http", outputs=[{"name": "out", "type": "string"}],
                     config={"url": "https://api.example.com/x", "method": "GET"})
        issues = validate_graph_structure(
            self._graph_with(node), domain=DOMAIN_USER, http_allowed_domains=["example.com"]
        )
        self.assertNotIn("E-109", codes(issues))


# ============================================================
# A3. 校验器：资源授权 E-110 / 子工作流 E-108（注入式异步）
# ============================================================
class ValidatorAsyncInjectionTest(unittest.IsolatedAsyncioTestCase):

    def _llm_graph(self, model_ref: str = "m_gpt4o") -> Dict[str, Any]:
        return _graph(
            nodes=[
                _node("n_start", "start", outputs=[{"name": "query", "type": "string"}]),
                _node("n_llm", "llm",
                      outputs=[{"name": "answer", "type": "string"}],
                      config={"model_ref": model_ref, "user_prompt": "ok"}),
                _node("n_end", "end",
                      inputs=[{"name": "answer", "type": "any", "from": "n_llm.answer"}],
                      outputs=[]),
            ],
            edges=[_edge("e1", "n_start", "n_llm"), _edge("e2", "n_llm", "n_end")],
        )

    async def test_e110_unauthorized_model_ref(self):
        async def deny_all(rtype, ids):
            return set()

        issues = await validate_graph(
            self._llm_graph(), domain=DOMAIN_USER, resource_checker=deny_all
        )
        e110 = [i for i in issues if i["code"] == "E-110"]
        self.assertTrue(e110 and e110[0]["node_id"] == "n_llm")
        self.assertIn("model:m_gpt4o", e110[0]["missing"])

    async def test_e110_authorized_passes(self):
        async def allow(rtype, ids):
            return {"m_gpt4o"}

        issues = await validate_graph(
            self._llm_graph(), domain=DOMAIN_USER, resource_checker=allow
        )
        self.assertNotIn("E-110", codes(issues))

    async def test_e110_checker_exception_is_safe_side(self):
        async def boom(rtype, ids):
            raise RuntimeError("grant service down")

        issues = await validate_graph(
            self._llm_graph(), domain=DOMAIN_USER, resource_checker=boom
        )
        self.assertIn("E-110", codes(issues))  # 授权服务异常按未授权处理（R-03 安全侧）

    async def test_e108_subworkflow_ref_invalid(self):
        g = _graph(
            nodes=[
                _node("n_start", "start", outputs=[{"name": "q", "type": "string"}]),
                _node("n_sub", "sub_workflow",
                      inputs=[{"name": "inputs", "type": "any", "from": "n_start.q"}],
                      outputs=[{"name": "out", "type": "any"}],
                      config={"workflow_ref": "999", "version_policy": "pinned",
                              "pinned_version": 1, "input_mapping": {"q": "q"}}),
                _node("n_end", "end",
                      inputs=[{"name": "answer", "type": "any", "from": "n_sub.out"}],
                      outputs=[]),
            ],
            edges=[_edge("e1", "n_start", "n_sub"), _edge("e2", "n_sub", "n_end")],
        )

        async def sub_checker(wf_ref, pinned):
            return f"子工作流 {wf_ref} 不存在或已删除"

        issues = await validate_graph(g, domain=DOMAIN_USER, subworkflow_checker=sub_checker)
        self.assertIn("E-108", codes(issues))


# ============================================================
# B. 工作流服务（sqlite 内存库）
# ============================================================
class WorkflowServiceTest(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TEST_MODULES})
        await Tortoise.generate_schemas()
        _IdempotencyStore._mem.clear()
        self.owner_a = OwnerContext(owner_type="cus", owner_id=101)
        self.owner_b = OwnerContext(owner_type="cus", owner_id=102)
        self.super_usr = OwnerContext(
            owner_type="usr", owner_id=999, data_scope="all", is_superuser=True
        )

    async def asyncTearDown(self):
        _IdempotencyStore._mem.clear()
        await Tortoise.close_connections()

    async def _create(self, owner=None, name="wf") -> Workflow:
        wf, issues = await WorkflowService.create_user_workflow(owner or self.owner_a, name=name)
        assert not has_blocking_errors(issues), f"骨架图应合法: {issues}"
        return wf

    # ---- 新建 ----
    async def test_create_blank_user_workflow(self):
        wf = await self._create()
        self.assertEqual(wf.schema_version, "v2")
        self.assertEqual(wf.draft_version, 1)
        self.assertEqual((wf.owner_type, wf.owner_id), ("cus", 101))
        self.assertEqual(wf.definition["schema_version"], 2)

    async def test_create_from_template_copies_graph(self):
        tpl = await Workflow.create(
            name="tpl", description="", status="active",
            definition=minimal_graph(), owner_type="usr", owner_id=1,
            visibility="template", schema_version="v2",
        )
        wf, issues = await WorkflowService.create_user_workflow(
            self.owner_a, name="from_tpl", template_id=tpl.id
        )
        self.assertEqual(wf.definition["nodes"][0]["id"], "n_start")
        self.assertEqual(wf.visibility, "private")
        self.assertEqual((wf.owner_type, wf.owner_id), ("cus", 101))

    # ---- 草稿乐观锁 ----
    async def test_save_draft_optimistic_lock_conflict(self):
        wf = await self._create()
        fresh, issues = await WorkflowService.save_draft(
            wf.id, minimal_graph(), 1, self.owner_a, DOMAIN_USER
        )
        self.assertEqual(fresh.draft_version, 2)
        with self.assertRaises(DraftConflictError) as ctx:
            await WorkflowService.save_draft(
                wf.id, minimal_graph(), 1, self.owner_a, DOMAIN_USER
            )
        self.assertEqual(ctx.exception.current_version, 2)

    async def test_save_draft_validation_not_blocking(self):
        """校验错误不阻断保存，issues 随响应返回"""
        wf = await self._create()
        bad = minimal_graph()
        bad["schema_version"] = 1  # E-100
        fresh, issues = await WorkflowService.save_draft(
            wf.id, bad, 1, self.owner_a, DOMAIN_USER
        )
        self.assertEqual(fresh.draft_version, 2)
        self.assertIn("E-100", codes(issues))

    # ---- 发布 ----
    async def test_publish_creates_version_and_updates_pointer(self):
        wf = await self._create()
        payload = await WorkflowService.publish_workflow(
            wf.id, self.owner_a, domain=DOMAIN_USER
        )
        self.assertEqual(payload["version_no"], 1)
        fresh = await Workflow.get(id=wf.id)
        self.assertEqual(fresh.current_version_id, payload["version_id"])
        self.assertEqual(fresh.status, "active")
        version = await WorkflowVersion.get(id=payload["version_id"])
        self.assertEqual(version.status, "published")
        self.assertIsNotNone(version.resource_refs)

    async def test_publish_idempotent_replay(self):
        wf = await self._create()
        p1 = await WorkflowService.publish_workflow(
            wf.id, self.owner_a, idempotency_key="key-1", domain=DOMAIN_USER
        )
        p2 = await WorkflowService.publish_workflow(
            wf.id, self.owner_a, idempotency_key="key-1", domain=DOMAIN_USER
        )
        self.assertTrue(p2.get("idempotent_replay"))
        self.assertEqual(p1["version_id"], p2["version_id"])
        self.assertEqual(await WorkflowVersion.filter(workflow_id=wf.id).count(), 1)
        # 不同 key 正常发布新版本
        p3 = await WorkflowService.publish_workflow(
            wf.id, self.owner_a, idempotency_key="key-2", domain=DOMAIN_USER
        )
        self.assertEqual(p3["version_no"], 2)

    async def test_version_immutable_after_republish(self):
        wf = await self._create()
        p1 = await WorkflowService.publish_workflow(wf.id, self.owner_a, domain=DOMAIN_USER)
        v1 = await WorkflowVersion.get(id=p1["version_id"])
        v1_graph = dict(v1.graph_json)
        # 改草稿再发布
        changed = minimal_graph()
        changed["meta"]["name"] = "changed"
        await WorkflowService.save_draft(wf.id, changed, 1, self.owner_a, DOMAIN_USER)
        p2 = await WorkflowService.publish_workflow(wf.id, self.owner_a, domain=DOMAIN_USER)
        self.assertEqual(p2["version_no"], 2)
        v1_after = await WorkflowVersion.get(id=p1["version_id"])
        self.assertEqual(v1_after.graph_json, v1_graph)  # 旧版本快照不被修改

    async def test_publish_blocked_by_user_domain_code_node(self):
        wf = await self._create()
        bad = _graph(
            nodes=[
                _node("n_start", "start", outputs=[{"name": "q", "type": "string"}]),
                _node("n_code", "code", outputs=[{"name": "out", "type": "any"}],
                      config={"code": "return 1"}),
                _node("n_end", "end",
                      inputs=[{"name": "answer", "type": "any", "from": "n_code.out"}],
                      outputs=[]),
            ],
            edges=[_edge("e1", "n_start", "n_code"), _edge("e2", "n_code", "n_end")],
        )
        await Workflow.filter(id=wf.id).update(definition=bad)
        with self.assertRaises(ValidationBlockedError) as ctx:
            await WorkflowService.publish_workflow(wf.id, self.owner_a, domain=DOMAIN_USER)
        self.assertIn("E-109", codes(ctx.exception.issues))

    # ---- 回滚 ----
    async def test_rollback_creates_new_version_from_old_graph(self):
        wf = await self._create()
        p1 = await WorkflowService.publish_workflow(wf.id, self.owner_a, domain=DOMAIN_USER)
        changed = minimal_graph()
        changed["meta"]["name"] = "v2-graph"
        await WorkflowService.save_draft(wf.id, changed, 1, self.owner_a, DOMAIN_USER)
        await WorkflowService.publish_workflow(wf.id, self.owner_a, domain=DOMAIN_USER)

        result = await WorkflowService.rollback_workflow(
            wf.id, 1, self.owner_a, domain=DOMAIN_USER
        )
        self.assertEqual(result["rolled_back_from"], 1)
        self.assertEqual(result["version_no"], 3)
        v3 = await WorkflowVersion.get(id=result["version_id"])
        v1 = await WorkflowVersion.get(id=p1["version_id"])
        self.assertEqual(v3.graph_json, v1.graph_json)
        fresh = await Workflow.get(id=wf.id)
        self.assertEqual(fresh.current_version_id, v3.id)

    async def test_rollback_missing_version_404(self):
        wf = await self._create()
        with self.assertRaises(OwnedResourceNotFound):
            await WorkflowService.rollback_workflow(
                wf.id, 99, self.owner_a, domain=DOMAIN_USER
            )

    # ---- 归属隔离 ----
    async def test_ownership_isolation_cross_owner_404(self):
        wf = await self._create(self.owner_a)
        await WorkflowService.publish_workflow(wf.id, self.owner_a, domain=DOMAIN_USER)
        with self.assertRaises(OwnedResourceNotFound):
            await WorkflowService.save_draft(wf.id, minimal_graph(), 1, self.owner_b, DOMAIN_USER)
        with self.assertRaises(OwnedResourceNotFound):
            await WorkflowService.publish_workflow(wf.id, self.owner_b, domain=DOMAIN_USER)
        with self.assertRaises(OwnedResourceNotFound):
            await WorkflowService.get_version_snapshot(wf.id, 1, self.owner_b)
        with self.assertRaises(OwnedResourceNotFound):
            await WorkflowService.list_versions(wf.id, self.owner_b)
        with self.assertRaises(OwnedResourceNotFound):
            await WorkflowService.delete_workflow(wf.id, owner=self.owner_b)
        mine_b = await WorkflowService.get_workflows(owner=self.owner_b)
        self.assertEqual(mine_b, [])

    async def test_admin_superuser_sees_all(self):
        """usr 超管 data_scope=all：可见全部 usr 域资源（PRD §7.1 规则 4 域内语义）；
        cus 域资源不属 usr 数据范围（T2 归属模型既定语义）"""
        other_usr = OwnerContext(owner_type="usr", owner_id=555)
        wf_usr, _ = await WorkflowService.create_user_workflow(other_usr, name="usr-wf")
        wf_cus = await self._create(self.owner_a)
        all_wfs = await WorkflowService.get_workflows(owner=self.super_usr)
        ids = [w.id for w in all_wfs]
        self.assertIn(wf_usr.id, ids)          # 超管看全部 usr 域
        self.assertNotIn(wf_cus.id, ids)       # cus 域不并入 usr 数据范围

    # ---- 删除保护 ----
    async def test_delete_active_workflow_requires_disable(self):
        wf = await self._create()
        await WorkflowService.publish_workflow(wf.id, self.owner_a, domain=DOMAIN_USER)
        with self.assertRaises(WorkflowStateError):
            await WorkflowService.delete_workflow(wf.id, owner=self.owner_a)
        await WorkflowService.disable_workflow(wf.id, self.owner_a)
        ok = await WorkflowService.delete_workflow(wf.id, owner=self.owner_a)
        self.assertTrue(ok)

    # ---- 版本列表/快照 ----
    async def test_list_versions_and_snapshot(self):
        wf = await self._create()
        await WorkflowService.publish_workflow(wf.id, self.owner_a, domain=DOMAIN_USER)
        await WorkflowService.publish_workflow(wf.id, self.owner_a, domain=DOMAIN_USER)
        versions = await WorkflowService.list_versions(wf.id, self.owner_a)
        self.assertEqual([v.version_no for v in versions], [2, 1])
        snap = await WorkflowService.get_version_snapshot(wf.id, 1, self.owner_a)
        self.assertEqual(snap.graph_json["schema_version"], 2)


# ============================================================
# C. D1 迁移验证（usage_record.seq 幂等补列 + 结算去重键）
# ============================================================
class MigrationD1Test(unittest.IsolatedAsyncioTestCase):
    """
    D1 迁移两轮幂等：
    - SQL 静态断言：ADD COLUMN IF NOT EXISTS / CREATE UNIQUE INDEX IF NOT EXISTS
      （PostgreSQL/openGauss 下两轮执行安全的语义保证；SQLite 不支持该子句，
      真实两轮执行属部署侧验证，此处锁定迁移文本的幂等结构不回归）
    - ORM 级验证：seq 默认值 0 生效、UNIQUE(execution_id,node_id,seq) 约束生效
      （重复键写入拒绝 = 结算幂等去重的 DB 兜底）
    """

    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TEST_MODULES})
        await Tortoise.generate_schemas()

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    def test_migration_sql_is_idempotent(self):
        from pathlib import Path
        mig_dir = Path(__file__).resolve().parent.parent / "migrations"
        sql_files = list(mig_dir.glob("core_add_column_usage_record__seq_*.sql"))
        self.assertTrue(sql_files, "D1 迁移文件缺失")
        sql = sql_files[0].read_text(encoding="utf-8").upper()
        self.assertIn("ADD COLUMN IF NOT EXISTS SEQ", sql)
        self.assertIn("CREATE UNIQUE INDEX IF NOT EXISTS", sql)
        self.assertIn("EXECUTION_ID", sql)
        self.assertIn("NODE_ID", sql)

    async def test_usage_record_seq_default_and_unique(self):
        from base.common.quota.models.quota import UsageRecord

        rec = await UsageRecord.create(
            owner_type="cus", owner_id=1, period="2026-11",
            execution_id=7001, node_id="n_llm", resource_type="token", amount=1.5,
        )
        self.assertEqual(rec.seq, 0)  # 缺省 seq=0（D1 默认）
        # 同 (execution_id,node_id,seq) 重复写入被唯一约束拒绝（结算幂等 DB 兜底）
        with self.assertRaises(Exception):
            await UsageRecord.create(
                owner_type="cus", owner_id=1, period="2026-11",
                execution_id=7001, node_id="n_llm", seq=0,
                resource_type="token", amount=2.0,
            )
        # 不同 seq 可正常写入（同节点多事件）
        rec2 = await UsageRecord.create(
            owner_type="cus", owner_id=1, period="2026-11",
            execution_id=7001, node_id="n_llm", seq=1,
            resource_type="token", amount=2.0,
        )
        self.assertEqual(rec2.seq, 1)


if __name__ == "__main__":
    unittest.main()
