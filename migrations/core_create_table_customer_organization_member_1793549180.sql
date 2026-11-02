-- T1 新增表：customer_organization_member（客户组织成员，HITL 审批人范围解析依据）
-- 溯源：docs/arch/02 §4.2；索引策略 03 §4：(customer_id, status) / (org_id, status)
CREATE TABLE IF NOT EXISTS customer_organization_member (
    id BIGSERIAL PRIMARY KEY,
    org_id BIGINT NOT NULL,
    customer_id BIGINT NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='customer_organization')
       AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                       WHERE constraint_name='fk_customer_org_member_org' AND table_name='customer_organization_member') THEN
        EXECUTE 'ALTER TABLE customer_organization_member ADD CONSTRAINT fk_customer_org_member_org FOREIGN KEY (org_id) REFERENCES customer_organization(id) ON DELETE CASCADE';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='customer')
       AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                       WHERE constraint_name='fk_customer_org_member_customer' AND table_name='customer_organization_member') THEN
        EXECUTE 'ALTER TABLE customer_organization_member ADD CONSTRAINT fk_customer_org_member_customer FOREIGN KEY (customer_id) REFERENCES customer(id) ON DELETE CASCADE';
    END IF;
END $$;

-- 同一客户在同一组织内仅一条成员记录
CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_org_member ON customer_organization_member (org_id, customer_id);
-- 索引策略 03 §4
CREATE INDEX IF NOT EXISTS idx_customer_org_member_customer ON customer_organization_member (customer_id, status);
CREATE INDEX IF NOT EXISTS idx_customer_org_member_org ON customer_organization_member (org_id, status);
