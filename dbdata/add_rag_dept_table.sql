-- 创建知识库和部门的多对多关系表
CREATE TABLE IF NOT EXISTS rag_knowledge_base_department (
    id SERIAL PRIMARY KEY,
    ragknowledgebase_id INT NOT NULL REFERENCES rag_knowledge_base(id) ON DELETE CASCADE,
    department_id INT NOT NULL REFERENCES department(id) ON DELETE CASCADE,
    UNIQUE(ragknowledgebase_id, department_id)
);

-- 添加注释
COMMENT ON TABLE rag_knowledge_base_department IS '知识库与部门的关联表';
COMMENT ON COLUMN rag_knowledge_base_department.ragknowledgebase_id IS '知识库ID';
COMMENT ON COLUMN rag_knowledge_base_department.department_id IS '部门ID';
