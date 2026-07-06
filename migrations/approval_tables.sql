-- 审批模块数据库建表脚本
-- 生成时间: 2026-07-06

CREATE TABLE IF NOT EXISTS approval_flow (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    form_config JSONB DEFAULT '[]'::jsonb,
    flow_config JSONB DEFAULT '{}'::jsonb,
    business_type VARCHAR(50),
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_approval_flow_business_type ON approval_flow(business_type);
CREATE INDEX IF NOT EXISTS idx_approval_flow_is_active ON approval_flow(is_active);

CREATE TABLE IF NOT EXISTS approval_instance (
    id BIGSERIAL PRIMARY KEY,
    flow_id BIGINT NOT NULL,
    business_type VARCHAR(50),
    business_id BIGINT,
    business_data JSONB,
    title VARCHAR(255) NOT NULL,
    applicant_id BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    current_node VARCHAR(50),
    form_data JSONB,
    result TEXT,
    complete_time TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_approval_instance_flow_id ON approval_instance(flow_id);
CREATE INDEX IF NOT EXISTS idx_approval_instance_business ON approval_instance(business_type, business_id);
CREATE INDEX IF NOT EXISTS idx_approval_instance_applicant ON approval_instance(applicant_id);
CREATE INDEX IF NOT EXISTS idx_approval_instance_status ON approval_instance(status);

CREATE TABLE IF NOT EXISTS approval_task (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL,
    node_id VARCHAR(50) NOT NULL,
    approver_id BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    comment TEXT,
    approve_time TIMESTAMP,
    transfer_to BIGINT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_approval_task_instance ON approval_task(instance_id);
CREATE INDEX IF NOT EXISTS idx_approval_task_approver ON approval_task(approver_id);
CREATE INDEX IF NOT EXISTS idx_approval_task_status ON approval_task(status);

CREATE TABLE IF NOT EXISTS approval_record (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL,
    task_id BIGINT,
    node_id VARCHAR(50),
    operator_id BIGINT NOT NULL,
    action VARCHAR(20) NOT NULL,
    comment TEXT,
    after_status VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_approval_record_instance ON approval_record(instance_id);
CREATE INDEX IF NOT EXISTS idx_approval_record_operator ON approval_record(operator_id);

CREATE TABLE IF NOT EXISTS approval_rule (
    id BIGSERIAL PRIMARY KEY,
    business_type VARCHAR(50) NOT NULL,
    path_pattern VARCHAR(255) NOT NULL,
    methods JSONB DEFAULT '["POST", "PUT", "DELETE"]'::jsonb,
    flow_id BIGINT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    priority INT DEFAULT 0,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_approval_rule_business_type ON approval_rule(business_type);
CREATE INDEX IF NOT EXISTS idx_approval_rule_path_pattern ON approval_rule(path_pattern);
CREATE INDEX IF NOT EXISTS idx_approval_rule_is_active ON approval_rule(is_active);
CREATE INDEX IF NOT EXISTS idx_approval_rule_priority ON approval_rule(priority);

-- 初始化默认审批流程（采购审批）
INSERT INTO approval_flow (name, code, description, is_active, form_config, flow_config, business_type, is_system)
SELECT '采购审批流程', 'default_purchase_approval', '采购订单审批默认流程', TRUE,
    '[{"field": "title", "label": "标题", "type": "text", "required": true}, {"field": "amount", "label": "金额", "type": "number", "required": true}, {"field": "reason", "label": "事由", "type": "textarea", "required": false}]'::jsonb,
    '{"nodes": [{"id": "start", "type": "start", "name": "开始", "approver_config": {}, "approve_type": "single"}, {"id": "manager_approve", "type": "approve", "name": "部门经理审批", "approver_config": {"type": "dynamic", "expression": "applicant.dept_head"}, "approve_type": "single"}, {"id": "director_approve", "type": "approve", "name": "总监审批", "approver_config": {"type": "role", "role_ids": [1]}, "approve_type": "single"}, {"id": "end", "type": "end", "name": "结束", "approver_config": {}, "approve_type": "single"}], "edges": [{"source": "start", "target": "manager_approve", "type": "approve"}, {"source": "manager_approve", "target": "director_approve", "type": "approve"}, {"source": "director_approve", "target": "end", "type": "approve"}, {"source": "manager_approve", "target": "end", "type": "reject"}, {"source": "director_approve", "target": "end", "type": "reject"}]}'::jsonb,
    'purchase_order', TRUE
WHERE NOT EXISTS (SELECT 1 FROM approval_flow WHERE code = 'default_purchase_approval');

-- 初始化默认审批规则（拦截采购订单创建和编辑）
INSERT INTO approval_rule (business_type, path_pattern, methods, flow_id, is_active, priority, description)
SELECT 'purchase_order', '/v1/purchase/order*', '["POST", "PUT"]'::jsonb, af.id, TRUE, 100, '采购订单需要审批'
FROM approval_flow af
WHERE af.code = 'default_purchase_approval'
  AND NOT EXISTS (SELECT 1 FROM approval_rule ar WHERE ar.business_type = 'purchase_order' AND ar.path_pattern = '/v1/purchase/order*');
