"""
Workflow models
"""
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class Workflow(BaseModel, TimestampMixin):
    """Workflow model"""
    
    name = fields.CharField(max_length=100, description="Workflow name")
    description = fields.TextField(null=True, description="Workflow description")
    status = fields.CharField(max_length=20, default="draft", description="Status: draft/active/inactive")
    definition = fields.JSONField(description="Workflow definition")
    agents = fields.ManyToManyField("models.Agent", related_name="workflows", description="Associated agents")
    
    class Meta:
        table = "workflow"
    
    def __str__(self):
        return self.name


class WorkflowNode(BaseModel, TimestampMixin):
    """Workflow node model"""
    
    workflow = fields.ForeignKeyField("models.Workflow", related_name="nodes", description="Associated workflow")
    name = fields.CharField(max_length=100, description="Node name")
    type = fields.CharField(max_length=50, description="Node type: agent/skill/decision/fork/join")
    config = fields.JSONField(description="Node configuration")
    position = fields.JSONField(description="Node position in UI")
    agent = fields.ForeignKeyField("models.Agent", null=True, related_name="workflow_nodes", description="Associated agent")
    skill = fields.ForeignKeyField("models.Skill", null=True, related_name="workflow_nodes", description="Associated skill")
    
    class Meta:
        table = "workflow_node"
    
    def __str__(self):
        return f"{self.name} ({self.type})"


class WorkflowEdge(BaseModel, TimestampMixin):
    """Workflow edge model"""
    
    workflow = fields.ForeignKeyField("models.Workflow", related_name="edges", description="Associated workflow")
    source_node = fields.ForeignKeyField("models.WorkflowNode", related_name="outgoing_edges", description="Source node")
    target_node = fields.ForeignKeyField("models.WorkflowNode", related_name="incoming_edges", description="Target node")
    condition = fields.TextField(null=True, description="Edge condition")
    label = fields.CharField(max_length=100, null=True, description="Edge label")
    
    class Meta:
        table = "workflow_edge"
    
    def __str__(self):
        return f"{self.source_node.name} -> {self.target_node.name}"


class WorkflowExecution(BaseModel, TimestampMixin):
    """Workflow execution model"""
    
    workflow = fields.ForeignKeyField("models.Workflow", related_name="executions", description="Associated workflow")
    status = fields.CharField(max_length=20, default="running", description="Status: running/success/failed")
    input_data = fields.JSONField(description="Input data")
    output_data = fields.JSONField(null=True, description="Output data")
    error_message = fields.TextField(null=True, description="Error message")
    started_at = fields.DatetimeField(auto_now_add=True, description="Start time")
    completed_at = fields.DatetimeField(null=True, description="Completion time")
    
    class Meta:
        table = "workflow_execution"
    
    def __str__(self):
        return f"Execution of {self.workflow.name} - {self.status}"
