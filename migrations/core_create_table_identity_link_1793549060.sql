-- T1 新增表：identity_link（客户<->后台用户身份关联，L1/Q8）
-- 溯源：docs/arch/02 §4.2；索引策略 03 §4：UNIQUE(customer_id) / UNIQUE(user_id)
-- R-14：仅"提示->主动确认->验证"流程可写入，禁止自动绑定代码路径
-- 注意："user" 为保留字，引用必须加双引号
CREATE TABLE IF NOT EXISTS identity_link (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'prompted',
    dismissed_until TIMESTAMPTZ NULL,
    verified_via VARCHAR(20) NULL,
    verified_at TIMESTAMPTZ NULL,
    audit JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 基表存在性兜底后补 FK（Q2）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='customer')
       AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                       WHERE constraint_name='fk_identity_link_customer' AND table_name='identity_link') THEN
        EXECUTE 'ALTER TABLE identity_link ADD CONSTRAINT fk_identity_link_customer FOREIGN KEY (customer_id) REFERENCES customer(id) ON DELETE CASCADE';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='user')
       AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                       WHERE constraint_name='fk_identity_link_user' AND table_name='identity_link') THEN
        EXECUTE 'ALTER TABLE identity_link ADD CONSTRAINT fk_identity_link_user FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE';
    END IF;
END $$;

-- D1：双列各自唯一，映射关系唯一
CREATE UNIQUE INDEX IF NOT EXISTS uq_identity_link_customer ON identity_link (customer_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_identity_link_user ON identity_link (user_id);
