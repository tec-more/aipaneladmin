-- T1 新增表：customer_organization（客户组织，Q-H；仅客户域，不引入组织级配额 C-23）
-- 溯源：docs/arch/02 §4.2
CREATE TABLE IF NOT EXISTS customer_organization (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    owner_customer_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='customer')
       AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                       WHERE constraint_name='fk_customer_org_owner' AND table_name='customer_organization') THEN
        EXECUTE 'ALTER TABLE customer_organization ADD CONSTRAINT fk_customer_org_owner FOREIGN KEY (owner_customer_id) REFERENCES customer(id) ON DELETE CASCADE';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_customer_org_owner ON customer_organization (owner_customer_id);
