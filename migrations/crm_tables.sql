-- CRM模块数据库建表脚本
-- 生成时间: 2026-07-04

CREATE TABLE IF NOT EXISTS crm_lead (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    company VARCHAR(200),
    source VARCHAR(50),
    status VARCHAR(20) DEFAULT 'new',
    assigned_to BIGINT,
    customer_id BIGINT,
    description TEXT,
    last_follow_up_time TIMESTAMP,
    converted_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm_opportunity (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    customer_id BIGINT NOT NULL,
    contact_id BIGINT,
    stage VARCHAR(50) NOT NULL,
    expected_amount DECIMAL(10,2) NOT NULL,
    actual_amount DECIMAL(10,2),
    probability INT,
    expected_close_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    lost_reason TEXT,
    assigned_to BIGINT,
    last_follow_up_time TIMESTAMP,
    won_at TIMESTAMP,
    lost_at TIMESTAMP,
    product_id BIGINT,
    order_id BIGINT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm_opportunity_stage (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    sort_order INT DEFAULT 0,
    probability INT,
    is_won_stage BOOLEAN DEFAULT FALSE,
    is_lost_stage BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm_stage_change_log (
    id BIGSERIAL PRIMARY KEY,
    opportunity_id BIGINT NOT NULL,
    from_stage VARCHAR(50),
    to_stage VARCHAR(50) NOT NULL,
    changed_by BIGINT NOT NULL,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm_activity (
    id BIGSERIAL PRIMARY KEY,
    type VARCHAR(20) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    content TEXT,
    activity_time TIMESTAMP NOT NULL,
    lead_id BIGINT,
    opportunity_id BIGINT,
    contact_id BIGINT,
    created_by BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm_contact (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    position VARCHAR(100),
    department VARCHAR(100),
    is_primary BOOLEAN DEFAULT FALSE,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(customer_id, phone)
);

CREATE TABLE IF NOT EXISTS crm_follow_up_task (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    lead_id BIGINT,
    opportunity_id BIGINT,
    assigned_to BIGINT NOT NULL,
    due_date TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'todo',
    completed_at TIMESTAMP,
    create_activity_on_complete BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm_lead_source (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm_config (
    id BIGSERIAL PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value VARCHAR(500) NOT NULL,
    description VARCHAR(200),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 初始化默认商机阶段
INSERT INTO crm_opportunity_stage (name, code, sort_order, probability, is_won_stage, is_lost_stage) VALUES
('初步接触', 'initial_contact', 1, 10, FALSE, FALSE),
('需求确认', 'requirement_confirmation', 2, 25, FALSE, FALSE),
('方案报价', 'proposal_quotation', 3, 50, FALSE, FALSE),
('商务谈判', 'negotiation', 4, 75, FALSE, FALSE),
('赢单', 'won', 5, 100, TRUE, FALSE),
('输单', 'lost', 6, 0, FALSE, TRUE)
ON CONFLICT (code) DO NOTHING;

-- 初始化默认线索来源
INSERT INTO crm_lead_source (name, code, sort_order) VALUES
('官网注册', 'website', 1),
('广告投放', 'advertisement', 2),
('转介绍', 'referral', 3),
('展会', 'exhibition', 4),
('其他', 'other', 5)
ON CONFLICT (code) DO NOTHING;

-- 初始化默认系统配置
INSERT INTO crm_config (config_key, config_value, description) VALUES
('auto_recycle_days', '30', '线索自动回收天数'),
('stale_warning_days', '14', '商机超期预警天数')
ON CONFLICT (config_key) DO NOTHING;