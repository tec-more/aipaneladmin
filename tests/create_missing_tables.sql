CREATE TABLE IF NOT EXISTS "finance_account" (
  "id" integer DEFAULT nextval('finance_account_id_seq'::regclass) NOT NULL,
  "code" varchar(50) NOT NULL,
  "name" varchar(100) NOT NULL,
  "account_type" varchar(20) NOT NULL,
  "parent_id" integer,
  "balance" numeric DEFAULT 0 NOT NULL,
  "description" text,
  "is_active" boolean DEFAULT true NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_account_templates" (
  "id" bigint DEFAULT nextval('finance_account_templates_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "code" varchar(50) NOT NULL,
  "name" varchar(255) NOT NULL,
  "account_type" varchar(20) NOT NULL,
  "level" integer DEFAULT 1 NOT NULL,
  "parent_code" varchar(50),
  "description" text,
  "reconcile" boolean DEFAULT false NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_accounts" (
  "id" bigint DEFAULT nextval('finance_accounts_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "code" varchar(50) NOT NULL,
  "name" varchar(255) NOT NULL,
  "account_type" varchar(20) NOT NULL,
  "level" integer DEFAULT 1 NOT NULL,
  "is_leaf" boolean DEFAULT true NOT NULL,
  "debit_balance" numeric DEFAULT 0 NOT NULL,
  "credit_balance" numeric DEFAULT 0 NOT NULL,
  "description" text,
  "tax_code" varchar(50),
  "currency_id" integer,
  "currency_code" varchar(10) DEFAULT 'CNY'::character varying NOT NULL,
  "reconcile" boolean DEFAULT false NOT NULL,
  "active" boolean DEFAULT true NOT NULL,
  "parent_id" bigint
);

CREATE TABLE IF NOT EXISTS "finance_asset_changes" (
  "id" bigint DEFAULT nextval('finance_asset_changes_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "change_type" varchar(32) NOT NULL,
  "change_date" date NOT NULL,
  "old_value" numeric NOT NULL,
  "new_value" numeric NOT NULL,
  "description" text NOT NULL,
  "created_by" varchar(64) NOT NULL,
  "asset_id" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_asset_disposals" (
  "id" bigint DEFAULT nextval('finance_asset_disposals_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "disposal_date" date NOT NULL,
  "disposal_method" varchar(32) NOT NULL,
  "disposal_amount" numeric NOT NULL,
  "net_disposal_value" numeric NOT NULL,
  "description" text NOT NULL,
  "created_by" varchar(64) NOT NULL,
  "asset_id" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_assets" (
  "id" bigint DEFAULT nextval('finance_assets_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "asset_code" varchar(64) NOT NULL,
  "asset_name" varchar(128) NOT NULL,
  "asset_category" varchar(64) NOT NULL,
  "model" varchar(128),
  "brand" varchar(64),
  "purchase_date" date NOT NULL,
  "purchase_cost" numeric NOT NULL,
  "salvage_value" numeric DEFAULT 0 NOT NULL,
  "useful_life" integer NOT NULL,
  "depreciation_method" varchar(32) DEFAULT 'straight_line'::character varying NOT NULL,
  "monthly_depreciation" numeric DEFAULT 0 NOT NULL,
  "accumulated_depreciation" numeric DEFAULT 0 NOT NULL,
  "net_value" numeric NOT NULL,
  "location" varchar(128),
  "status" varchar(20) DEFAULT 'in_use'::character varying NOT NULL,
  "description" text,
  "account_id" bigint,
  "department_id" bigint,
  "responsible_person_id" bigint
);

CREATE TABLE IF NOT EXISTS "finance_bank_accounts" (
  "id" bigint DEFAULT nextval('finance_bank_accounts_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "account_name" varchar(128) NOT NULL,
  "bank_name" varchar(128) NOT NULL,
  "account_no" varchar(64) NOT NULL,
  "currency" varchar(16) DEFAULT 'CNY'::character varying NOT NULL,
  "balance" numeric DEFAULT 0 NOT NULL,
  "is_active" boolean DEFAULT true NOT NULL,
  "description" text
);

CREATE TABLE IF NOT EXISTS "finance_bills" (
  "id" bigint DEFAULT nextval('finance_bills_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "bill_no" varchar(64) NOT NULL,
  "bill_type" varchar(32) NOT NULL,
  "amount" numeric NOT NULL,
  "issue_date" date NOT NULL,
  "due_date" date NOT NULL,
  "issuer" varchar(128) NOT NULL,
  "payee" varchar(128) NOT NULL,
  "drawer_bank" varchar(128) NOT NULL,
  "status" varchar(20) DEFAULT 'issued'::character varying NOT NULL,
  "description" text,
  "bank_account_id" bigint
);

CREATE TABLE IF NOT EXISTS "finance_cash_flow_records" (
  "id" bigint DEFAULT nextval('finance_cash_flow_records_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "flow_date" date NOT NULL,
  "amount" numeric NOT NULL,
  "flow_type" varchar(32) NOT NULL,
  "balance" numeric NOT NULL,
  "description" text,
  "reference_no" varchar(64),
  "bank_account_id" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_cash_plans" (
  "id" bigint DEFAULT nextval('finance_cash_plans_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "plan_no" varchar(64) NOT NULL,
  "period" varchar(10) NOT NULL,
  "inflow_amount" numeric NOT NULL,
  "outflow_amount" numeric NOT NULL,
  "net_amount" numeric NOT NULL,
  "status" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "description" text,
  "created_by" varchar(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_cost_transfers" (
  "id" bigint DEFAULT nextval('finance_cost_transfers_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "transfer_no" varchar(64) NOT NULL,
  "period" varchar(10) NOT NULL,
  "total_amount" numeric NOT NULL,
  "status" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "created_by" varchar(64) NOT NULL,
  "confirmed_by" varchar(64),
  "journal_entry_id" bigint
);

CREATE TABLE IF NOT EXISTS "finance_cost_variances" (
  "id" bigint DEFAULT nextval('finance_cost_variances_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "period" varchar(10) NOT NULL,
  "standard_cost" numeric NOT NULL,
  "actual_cost" numeric NOT NULL,
  "variance_amount" numeric NOT NULL,
  "variance_rate" numeric NOT NULL,
  "variance_type" varchar(32) NOT NULL,
  "product_id" bigint
);

CREATE TABLE IF NOT EXISTS "finance_daily_journal" (
  "id" integer DEFAULT nextval('finance_daily_journal_id_seq'::regclass) NOT NULL,
  "journal_date" date NOT NULL,
  "account_id" integer NOT NULL,
  "period" varchar(10) NOT NULL,
  "total_debit" numeric DEFAULT 0 NOT NULL,
  "total_credit" numeric DEFAULT 0 NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_daily_journals" (
  "id" bigint DEFAULT nextval('finance_daily_journals_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "journal_date" date NOT NULL,
  "period" varchar(10) NOT NULL,
  "description" text,
  "reference" varchar(255),
  "debit" numeric DEFAULT 0 NOT NULL,
  "credit" numeric DEFAULT 0 NOT NULL,
  "balance" numeric DEFAULT 0 NOT NULL,
  "balance_type" varchar(10) DEFAULT 'debit'::character varying NOT NULL,
  "journal_entry_id" integer,
  "account_id" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_depreciation_records" (
  "id" bigint DEFAULT nextval('finance_depreciation_records_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "period" varchar(10) NOT NULL,
  "depreciation_amount" numeric NOT NULL,
  "accumulated_depreciation" numeric NOT NULL,
  "created_by" varchar(64) NOT NULL,
  "asset_id" bigint NOT NULL,
  "journal_entry_id" bigint
);

CREATE TABLE IF NOT EXISTS "finance_expense_applies" (
  "id" bigint DEFAULT nextval('finance_expense_applies_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "apply_no" varchar(64) NOT NULL,
  "applicant_name" varchar(64) NOT NULL,
  "expense_type" varchar(32) NOT NULL,
  "amount" numeric NOT NULL,
  "apply_date" date NOT NULL,
  "status" varchar(20) DEFAULT 'pending'::character varying NOT NULL,
  "description" text,
  "approved_by" varchar(64),
  "approved_date" date,
  "account_id" bigint,
  "applicant_id" bigint,
  "department_id" bigint
);

CREATE TABLE IF NOT EXISTS "finance_expense_items" (
  "id" bigint DEFAULT nextval('finance_expense_items_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "expense_date" date NOT NULL,
  "description" varchar(256) NOT NULL,
  "amount" numeric NOT NULL,
  "account_id" bigint,
  "report_id" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_expense_reports" (
  "id" bigint DEFAULT nextval('finance_expense_reports_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "report_no" varchar(64) NOT NULL,
  "applicant_name" varchar(64) NOT NULL,
  "amount" numeric NOT NULL,
  "report_date" date NOT NULL,
  "status" varchar(20) DEFAULT 'pending'::character varying NOT NULL,
  "posted_by" varchar(64),
  "applicant_id" bigint,
  "apply_id" bigint NOT NULL,
  "bank_account_id" bigint,
  "journal_entry_id" bigint
);

CREATE TABLE IF NOT EXISTS "finance_financial_report" (
  "id" integer DEFAULT nextval('finance_financial_report_id_seq'::regclass) NOT NULL,
  "report_type" varchar(50) NOT NULL,
  "period" varchar(10) NOT NULL,
  "year" integer NOT NULL,
  "month" integer NOT NULL,
  "report_data" jsonb NOT NULL,
  "total_revenue" numeric DEFAULT 0 NOT NULL,
  "total_expense" numeric DEFAULT 0 NOT NULL,
  "net_profit" numeric DEFAULT 0 NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_financial_reports" (
  "id" bigint DEFAULT nextval('finance_financial_reports_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "report_no" varchar(64) NOT NULL,
  "report_type" varchar(30) NOT NULL,
  "period" varchar(10) NOT NULL,
  "year" integer NOT NULL,
  "month" integer NOT NULL,
  "report_date" date NOT NULL,
  "status" varchar(20) DEFAULT 'generated'::character varying NOT NULL,
  "data" jsonb,
  "created_by" varchar(50),
  "remark" text
);

CREATE TABLE IF NOT EXISTS "finance_general_ledger" (
  "id" integer DEFAULT nextval('finance_general_ledger_id_seq'::regclass) NOT NULL,
  "account_id" integer NOT NULL,
  "period" varchar(10) NOT NULL,
  "year" integer NOT NULL,
  "month" integer NOT NULL,
  "opening_debit" numeric DEFAULT 0 NOT NULL,
  "opening_credit" numeric DEFAULT 0 NOT NULL,
  "period_debit" numeric DEFAULT 0 NOT NULL,
  "period_credit" numeric DEFAULT 0 NOT NULL,
  "ending_debit" numeric DEFAULT 0 NOT NULL,
  "ending_credit" numeric DEFAULT 0 NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_general_ledgers" (
  "id" bigint DEFAULT nextval('finance_general_ledgers_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "period" varchar(10) NOT NULL,
  "year" integer NOT NULL,
  "month" integer NOT NULL,
  "beginning_debit" numeric DEFAULT 0 NOT NULL,
  "beginning_credit" numeric DEFAULT 0 NOT NULL,
  "beginning_balance" numeric DEFAULT 0 NOT NULL,
  "beginning_balance_type" varchar(10) DEFAULT 'debit'::character varying NOT NULL,
  "debit_amount" numeric DEFAULT 0 NOT NULL,
  "credit_amount" numeric DEFAULT 0 NOT NULL,
  "ending_debit" numeric DEFAULT 0 NOT NULL,
  "ending_credit" numeric DEFAULT 0 NOT NULL,
  "ending_balance" numeric DEFAULT 0 NOT NULL,
  "ending_balance_type" varchar(10) DEFAULT 'debit'::character varying NOT NULL,
  "account_id" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_integration_account_mappings" (
  "id" bigint DEFAULT nextval('finance_integration_account_mappings_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "event_type" varchar(64) NOT NULL,
  "debit_account_code" varchar(64) NOT NULL,
  "credit_account_code" varchar(64) NOT NULL,
  "is_active" boolean DEFAULT true NOT NULL,
  "description" text
);

CREATE TABLE IF NOT EXISTS "finance_integration_configs" (
  "id" bigint DEFAULT nextval('finance_integration_configs_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "config_key" varchar(128) NOT NULL,
  "config_value" varchar(256) NOT NULL,
  "description" text
);

CREATE TABLE IF NOT EXISTS "finance_integration_logs" (
  "id" bigint DEFAULT nextval('finance_integration_logs_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "event_name" varchar(128) NOT NULL,
  "source_type" varchar(64) NOT NULL,
  "source_id" integer,
  "source_no" varchar(128),
  "result" varchar(20) NOT NULL,
  "payable_id" integer,
  "receivable_id" integer,
  "payment_id" integer,
  "receipt_id" integer,
  "journal_id" integer,
  "inventory_cost_ids" jsonb,
  "error_message" text,
  "processing_time_ms" integer DEFAULT 0 NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_inventory_costs" (
  "id" bigint DEFAULT nextval('finance_inventory_costs_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "product_code" varchar(64) NOT NULL,
  "product_name" varchar(128) NOT NULL,
  "batch_no" varchar(64),
  "quantity" numeric NOT NULL,
  "unit_cost" numeric NOT NULL,
  "total_cost" numeric NOT NULL,
  "cost_method" varchar(32) DEFAULT 'weighted_average'::character varying NOT NULL,
  "period" varchar(10) NOT NULL,
  "source_type" varchar(32) NOT NULL,
  "source_id" integer,
  "product_id" bigint
);

CREATE TABLE IF NOT EXISTS "finance_journal_entries" (
  "id" bigint DEFAULT nextval('finance_journal_entries_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "journal_no" varchar(64) NOT NULL,
  "journal_date" date NOT NULL,
  "journal_type" varchar(20) DEFAULT 'general'::character varying NOT NULL,
  "status" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "period" varchar(10) NOT NULL,
  "reference" varchar(255),
  "description" text,
  "total_debit" numeric DEFAULT 0 NOT NULL,
  "total_credit" numeric DEFAULT 0 NOT NULL,
  "created_by" varchar(50),
  "confirmed_by" varchar(50),
  "confirmed_at" timestamp with time zone,
  "posted_by" varchar(50),
  "posted_at" timestamp with time zone,
  "cancelled_by" varchar(50),
  "cancelled_at" timestamp with time zone,
  "remark" text
);

CREATE TABLE IF NOT EXISTS "finance_journal_entry" (
  "id" integer DEFAULT nextval('finance_journal_entry_id_seq'::regclass) NOT NULL,
  "journal_number" varchar(50) NOT NULL,
  "journal_type" varchar(20) NOT NULL,
  "journal_date" date NOT NULL,
  "period" varchar(10) NOT NULL,
  "description" text,
  "total_debit" numeric DEFAULT 0 NOT NULL,
  "total_credit" numeric DEFAULT 0 NOT NULL,
  "status" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "created_by" varchar(100),
  "confirmed_by" varchar(100),
  "posted_by" varchar(100),
  "cancelled_by" varchar(100),
  "confirmed_at" timestamp with time zone,
  "posted_at" timestamp with time zone,
  "cancelled_at" timestamp with time zone,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_journal_line" (
  "id" integer DEFAULT nextval('finance_journal_line_id_seq'::regclass) NOT NULL,
  "journal_entry_id" integer NOT NULL,
  "account_id" integer NOT NULL,
  "debit" numeric DEFAULT 0 NOT NULL,
  "credit" numeric DEFAULT 0 NOT NULL,
  "description" text,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_journal_lines" (
  "id" bigint DEFAULT nextval('finance_journal_lines_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "sequence" integer DEFAULT 1 NOT NULL,
  "description" text,
  "debit" numeric DEFAULT 0 NOT NULL,
  "credit" numeric DEFAULT 0 NOT NULL,
  "tax_amount" numeric DEFAULT 0 NOT NULL,
  "tax_code" varchar(50),
  "currency_code" varchar(10) DEFAULT 'CNY'::character varying NOT NULL,
  "exchange_rate" numeric DEFAULT 1 NOT NULL,
  "original_amount" numeric DEFAULT 0 NOT NULL,
  "partner_id" integer,
  "partner_type" varchar(20),
  "analytic_account_id" integer,
  "remark" text,
  "account_id" bigint NOT NULL,
  "journal_entry_id" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_payable_settlements" (
  "id" bigint DEFAULT nextval('finance_payable_settlements_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "amount" numeric NOT NULL,
  "settlement_date" date NOT NULL,
  "created_by" varchar(64) NOT NULL,
  "payable_id" bigint NOT NULL,
  "payment_id" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_payables" (
  "id" bigint DEFAULT nextval('finance_payables_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "payable_no" varchar(64) NOT NULL,
  "supplier_name" varchar(128) NOT NULL,
  "amount" numeric NOT NULL,
  "paid_amount" numeric DEFAULT 0 NOT NULL,
  "remaining_amount" numeric NOT NULL,
  "due_date" date NOT NULL,
  "status" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "source_type" varchar(32) DEFAULT 'manual'::character varying NOT NULL,
  "source_id" integer,
  "description" text,
  "created_by" varchar(64) NOT NULL,
  "confirmed_by" varchar(64),
  "supplier_id" bigint
);

CREATE TABLE IF NOT EXISTS "finance_payments" (
  "id" bigint DEFAULT nextval('finance_payments_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "payment_no" varchar(64) NOT NULL,
  "supplier_name" varchar(128) NOT NULL,
  "amount" numeric NOT NULL,
  "payment_date" date NOT NULL,
  "status" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "payment_method" varchar(32) DEFAULT 'bank_transfer'::character varying NOT NULL,
  "description" text,
  "created_by" varchar(64) NOT NULL,
  "confirmed_by" varchar(64),
  "posted_by" varchar(64),
  "bank_account_id" bigint,
  "supplier_id" bigint
);

CREATE TABLE IF NOT EXISTS "finance_receipts" (
  "id" bigint DEFAULT nextval('finance_receipts_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "receipt_no" varchar(64) NOT NULL,
  "customer_name" varchar(128) NOT NULL,
  "amount" numeric NOT NULL,
  "receipt_date" date NOT NULL,
  "status" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "payment_method" varchar(32) DEFAULT 'bank_transfer'::character varying NOT NULL,
  "description" text,
  "created_by" varchar(64) NOT NULL,
  "confirmed_by" varchar(64),
  "posted_by" varchar(64),
  "bank_account_id" bigint,
  "customer_id" bigint
);

CREATE TABLE IF NOT EXISTS "finance_receivable_settlements" (
  "id" bigint DEFAULT nextval('finance_receivable_settlements_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "amount" numeric NOT NULL,
  "settlement_date" date NOT NULL,
  "created_by" varchar(64) NOT NULL,
  "receipt_id" bigint NOT NULL,
  "receivable_id" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_receivables" (
  "id" bigint DEFAULT nextval('finance_receivables_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "receivable_no" varchar(64) NOT NULL,
  "customer_name" varchar(128) NOT NULL,
  "amount" numeric NOT NULL,
  "paid_amount" numeric DEFAULT 0 NOT NULL,
  "remaining_amount" numeric NOT NULL,
  "due_date" date NOT NULL,
  "status" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "source_type" varchar(32) DEFAULT 'manual'::character varying NOT NULL,
  "source_id" integer,
  "description" text,
  "created_by" varchar(64) NOT NULL,
  "confirmed_by" varchar(64),
  "customer_id" bigint
);

CREATE TABLE IF NOT EXISTS "finance_sub_ledger" (
  "id" integer DEFAULT nextval('finance_sub_ledger_id_seq'::regclass) NOT NULL,
  "account_id" integer NOT NULL,
  "general_ledger_id" integer NOT NULL,
  "period" varchar(10) NOT NULL,
  "partner_id" integer,
  "partner_name" varchar(200),
  "opening_debit" numeric DEFAULT 0 NOT NULL,
  "opening_credit" numeric DEFAULT 0 NOT NULL,
  "period_debit" numeric DEFAULT 0 NOT NULL,
  "period_credit" numeric DEFAULT 0 NOT NULL,
  "ending_debit" numeric DEFAULT 0 NOT NULL,
  "ending_credit" numeric DEFAULT 0 NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_sub_ledgers" (
  "id" bigint DEFAULT nextval('finance_sub_ledgers_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "period" varchar(10) NOT NULL,
  "sub_account_id" integer,
  "sub_account_name" varchar(255),
  "year" integer NOT NULL,
  "month" integer NOT NULL,
  "beginning_debit" numeric DEFAULT 0 NOT NULL,
  "beginning_credit" numeric DEFAULT 0 NOT NULL,
  "beginning_balance" numeric DEFAULT 0 NOT NULL,
  "beginning_balance_type" varchar(10) DEFAULT 'debit'::character varying NOT NULL,
  "debit_amount" numeric DEFAULT 0 NOT NULL,
  "credit_amount" numeric DEFAULT 0 NOT NULL,
  "ending_debit" numeric DEFAULT 0 NOT NULL,
  "ending_credit" numeric DEFAULT 0 NOT NULL,
  "ending_balance" numeric DEFAULT 0 NOT NULL,
  "ending_balance_type" varchar(10) DEFAULT 'debit'::character varying NOT NULL,
  "partner_id" integer,
  "partner_name" varchar(255),
  "account_id" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_tax_declarations" (
  "id" bigint DEFAULT nextval('finance_tax_declarations_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "declaration_no" varchar(64) NOT NULL,
  "period" varchar(10) NOT NULL,
  "declaration_date" date NOT NULL,
  "status" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "total_output_tax" numeric NOT NULL,
  "total_input_tax" numeric NOT NULL,
  "payable_tax" numeric NOT NULL,
  "paid_tax" numeric DEFAULT 0 NOT NULL,
  "description" text,
  "created_by" varchar(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_tax_invoices" (
  "id" bigint DEFAULT nextval('finance_tax_invoices_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "invoice_no" varchar(64) NOT NULL,
  "invoice_code" varchar(64) NOT NULL,
  "invoice_type" varchar(32) NOT NULL,
  "amount" numeric NOT NULL,
  "tax_amount" numeric NOT NULL,
  "total_amount" numeric NOT NULL,
  "tax_rate" numeric NOT NULL,
  "invoice_date" date NOT NULL,
  "status" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "customer_name" varchar(128) NOT NULL,
  "customer_tax_id" varchar(64),
  "supplier_name" varchar(128),
  "supplier_tax_id" varchar(64),
  "is_input" boolean DEFAULT false NOT NULL,
  "related_order_id" integer,
  "description" text,
  "created_by" varchar(64) NOT NULL,
  "customer_id" bigint,
  "supplier_id" bigint
);

CREATE TABLE IF NOT EXISTS "finance_tax_summaries" (
  "id" bigint DEFAULT nextval('finance_tax_summaries_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "period" varchar(10) NOT NULL,
  "output_tax" numeric NOT NULL,
  "input_tax" numeric NOT NULL,
  "payable_tax" numeric NOT NULL,
  "paid_tax" numeric NOT NULL,
  "balance_tax" numeric NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_trial_balance" (
  "id" integer DEFAULT nextval('finance_trial_balance_id_seq'::regclass) NOT NULL,
  "account_id" integer NOT NULL,
  "period" varchar(10) NOT NULL,
  "year" integer NOT NULL,
  "month" integer NOT NULL,
  "opening_debit" numeric DEFAULT 0 NOT NULL,
  "opening_credit" numeric DEFAULT 0 NOT NULL,
  "period_debit" numeric DEFAULT 0 NOT NULL,
  "period_credit" numeric DEFAULT 0 NOT NULL,
  "ending_debit" numeric DEFAULT 0 NOT NULL,
  "ending_credit" numeric DEFAULT 0 NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS "finance_trial_balances" (
  "id" bigint DEFAULT nextval('finance_trial_balances_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "period" varchar(10) NOT NULL,
  "year" integer NOT NULL,
  "month" integer NOT NULL,
  "beginning_debit" numeric DEFAULT 0 NOT NULL,
  "beginning_credit" numeric DEFAULT 0 NOT NULL,
  "beginning_balance" numeric DEFAULT 0 NOT NULL,
  "beginning_balance_type" varchar(10) DEFAULT 'debit'::character varying NOT NULL,
  "debit_amount" numeric DEFAULT 0 NOT NULL,
  "credit_amount" numeric DEFAULT 0 NOT NULL,
  "ending_debit" numeric DEFAULT 0 NOT NULL,
  "ending_credit" numeric DEFAULT 0 NOT NULL,
  "ending_balance" numeric DEFAULT 0 NOT NULL,
  "ending_balance_type" varchar(10) DEFAULT 'debit'::character varying NOT NULL,
  "is_leaf" boolean DEFAULT true NOT NULL,
  "account_id" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS "mes_barcode_record" (
  "id" integer DEFAULT nextval('mes_barcode_record_id_seq'::regclass) NOT NULL,
  "barcode" varchar(255) NOT NULL,
  "barcode_type" varchar(20) NOT NULL,
  "entity_type" varchar(50),
  "entity_code" varchar(100),
  "status" varchar(20) DEFAULT 'active'::character varying,
  "parsed_data" jsonb,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  "reference_code" varchar(100),
  "is_active" boolean DEFAULT true
);

CREATE TABLE IF NOT EXISTS "mes_bom" (
  "id" bigint DEFAULT nextval('mes_bom_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "product_id" integer,
  "product_code" varchar(100) NOT NULL,
  "product_name" varchar(255) NOT NULL,
  "version" varchar(20) DEFAULT 'V1.0'::character varying NOT NULL,
  "level" integer DEFAULT 1 NOT NULL,
  "parent_item_code" varchar(100),
  "item_id" integer,
  "item_code" varchar(100) NOT NULL,
  "item_name" varchar(255) NOT NULL,
  "quantity" numeric NOT NULL,
  "unit" varchar(20) NOT NULL,
  "scrap_rate" numeric DEFAULT 0 NOT NULL,
  "remark" text,
  "is_active" boolean DEFAULT true NOT NULL,
  "drawing_url" varchar(500),
  "drawing_code" varchar(100)
);

CREATE TABLE IF NOT EXISTS "mes_bom_version" (
  "id" bigint DEFAULT nextval('mes_bom_version_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "product_id" integer,
  "product_code" varchar(100) NOT NULL,
  "product_name" varchar(255) NOT NULL,
  "version" varchar(20) NOT NULL,
  "status" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "description" text,
  "ecn_code" varchar(100),
  "effective_date" date
);

CREATE TABLE IF NOT EXISTS "mes_energy_record" (
  "id" integer DEFAULT nextval('mes_energy_record_id_seq'::regclass) NOT NULL,
  "work_center_code" varchar(100) NOT NULL,
  "energy_type" varchar(50) NOT NULL,
  "consumption" numeric DEFAULT 0,
  "unit" varchar(20),
  "record_date" date,
  "recorder" varchar(100),
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  "equipment_code" varchar(100),
  "consumption_value" numeric DEFAULT 0,
  "record_time" timestamp with time zone,
  "shift_code" varchar(100)
);

CREATE TABLE IF NOT EXISTS "mes_equipment" (
  "id" bigint DEFAULT nextval('mes_equipment_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "equipment_code" varchar(100) NOT NULL,
  "equipment_name" varchar(255) NOT NULL,
  "equipment_type" varchar(50) NOT NULL,
  "model" varchar(100),
  "manufacturer" varchar(255),
  "location" varchar(255),
  "work_center_code" varchar(100),
  "status" varchar(20) DEFAULT 'idle'::character varying NOT NULL,
  "purchase_date" timestamp with time zone,
  "warranty_date" timestamp with time zone,
  "description" text,
  "is_active" boolean DEFAULT true NOT NULL,
  "daily_capacity" integer DEFAULT 0,
  "next_maintenance_date" date
);

CREATE TABLE IF NOT EXISTS "mes_equipment_fault" (
  "id" bigint DEFAULT nextval('mes_equipment_fault_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "fault_code" varchar(100) NOT NULL,
  "equipment_code" varchar(100) NOT NULL,
  "equipment_name" varchar(255) NOT NULL,
  "fault_type" varchar(50) NOT NULL,
  "fault_level" varchar(20) DEFAULT 'minor'::character varying NOT NULL,
  "fault_time" timestamp with time zone,
  "recovery_time" timestamp with time zone,
  "status" varchar(20) DEFAULT 'open'::character varying NOT NULL,
  "description" text,
  "solution" text,
  "operator" varchar(100)
);

CREATE TABLE IF NOT EXISTS "mes_equipment_maintenance" (
  "id" bigint DEFAULT nextval('mes_equipment_maintenance_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "maintenance_code" varchar(100) NOT NULL,
  "equipment_code" varchar(100) NOT NULL,
  "equipment_name" varchar(255) NOT NULL,
  "maintenance_type" varchar(20) NOT NULL,
  "planned_date" timestamp with time zone,
  "actual_date" timestamp with time zone,
  "status" varchar(20) DEFAULT 'pending'::character varying NOT NULL,
  "operator" varchar(100),
  "items" jsonb,
  "remark" text
);

CREATE TABLE IF NOT EXISTS "mes_inspection_standard" (
  "id" bigint DEFAULT nextval('mes_inspection_standard_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "standard_code" varchar(100) NOT NULL,
  "standard_name" varchar(255) NOT NULL,
  "material_code" varchar(100),
  "inspection_type" varchar(20) NOT NULL,
  "items" jsonb,
  "sampling_rule" text,
  "is_active" boolean DEFAULT true NOT NULL
);

CREATE TABLE IF NOT EXISTS "mes_manufacturing_order" (
  "id" bigint DEFAULT nextval('mes_manufacturing_order_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "mo_code" varchar(100) NOT NULL,
  "product_code" varchar(100) NOT NULL,
  "product_name" varchar(255) NOT NULL,
  "quantity" integer NOT NULL,
  "actual_quantity" integer DEFAULT 0 NOT NULL,
  "status" varchar(20) DEFAULT 'planned'::character varying NOT NULL,
  "priority" varchar(20) DEFAULT 'normal'::character varying NOT NULL,
  "route_code" varchar(100),
  "bom_version" varchar(20),
  "planned_start_date" timestamp with time zone,
  "planned_end_date" timestamp with time zone,
  "actual_start_date" timestamp with time zone,
  "actual_end_date" timestamp with time zone,
  "remark" text,
  "source_type" varchar(20) DEFAULT 'manual'::character varying,
  "source_code" varchar(100),
  "released_at" timestamp with time zone,
  "source_mps_id" integer,
  "source_mps_code" varchar(100),
  "source_mps_line_id" integer,
  "source_planned_order_code" varchar(100),
  "warehouse_code" varchar(100),
  "barcode" varchar(100)
);

CREATE TABLE IF NOT EXISTS "mes_material" (
  "id" bigint DEFAULT nextval('mes_material_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "product_id" integer,
  "material_code" varchar(100) NOT NULL,
  "material_name" varchar(255) NOT NULL,
  "material_type" varchar(50) NOT NULL,
  "unit" varchar(20) NOT NULL,
  "specification" varchar(255),
  "description" text,
  "is_active" boolean DEFAULT true NOT NULL,
  "drawing_url" varchar(500),
  "drawing_code" varchar(100)
);

CREATE TABLE IF NOT EXISTS "mes_material_requisition" (
  "id" integer DEFAULT nextval('mes_material_requisition_id_seq'::regclass) NOT NULL,
  "requisition_code" varchar(100) NOT NULL,
  "mo_code" varchar(100) NOT NULL,
  "requisition_type" varchar(20) DEFAULT 'manual'::character varying,
  "warehouse_code" varchar(100),
  "location_code" varchar(100),
  "applicant" varchar(100),
  "status" varchar(20) DEFAULT 'draft'::character varying,
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "mes_material_requisition_detail" (
  "id" integer DEFAULT nextval('mes_material_requisition_detail_id_seq'::regclass) NOT NULL,
  "requisition_id" integer NOT NULL,
  "material_code" varchar(100) NOT NULL,
  "material_name" varchar(255),
  "required_quantity" numeric DEFAULT 0,
  "issued_quantity" numeric DEFAULT 0,
  "unit" varchar(20),
  "warehouse_code" varchar(100),
  "location_code" varchar(100),
  "batch_no" varchar(100),
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  "process_code" varchar(100),
  "substitute_material_code" varchar(100),
  "is_substituted" boolean DEFAULT false
);

CREATE TABLE IF NOT EXISTS "mes_material_return" (
  "id" integer DEFAULT nextval('mes_material_return_id_seq'::regclass) NOT NULL,
  "return_code" varchar(100) NOT NULL,
  "mo_code" varchar(100) NOT NULL,
  "warehouse_code" varchar(100),
  "location_code" varchar(100),
  "operator" varchar(100),
  "status" varchar(20) DEFAULT 'draft'::character varying,
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  "requisition_code" varchar(100)
);

CREATE TABLE IF NOT EXISTS "mes_material_return_detail" (
  "id" integer DEFAULT nextval('mes_material_return_detail_id_seq'::regclass) NOT NULL,
  "return_id" integer NOT NULL,
  "material_code" varchar(100) NOT NULL,
  "material_name" varchar(255),
  "return_quantity" numeric DEFAULT 0,
  "unit" varchar(20),
  "warehouse_code" varchar(100),
  "location_code" varchar(100),
  "batch_no" varchar(100),
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "mes_operation_log" (
  "id" integer DEFAULT nextval('mes_operation_log_id_seq'::regclass) NOT NULL,
  "operation_type" varchar(50) NOT NULL,
  "entity_type" varchar(50) NOT NULL,
  "entity_code" varchar(100) NOT NULL,
  "operator" varchar(100),
  "detail" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  "entity_id" integer,
  "action" varchar(50),
  "old_value" jsonb,
  "new_value" jsonb,
  "operated_at" timestamp without time zone,
  "remark" text
);

CREATE TABLE IF NOT EXISTS "mes_process" (
  "id" bigint DEFAULT nextval('mes_process_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "process_code" varchar(100) NOT NULL,
  "process_name" varchar(255) NOT NULL,
  "process_type" varchar(50) NOT NULL,
  "sequence" integer DEFAULT 0 NOT NULL,
  "work_center_code" varchar(100),
  "work_center_name" varchar(255),
  "standard_time" numeric,
  "description" text,
  "is_active" boolean DEFAULT true NOT NULL,
  "drawing_code" varchar(100)
);

CREATE TABLE IF NOT EXISTS "mes_production_exception" (
  "id" integer DEFAULT nextval('mes_production_exception_id_seq'::regclass) NOT NULL,
  "exception_code" varchar(100) NOT NULL,
  "exception_type" varchar(50) NOT NULL,
  "severity" varchar(20) DEFAULT 'medium'::character varying NOT NULL,
  "wo_code" varchar(100),
  "work_center_code" varchar(100),
  "description" text NOT NULL,
  "reporter" varchar(100),
  "handler" varchar(100),
  "handle_measure" text,
  "handle_result" varchar(20),
  "status" varchar(20) DEFAULT 'pending'::character varying,
  "resolved_at" timestamp with time zone,
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  "mo_code" varchar(100),
  "solution" text,
  "escalation_level" integer DEFAULT 0
);

CREATE TABLE IF NOT EXISTS "mes_production_receipt" (
  "id" integer DEFAULT nextval('mes_production_receipt_id_seq'::regclass) NOT NULL,
  "receipt_code" varchar(100) NOT NULL,
  "mo_code" varchar(100) NOT NULL,
  "product_code" varchar(100),
  "product_name" varchar(255),
  "quantity" numeric DEFAULT 0,
  "unit" varchar(20) DEFAULT '个'::character varying,
  "batch_no" varchar(100),
  "warehouse_code" varchar(100),
  "location_code" varchar(100),
  "inspection_result" varchar(20) DEFAULT 'qualified'::character varying,
  "operator" varchar(100),
  "status" varchar(20) DEFAULT 'draft'::character varying,
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "mes_production_report" (
  "id" integer DEFAULT nextval('mes_production_report_id_seq'::regclass) NOT NULL,
  "report_code" varchar(100) NOT NULL,
  "wo_code" varchar(100) NOT NULL,
  "mo_code" varchar(100),
  "process_code" varchar(100),
  "work_center_code" varchar(100),
  "equipment_code" varchar(100),
  "shift_code" varchar(100),
  "batch_no" varchar(100),
  "operator" varchar(100),
  "qualified_quantity" numeric DEFAULT 0,
  "scrap_quantity" numeric DEFAULT 0,
  "actual_work_hours" numeric DEFAULT 0,
  "actual_start_time" timestamp with time zone,
  "actual_end_time" timestamp with time zone,
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "mes_quality_inspection" (
  "id" bigint DEFAULT nextval('mes_quality_inspection_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "inspection_code" varchar(100) NOT NULL,
  "inspection_type" varchar(20) NOT NULL,
  "mo_code" varchar(100),
  "wo_code" varchar(100),
  "material_code" varchar(100) NOT NULL,
  "material_name" varchar(255) NOT NULL,
  "batch_no" varchar(100),
  "quantity" integer NOT NULL,
  "qualified_quantity" integer DEFAULT 0 NOT NULL,
  "unqualified_quantity" integer DEFAULT 0 NOT NULL,
  "inspection_result" varchar(20) DEFAULT 'pending'::character varying NOT NULL,
  "inspector" varchar(100),
  "inspection_items" jsonb,
  "remark" text
);

CREATE TABLE IF NOT EXISTS "mes_route" (
  "id" bigint DEFAULT nextval('mes_route_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "route_code" varchar(100) NOT NULL,
  "route_name" varchar(255) NOT NULL,
  "product_code" varchar(100) NOT NULL,
  "product_name" varchar(255) NOT NULL,
  "version" varchar(20) DEFAULT 'V1.0'::character varying NOT NULL,
  "description" text,
  "is_active" boolean DEFAULT true NOT NULL,
  "bom_code" varchar(100),
  "bom_version" varchar(20)
);

CREATE TABLE IF NOT EXISTS "mes_route_process" (
  "id" bigint DEFAULT nextval('mes_route_process_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "route_code" varchar(100) NOT NULL,
  "process_code" varchar(100) NOT NULL,
  "process_name" varchar(255) NOT NULL,
  "sequence" integer DEFAULT 0 NOT NULL,
  "work_center_code" varchar(100),
  "work_center_name" varchar(255)
);

CREATE TABLE IF NOT EXISTS "mes_shift_definition" (
  "id" integer DEFAULT nextval('mes_shift_definition_id_seq'::regclass) NOT NULL,
  "shift_code" varchar(100) NOT NULL,
  "shift_name" varchar(255) NOT NULL,
  "start_time" varchar(10) NOT NULL,
  "end_time" varchar(10) NOT NULL,
  "work_center_code" varchar(100),
  "is_cross_day" boolean DEFAULT false,
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  "is_active" boolean DEFAULT true,
  "description" text
);

CREATE TABLE IF NOT EXISTS "mes_shift_handover" (
  "id" integer DEFAULT nextval('mes_shift_handover_id_seq'::regclass) NOT NULL,
  "shift_code" varchar(100) NOT NULL,
  "work_center_code" varchar(100),
  "handover_date" date NOT NULL,
  "from_worker" varchar(100),
  "to_worker" varchar(100),
  "handover_content" text,
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  "date" date,
  "outgoing_leader" varchar(100),
  "incoming_leader" varchar(100),
  "equipment_status" text,
  "production_progress" text,
  "exception_items" text
);

CREATE TABLE IF NOT EXISTS "mes_shift_schedule" (
  "id" integer DEFAULT nextval('mes_shift_schedule_id_seq'::regclass) NOT NULL,
  "shift_id" integer NOT NULL,
  "shift_code" varchar(100),
  "work_center_code" varchar(100),
  "schedule_date" date NOT NULL,
  "worker_id" integer,
  "worker_name" varchar(100),
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  "date" date,
  "operator_list" jsonb,
  "leader" varchar(100)
);

CREATE TABLE IF NOT EXISTS "mes_tooling" (
  "id" integer DEFAULT nextval('mes_tooling_id_seq'::regclass) NOT NULL,
  "tooling_code" varchar(100) NOT NULL,
  "tooling_name" varchar(255) NOT NULL,
  "tooling_type" varchar(50),
  "work_center_code" varchar(100),
  "status" varchar(20) DEFAULT 'normal'::character varying,
  "total_usage_count" integer DEFAULT 0,
  "max_usage_count" integer,
  "last_validated_at" timestamp with time zone,
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  "life_count" integer,
  "used_count" integer DEFAULT 0,
  "life_hours" double precision,
  "used_hours" double precision DEFAULT 0,
  "calibration_date" date,
  "next_calibration_date" date,
  "is_active" boolean DEFAULT true
);

CREATE TABLE IF NOT EXISTS "mes_tooling_process" (
  "id" integer DEFAULT nextval('mes_tooling_process_id_seq'::regclass) NOT NULL,
  "tooling_id" integer NOT NULL,
  "tooling_code" varchar(100),
  "process_code" varchar(100) NOT NULL,
  "work_center_code" varchar(100),
  "usage_count" integer DEFAULT 0,
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "mes_tooling_process_binding" (
  "id" integer DEFAULT nextval('mes_tooling_process_binding_id_seq'::regclass) NOT NULL,
  "tooling_code" varchar(100) NOT NULL,
  "process_code" varchar(100) NOT NULL,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "mes_trace_record" (
  "id" integer DEFAULT nextval('mes_trace_record_id_seq'::regclass) NOT NULL,
  "trace_type" varchar(20) DEFAULT 'production'::character varying NOT NULL,
  "material_batch_no" varchar(100),
  "material_code" varchar(100),
  "material_name" varchar(255),
  "product_batch_no" varchar(100),
  "product_code" varchar(100),
  "product_name" varchar(255),
  "wo_code" varchar(100),
  "mo_code" varchar(100),
  "process_code" varchar(100),
  "work_center_code" varchar(100),
  "operator" varchar(100),
  "quantity" numeric DEFAULT 0,
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  "trace_code" varchar(100) DEFAULT ''::character varying,
  "equipment_code" varchar(100),
  "shift_code" varchar(100),
  "consumed_quantity" numeric DEFAULT 0,
  "produced_quantity" integer DEFAULT 0
);

CREATE TABLE IF NOT EXISTS "mes_work_center" (
  "id" bigint DEFAULT nextval('mes_work_center_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "work_center_code" varchar(100) NOT NULL,
  "work_center_name" varchar(255) NOT NULL,
  "department" varchar(100),
  "location" varchar(255),
  "capacity" integer DEFAULT 1 NOT NULL,
  "description" text,
  "is_active" boolean DEFAULT true NOT NULL
);

CREATE TABLE IF NOT EXISTS "mes_work_order" (
  "id" bigint DEFAULT nextval('mes_work_order_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "wo_code" varchar(100) NOT NULL,
  "mo_code" varchar(100) NOT NULL,
  "mo_name" varchar(255),
  "product_code" varchar(100) NOT NULL,
  "product_name" varchar(255) NOT NULL,
  "process_code" varchar(100) NOT NULL,
  "process_name" varchar(255) NOT NULL,
  "work_center_code" varchar(100) NOT NULL,
  "work_center_name" varchar(255) NOT NULL,
  "quantity" integer NOT NULL,
  "actual_quantity" integer DEFAULT 0 NOT NULL,
  "scrap_quantity" integer DEFAULT 0 NOT NULL,
  "status" varchar(20) DEFAULT 'pending'::character varying NOT NULL,
  "operator" varchar(100),
  "planned_start_date" timestamp with time zone,
  "planned_end_date" timestamp with time zone,
  "actual_start_date" timestamp with time zone,
  "actual_end_date" timestamp with time zone,
  "remark" text,
  "equipment_code" varchar(100),
  "shift_code" varchar(100),
  "batch_no" varchar(100),
  "actual_work_hours" numeric DEFAULT 0,
  "suspended_at" timestamp with time zone,
  "suspend_reason" text,
  "resumed_at" timestamp with time zone,
  "barcode" varchar(100),
  "suspend_source" varchar(100)
);

CREATE TABLE IF NOT EXISTS "mrp2_capacity_requirement_plan" (
  "id" bigint DEFAULT nextval('mrp2_capacity_requirement_plan_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "crp_code" varchar(100) NOT NULL,
  "crp_name" varchar(255) NOT NULL,
  "mrp_id" integer,
  "mrp_code" varchar(100),
  "mps_id" integer,
  "mps_code" varchar(100),
  "status" varchar(20) DEFAULT 'calculating'::character varying NOT NULL,
  "start_date" date NOT NULL,
  "end_date" date NOT NULL,
  "calculation_date" timestamp with time zone NOT NULL,
  "overall_capacity_utilization" numeric DEFAULT 0 NOT NULL,
  "bottleneck_work_centers" jsonb,
  "calculation_summary" jsonb,
  "error_message" text,
  "created_by" varchar(100)
);

CREATE TABLE IF NOT EXISTS "mrp2_crp_detail" (
  "id" bigint DEFAULT nextval('mrp2_crp_detail_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "crp_id" integer NOT NULL,
  "crp_code" varchar(100) NOT NULL,
  "work_center_code" varchar(100) NOT NULL,
  "work_center_name" varchar(255) NOT NULL,
  "period_start" date NOT NULL,
  "period_end" date NOT NULL,
  "available_capacity" numeric NOT NULL,
  "required_capacity" numeric NOT NULL,
  "utilized_capacity" numeric DEFAULT 0 NOT NULL,
  "capacity_utilization" numeric DEFAULT 0 NOT NULL,
  "is_overloaded" boolean DEFAULT false NOT NULL,
  "overload_hours" numeric DEFAULT 0 NOT NULL,
  "recommended_action" text,
  "detail_items" jsonb
);

CREATE TABLE IF NOT EXISTS "mrp2_exception_alert" (
  "id" bigint DEFAULT nextval('mrp2_exception_alert_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "alert_code" varchar(100) NOT NULL,
  "monitor_id" integer,
  "alert_type" varchar(50) NOT NULL,
  "alert_level" varchar(20) DEFAULT 'warning'::character varying NOT NULL,
  "alert_status" varchar(20) DEFAULT 'active'::character varying NOT NULL,
  "related_code" varchar(100),
  "related_name" varchar(255),
  "description" text NOT NULL,
  "recommended_action" text,
  "resolved_by" varchar(100),
  "resolved_at" timestamp with time zone,
  "resolved_note" text
);

CREATE TABLE IF NOT EXISTS "mrp2_master_production_schedule" (
  "id" bigint DEFAULT nextval('mrp2_master_production_schedule_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "mps_code" varchar(100) NOT NULL,
  "mps_name" varchar(255) NOT NULL,
  "start_date" date NOT NULL,
  "end_date" date NOT NULL,
  "period_type" varchar(20) DEFAULT 'week'::character varying NOT NULL,
  "status" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "forecast_id" integer,
  "forecast_code" varchar(100),
  "description" text,
  "created_by" varchar(100),
  "plan_name" varchar(255),
  "approved_by" varchar(100),
  "approved_at" timestamp with time zone,
  "released_by" varchar(100),
  "released_at" timestamp with time zone,
  "demand_time_fence" integer DEFAULT 7,
  "planning_time_fence" integer DEFAULT 14
);

CREATE TABLE IF NOT EXISTS "mrp2_mps_detail" (
  "id" bigint DEFAULT nextval('mrp2_mps_detail_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "mps_id" integer NOT NULL,
  "mps_code" varchar(100) NOT NULL,
  "product_id" integer,
  "product_code" varchar(100) NOT NULL,
  "product_name" varchar(255) NOT NULL,
  "bom_version" varchar(20),
  "route_code" varchar(100),
  "period_start" date NOT NULL,
  "period_end" date NOT NULL,
  "forecast_quantity" numeric DEFAULT 0 NOT NULL,
  "planned_quantity" numeric NOT NULL,
  "production_quantity" numeric DEFAULT 0 NOT NULL,
  "unit" varchar(20) NOT NULL,
  "safety_stock" numeric DEFAULT 0 NOT NULL,
  "planned_inventory" numeric DEFAULT 0 NOT NULL,
  "remark" text
);

CREATE TABLE IF NOT EXISTS "mrp2_mps_plan_line" (
  "id" integer DEFAULT nextval('mrp2_mps_plan_line_id_seq'::regclass) NOT NULL,
  "mps_id" integer NOT NULL,
  "mps_code" varchar(100) NOT NULL,
  "line_no" integer NOT NULL,
  "product_code" varchar(100) NOT NULL,
  "product_name" varchar(255) NOT NULL,
  "plan_quantity" numeric NOT NULL,
  "plan_start_date" date NOT NULL,
  "plan_end_date" date NOT NULL,
  "priority" integer DEFAULT 5,
  "sales_order_no" varchar(100),
  "sales_order_line_no" integer,
  "bom_code" varchar(100),
  "route_code" varchar(100),
  "capacity_check_result" varchar(20) DEFAULT 'pass'::character varying,
  "capacity_check_remark" text,
  "actual_quantity" numeric DEFAULT 0,
  "status" varchar(20) DEFAULT 'planned'::character varying,
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "mrp2_mrp_calculation" (
  "id" bigint DEFAULT nextval('mrp2_mrp_calculation_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "mrp_code" varchar(100) NOT NULL,
  "mrp_name" varchar(255) NOT NULL,
  "mps_id" integer,
  "mps_code" varchar(100),
  "calculation_date" timestamp with time zone NOT NULL,
  "status" varchar(20) DEFAULT 'calculating'::character varying NOT NULL,
  "start_date" date NOT NULL,
  "end_date" date NOT NULL,
  "net_requirement_only" boolean DEFAULT false NOT NULL,
  "include_safety_stock" boolean DEFAULT true NOT NULL,
  "include_wip" boolean DEFAULT true NOT NULL,
  "calculation_result" jsonb,
  "error_message" text,
  "created_by" varchar(100)
);

CREATE TABLE IF NOT EXISTS "mrp2_mrp_result_detail" (
  "id" bigint DEFAULT nextval('mrp2_mrp_result_detail_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "mrp_id" integer NOT NULL,
  "mrp_code" varchar(100) NOT NULL,
  "level" integer DEFAULT 1 NOT NULL,
  "product_id" integer,
  "product_code" varchar(100) NOT NULL,
  "product_name" varchar(255) NOT NULL,
  "period_start" date NOT NULL,
  "period_end" date NOT NULL,
  "gross_requirement" numeric DEFAULT 0 NOT NULL,
  "scheduled_receipts" numeric DEFAULT 0 NOT NULL,
  "projected_available" numeric DEFAULT 0 NOT NULL,
  "net_requirement" numeric DEFAULT 0 NOT NULL,
  "planned_order_receipt" numeric DEFAULT 0 NOT NULL,
  "planned_order_release" numeric DEFAULT 0 NOT NULL,
  "planned_release_date" date,
  "planned_receipt_date" date,
  "lot_size" numeric DEFAULT 1 NOT NULL,
  "lead_time" integer DEFAULT 0 NOT NULL,
  "safety_stock" numeric DEFAULT 0 NOT NULL,
  "unit" varchar(20) NOT NULL,
  "parent_item_code" varchar(100),
  "bom_quantity" numeric DEFAULT 1 NOT NULL
);

CREATE TABLE IF NOT EXISTS "mrp2_plan_execution_monitor" (
  "id" bigint DEFAULT nextval('mrp2_plan_execution_monitor_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "monitor_code" varchar(100) NOT NULL,
  "monitor_name" varchar(255) NOT NULL,
  "mps_id" integer,
  "mps_code" varchar(100),
  "mrp_id" integer,
  "mrp_code" varchar(100),
  "start_date" date NOT NULL,
  "end_date" date NOT NULL,
  "status" varchar(20) DEFAULT 'monitoring'::character varying NOT NULL,
  "overall_progress" numeric DEFAULT 0 NOT NULL,
  "on_time_rate" numeric DEFAULT 0 NOT NULL,
  "quality_rate" numeric DEFAULT 0 NOT NULL,
  "efficiency_rate" numeric DEFAULT 0 NOT NULL,
  "alert_count" integer DEFAULT 0 NOT NULL,
  "exception_count" integer DEFAULT 0 NOT NULL,
  "metrics_summary" jsonb,
  "created_by" varchar(100)
);

CREATE TABLE IF NOT EXISTS "mrp2_planned_order" (
  "id" integer DEFAULT nextval('mrp2_planned_order_id_seq'::regclass) NOT NULL,
  "mrp_id" integer,
  "mrp_code" varchar(100),
  "order_no" varchar(100) NOT NULL,
  "order_type" varchar(20) DEFAULT 'manufacture'::character varying,
  "item_code" varchar(100) NOT NULL,
  "item_name" varchar(255) NOT NULL,
  "planned_quantity" numeric NOT NULL,
  "unit" varchar(20) NOT NULL,
  "planned_start_date" date NOT NULL,
  "planned_end_date" date NOT NULL,
  "source_type" varchar(20) DEFAULT 'mrp'::character varying,
  "source_code" varchar(100),
  "bom_code" varchar(100),
  "route_code" varchar(100),
  "status" varchar(20) DEFAULT 'planned'::character varying,
  "confirmed_quantity" numeric DEFAULT 0,
  "remark" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  "order_code" varchar(100),
  "net_quantity" numeric DEFAULT 0,
  "plan_quantity" numeric DEFAULT 0,
  "material_code" varchar(100),
  "material_name" varchar(255),
  "require_date" date,
  "plan_release_date" date,
  "lead_time" integer DEFAULT 0,
  "batch_rule" varchar(20) DEFAULT 'lot_for_lot'::character varying,
  "batch_size" numeric DEFAULT 1,
  "safety_stock" numeric DEFAULT 0,
  "current_stock" numeric DEFAULT 0,
  "on_order_quantity" numeric DEFAULT 0,
  "gross_requirement" numeric DEFAULT 0,
  "net_requirement" numeric DEFAULT 0,
  "bom_level" integer DEFAULT 0,
  "parent_material_code" varchar(100),
  "source_mps_id" integer,
  "source_mps_line_id" integer,
  "converted_mo_code" varchar(100)
);

CREATE TABLE IF NOT EXISTS "mrp2_sales_forecast" (
  "id" bigint DEFAULT nextval('mrp2_sales_forecast_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "forecast_code" varchar(100) NOT NULL,
  "forecast_name" varchar(255) NOT NULL,
  "forecast_type" varchar(20) DEFAULT 'monthly'::character varying NOT NULL,
  "forecast_date" date NOT NULL,
  "start_date" date NOT NULL,
  "end_date" date NOT NULL,
  "status" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "source" varchar(50) DEFAULT 'manual'::character varying NOT NULL,
  "description" text,
  "created_by" varchar(100)
);

CREATE TABLE IF NOT EXISTS "mrp2_sales_forecast_detail" (
  "id" bigint DEFAULT nextval('mrp2_sales_forecast_detail_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "forecast_id" integer NOT NULL,
  "forecast_code" varchar(100) NOT NULL,
  "product_id" integer,
  "product_code" varchar(100) NOT NULL,
  "product_name" varchar(255) NOT NULL,
  "period_type" varchar(20) DEFAULT 'month'::character varying NOT NULL,
  "period_start" date NOT NULL,
  "period_end" date NOT NULL,
  "forecast_quantity" numeric NOT NULL,
  "unit" varchar(20) NOT NULL,
  "confidence" numeric DEFAULT 80 NOT NULL,
  "remark" text
);

CREATE TABLE IF NOT EXISTS "purchase_order_items" (
  "id" bigint DEFAULT nextval('purchase_order_items_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "product_id" integer,
  "product_code" varchar(100),
  "product_name" varchar(255) NOT NULL,
  "product_spec" varchar(255),
  "product_unit" varchar(20) DEFAULT '件'::character varying NOT NULL,
  "quantity" integer DEFAULT 0 NOT NULL,
  "received_quantity" integer DEFAULT 0 NOT NULL,
  "unit_price" numeric DEFAULT 0 NOT NULL,
  "total_price" numeric DEFAULT 0 NOT NULL,
  "tax_rate" numeric DEFAULT 0 NOT NULL,
  "tax_amount" numeric DEFAULT 0 NOT NULL,
  "remark" text,
  "purchase_order_id" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS "purchase_orders" (
  "id" bigint DEFAULT nextval('purchase_orders_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "order_no" varchar(64) NOT NULL,
  "status" varchar(30) DEFAULT 'draft'::character varying NOT NULL,
  "order_date" timestamp with time zone NOT NULL,
  "expected_delivery_date" timestamp with time zone,
  "actual_delivery_date" timestamp with time zone,
  "total_amount" numeric DEFAULT 0 NOT NULL,
  "paid_amount" numeric DEFAULT 0 NOT NULL,
  "currency" varchar(10) DEFAULT 'CNY'::character varying NOT NULL,
  "exchange_rate" numeric DEFAULT 1 NOT NULL,
  "warehouse_id" integer,
  "warehouse_code" varchar(100),
  "remark" text,
  "created_by" varchar(50),
  "supplier_id" bigint NOT NULL,
  "tax_amount" numeric DEFAULT 0
);

CREATE TABLE IF NOT EXISTS "purchase_receipt_items" (
  "id" bigint DEFAULT nextval('purchase_receipt_items_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "product_id" integer,
  "product_code" varchar(100),
  "product_name" varchar(255) NOT NULL,
  "product_spec" varchar(255),
  "product_unit" varchar(20) DEFAULT '件'::character varying NOT NULL,
  "quantity" integer DEFAULT 0 NOT NULL,
  "unit_price" numeric DEFAULT 0 NOT NULL,
  "total_price" numeric DEFAULT 0 NOT NULL,
  "batch_no" varchar(100),
  "expire_date" timestamp with time zone,
  "remark" text,
  "order_item_id" bigint,
  "receipt_id" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS "purchase_receipts" (
  "id" bigint DEFAULT nextval('purchase_receipts_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "receipt_no" varchar(64) NOT NULL,
  "receipt_date" timestamp with time zone NOT NULL,
  "warehouse_id" integer,
  "warehouse_code" varchar(100),
  "location_id" integer,
  "location_code" varchar(100),
  "total_amount" numeric DEFAULT 0 NOT NULL,
  "inspector" varchar(50),
  "is_qualified" boolean DEFAULT true NOT NULL,
  "quality_result" text,
  "remark" text,
  "created_by" varchar(50),
  "purchase_order_id" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS "rag_document_chunk" (
  "id" bigint DEFAULT nextval('rag_document_chunk_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "document_id" bigint NOT NULL,
  "chunk_index" integer NOT NULL,
  "content" text NOT NULL,
  "metadata" jsonb,
  "node_id" varchar(100),
  "vector" USER-DEFINED,
  "created_by_id" bigint
);

CREATE TABLE IF NOT EXISTS "stock_location" (
  "id" bigint DEFAULT nextval('stock_location_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "location_code" varchar(100) NOT NULL,
  "location_name" varchar(255) NOT NULL,
  "parent_id" integer,
  "parent_code" varchar(100),
  "warehouse_id" integer,
  "warehouse_code" varchar(100),
  "location_type" varchar(20) DEFAULT 'internal'::character varying NOT NULL,
  "usage" varchar(20) DEFAULT 'internal'::character varying NOT NULL,
  "complete_name" varchar(500),
  "path" varchar(500),
  "is_active" boolean DEFAULT true NOT NULL,
  "is_scrap" boolean DEFAULT false NOT NULL,
  "is_inventory_loss" boolean DEFAULT false NOT NULL,
  "posx" integer DEFAULT 0 NOT NULL,
  "posy" integer DEFAULT 0 NOT NULL,
  "posz" integer DEFAULT 0 NOT NULL,
  "capacity" integer DEFAULT 0 NOT NULL,
  "description" text
);

CREATE TABLE IF NOT EXISTS "stock_lot" (
  "id" bigint DEFAULT nextval('stock_lot_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "lot_code" varchar(100) NOT NULL,
  "lot_name" varchar(255) NOT NULL,
  "product_id" integer,
  "product_code" varchar(100) NOT NULL,
  "product_name" varchar(255) NOT NULL,
  "company_code" varchar(100),
  "ref" varchar(100),
  "create_date" timestamp with time zone,
  "use_date" timestamp with time zone,
  "expiry_date" timestamp with time zone,
  "is_active" boolean DEFAULT true NOT NULL,
  "note" text
);

CREATE TABLE IF NOT EXISTS "stock_move" (
  "id" bigint DEFAULT nextval('stock_move_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "move_code" varchar(100) NOT NULL,
  "picking_id" integer NOT NULL,
  "picking_code" varchar(100) NOT NULL,
  "product_id" integer,
  "product_code" varchar(100) NOT NULL,
  "product_name" varchar(255) NOT NULL,
  "product_uom" varchar(20) NOT NULL,
  "product_uom_qty" numeric NOT NULL,
  "secondary_uom" varchar(20),
  "secondary_uom_qty" numeric,
  "conversion_factor" numeric DEFAULT 1 NOT NULL,
  "location_id" integer NOT NULL,
  "location_code" varchar(100) NOT NULL,
  "location_name" varchar(255) NOT NULL,
  "location_dest_id" integer NOT NULL,
  "location_dest_code" varchar(100) NOT NULL,
  "location_dest_name" varchar(255) NOT NULL,
  "state" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "quantity_done" numeric DEFAULT 0 NOT NULL,
  "reserved_quantity" numeric DEFAULT 0 NOT NULL,
  "origin" varchar(100),
  "origin_type" varchar(50),
  "reference" varchar(200),
  "procurement_id" integer,
  "procurement_code" varchar(100),
  "rule_id" integer,
  "rule_code" varchar(100),
  "company_code" varchar(100),
  "date_expected" timestamp with time zone,
  "date" timestamp with time zone,
  "backorder_id" integer,
  "backorder_code" varchar(100),
  "note" text
);

CREATE TABLE IF NOT EXISTS "stock_move_line" (
  "id" bigint DEFAULT nextval('stock_move_line_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "move_line_code" varchar(100) NOT NULL,
  "picking_id" integer NOT NULL,
  "picking_code" varchar(100) NOT NULL,
  "move_id" integer NOT NULL,
  "move_code" varchar(100) NOT NULL,
  "product_id" integer,
  "product_code" varchar(100) NOT NULL,
  "product_name" varchar(255) NOT NULL,
  "product_uom_id" integer,
  "product_uom" varchar(20) NOT NULL,
  "product_uom_qty" numeric NOT NULL,
  "qty_done" numeric DEFAULT 0 NOT NULL,
  "location_id" integer NOT NULL,
  "location_code" varchar(100) NOT NULL,
  "location_name" varchar(255) NOT NULL,
  "location_dest_id" integer NOT NULL,
  "location_dest_code" varchar(100) NOT NULL,
  "location_dest_name" varchar(255) NOT NULL,
  "lot_id" integer,
  "lot_name" varchar(100),
  "lot_ref" varchar(100),
  "serial_no" varchar(100),
  "package_id" integer,
  "package_code" varchar(100),
  "result_package_id" integer,
  "result_package_code" varchar(100),
  "owner_id" integer,
  "owner_code" varchar(100),
  "state" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "company_code" varchar(100),
  "date" timestamp with time zone,
  "reference" varchar(200),
  "is_done" boolean DEFAULT false NOT NULL,
  "note" text
);

CREATE TABLE IF NOT EXISTS "stock_package" (
  "id" bigint DEFAULT nextval('stock_package_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "package_code" varchar(100) NOT NULL,
  "package_name" varchar(255) NOT NULL,
  "package_type" varchar(50) DEFAULT 'box'::character varying NOT NULL,
  "location_id" integer,
  "location_code" varchar(100),
  "location_name" varchar(255),
  "company_code" varchar(100),
  "owner_id" integer,
  "owner_code" varchar(100),
  "parent_id" integer,
  "parent_code" varchar(100),
  "is_active" boolean DEFAULT true NOT NULL,
  "weight" numeric,
  "length" numeric,
  "width" numeric,
  "height" numeric,
  "note" text
);

CREATE TABLE IF NOT EXISTS "stock_picking" (
  "id" bigint DEFAULT nextval('stock_picking_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "picking_code" varchar(100) NOT NULL,
  "picking_type_id" integer NOT NULL,
  "picking_type_code" varchar(100) NOT NULL,
  "picking_type_name" varchar(255) NOT NULL,
  "origin" varchar(100),
  "origin_type" varchar(50),
  "partner_code" varchar(100),
  "partner_name" varchar(255),
  "location_id" integer NOT NULL,
  "location_code" varchar(100) NOT NULL,
  "location_name" varchar(255) NOT NULL,
  "location_dest_id" integer NOT NULL,
  "location_dest_code" varchar(100) NOT NULL,
  "location_dest_name" varchar(255) NOT NULL,
  "move_type" varchar(20) DEFAULT 'direct'::character varying NOT NULL,
  "state" varchar(20) DEFAULT 'draft'::character varying NOT NULL,
  "scheduled_date" timestamp with time zone,
  "date_done" timestamp with time zone,
  "owner_code" varchar(100),
  "responsible" varchar(100),
  "priority" varchar(10) DEFAULT 'normal'::character varying NOT NULL,
  "company_code" varchar(100),
  "backorder_id" integer,
  "backorder_code" varchar(100),
  "note" text,
  "printed" boolean DEFAULT false NOT NULL
);

CREATE TABLE IF NOT EXISTS "stock_picking_type" (
  "id" bigint DEFAULT nextval('stock_picking_type_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "picking_type_code" varchar(100) NOT NULL,
  "picking_type_name" varchar(255) NOT NULL,
  "code" varchar(20) NOT NULL,
  "sequence_code" varchar(50) DEFAULT '{type}/{year}/{month}'::character varying NOT NULL,
  "warehouse_id" integer,
  "warehouse_code" varchar(100),
  "default_location_src_id" integer,
  "default_location_src_code" varchar(100),
  "default_location_dest_id" integer,
  "default_location_dest_code" varchar(100),
  "last_sequence" integer DEFAULT 0 NOT NULL,
  "is_active" boolean DEFAULT true NOT NULL,
  "show_operations" boolean DEFAULT false NOT NULL,
  "show_reserved" boolean DEFAULT true NOT NULL,
  "color" integer DEFAULT 0 NOT NULL,
  "description" text
);

CREATE TABLE IF NOT EXISTS "stock_quant" (
  "id" bigint DEFAULT nextval('stock_quant_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "quant_code" varchar(100) NOT NULL,
  "product_id" integer,
  "product_code" varchar(100) NOT NULL,
  "product_name" varchar(255) NOT NULL,
  "location_id" integer NOT NULL,
  "location_code" varchar(100) NOT NULL,
  "location_name" varchar(255) NOT NULL,
  "lot_id" integer,
  "lot_name" varchar(100),
  "serial_no" varchar(100),
  "package_id" integer,
  "package_code" varchar(100),
  "owner_id" integer,
  "owner_code" varchar(100),
  "quantity" numeric DEFAULT 0 NOT NULL,
  "reserved_quantity" numeric DEFAULT 0 NOT NULL,
  "available_quantity" numeric DEFAULT 0 NOT NULL,
  "uom_id" integer,
  "uom_code" varchar(20) DEFAULT 'unit'::character varying NOT NULL,
  "uom_name" varchar(50) DEFAULT '件'::character varying NOT NULL,
  "secondary_uom_id" integer,
  "secondary_uom_name" varchar(50),
  "conversion_factor" numeric DEFAULT 1 NOT NULL,
  "inventory_value" numeric DEFAULT 0 NOT NULL,
  "cost" numeric,
  "company_code" varchar(100),
  "in_date" timestamp with time zone,
  "expiry_date" timestamp with time zone,
  "is_propagated" boolean DEFAULT false NOT NULL,
  "note" text
);

CREATE TABLE IF NOT EXISTS "stock_quant_reservation" (
  "id" bigint DEFAULT nextval('stock_quant_reservation_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "reservation_code" varchar(100) NOT NULL,
  "quant_id" integer NOT NULL,
  "quant_code" varchar(100) NOT NULL,
  "move_id" integer NOT NULL,
  "move_code" varchar(100) NOT NULL,
  "move_line_id" integer,
  "move_line_code" varchar(100),
  "product_code" varchar(100) NOT NULL,
  "location_id" integer NOT NULL,
  "location_code" varchar(100) NOT NULL,
  "lot_id" integer,
  "lot_name" varchar(100),
  "serial_no" varchar(100),
  "quantity" numeric NOT NULL,
  "reserved_at" timestamp with time zone,
  "released_at" timestamp with time zone,
  "state" varchar(20) DEFAULT 'reserved'::character varying NOT NULL,
  "company_code" varchar(100),
  "note" text
);

CREATE TABLE IF NOT EXISTS "stock_warehouse" (
  "id" bigint DEFAULT nextval('stock_warehouse_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "warehouse_code" varchar(100) NOT NULL,
  "warehouse_name" varchar(255) NOT NULL,
  "warehouse_type" varchar(20) DEFAULT 'internal'::character varying NOT NULL,
  "company_code" varchar(100),
  "view_location_id" integer,
  "view_location_code" varchar(100),
  "lot_stock_id" integer,
  "lot_stock_code" varchar(100),
  "input_location_id" integer,
  "input_location_code" varchar(100),
  "output_location_id" integer,
  "output_location_code" varchar(100),
  "qc_location_id" integer,
  "qc_location_code" varchar(100),
  "pack_location_id" integer,
  "pack_location_code" varchar(100),
  "scrap_location_id" integer,
  "scrap_location_code" varchar(100),
  "address" varchar(500),
  "manager" varchar(100),
  "contact_phone" varchar(50),
  "is_active" boolean DEFAULT true NOT NULL,
  "description" text
);

CREATE TABLE IF NOT EXISTS "suppliers" (
  "id" bigint DEFAULT nextval('suppliers_id_seq'::regclass) NOT NULL,
  "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  "supplier_code" varchar(64) NOT NULL,
  "supplier_name" varchar(255) NOT NULL,
  "supplier_type" varchar(20) DEFAULT 'distributor'::character varying NOT NULL,
  "status" varchar(20) DEFAULT 'active'::character varying NOT NULL,
  "contact_name" varchar(100),
  "contact_phone" varchar(20),
  "contact_email" varchar(100),
  "address" text,
  "province" varchar(50),
  "city" varchar(50),
  "district" varchar(50),
  "tax_id" varchar(50),
  "bank_name" varchar(100),
  "bank_account" varchar(100),
  "credit_limit" numeric DEFAULT 0 NOT NULL,
  "payment_term" varchar(50),
  "delivery_days" integer,
  "remark" text,
  "is_preferred" boolean DEFAULT false NOT NULL
);

