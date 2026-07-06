# 业务 Service 列表文档

> 生成时间：2026-07-06
> 说明：列出所有继承 `BaseBusinessService` 的服务类及其 `model` 属性，用于审批规则配置中的"业务模型"选项。

---

## 一、agent 插件

| 文件 | 类名 | model |
|------|------|-------|
| `agent/services/agent_service.py` | `AgentService` | `agent` |
| `agent/services/checkpoint_service.py` | `CheckpointService` | `checkpoint` |
| `agent/services/dialog_flow_service.py` | `DialogFlowService` | `dialog_flow` |
| `agent/services/document_processing_service.py` | `DocumentProcessingService` | `document_processing` |
| `agent/services/memory_service.py` | `MemoryService` | `memory` |
| `agent/services/rag_service.py` | `VectorService` | `vector` |
| `agent/services/rag_service.py` | `RAGService` | `rag` |
| `agent/services/rag_service.py` | `HybridRAGService` | `hybrid_r_a_g` |
| `agent/services/rag_service.py` | `RAGPermissionService` | `rag_permission` |
| `agent/services/skill_category_service.py` | `SkillCategoryService` | `skill_category` |
| `agent/services/skill_service.py` | `SkillService` | `skill` |
| `agent/services/task_decomposer_service.py` | `TaskDecomposerService` | `task_decomposer` |
| `agent/services/tool_service.py` | `ToolService` | `tool` |
| `agent/services/tool_tag_service.py` | `ToolTagService` | `tool_tag` |
| `agent/services/workflow_service.py` | `WorkflowService` | `workflow` |

### agent 辅助类（不继承 BaseBusinessService）

| 文件 | 类名 | 说明 |
|------|------|------|
| `agent/services/dialog_flow_langgraph.py` | `DialogFlowLangGraphExecutor` | 对话流 LangGraph 执行器 |
| `agent/services/langgraph_executor.py` | `LangGraphExecutor` | LangGraph 智能体执行器 |
| `agent/services/rag_service.py` | `TextSplitter` | 文本分割器 |
| `agent/services/rag_service.py` | `DocumentProcessor` | 文档处理器 |

---

## 二、approval 插件

| 文件 | 类名 | model | 说明 |
|------|------|-------|------|
| `approval/services/approval_gate.py` | - | - | 审批门禁 + 执行器（核心，不继承 BaseBusinessService） |
| `approval/services/flow_service.py` | `FlowService` | - | 审批流程 CRUD |
| `approval/services/rule_service.py` | `RuleService` | - | 审批规则 CRUD + 匹配 |
| `approval/services/instance_service.py` | `InstanceService` | - | 审批实例管理 |
| `approval/services/task_service.py` | `TaskService` | - | 审批任务管理 |

> 审批模块自身不注册业务 model，只提供框架能力。

---

## 三、audit 插件

| 文件 | 类名 | model |
|------|------|-------|
| `audit/services/audit_config_service.py` | `AuditConfigService` | `audit_config` |
| `audit/services/audit_service.py` | `AuditTraceService` | `audit_trace` |
| `audit/services/audit_service.py` | `InputLayerService` | `input_layer` |
| `audit/services/audit_service.py` | `DecisionLayerService` | `decision_layer` |
| `audit/services/audit_service.py` | `ExecutionLayerService` | `execution_layer` |
| `audit/services/audit_service.py` | `OutputLayerService` | `output_layer` |
| `audit/services/audit_service.py` | `SystemLayerService` | `system_layer` |
| `audit/services/audit_service.py` | `AuditLogService` | `audit_log` |
| `audit/services/audit_service.py` | `AuditReportService` | `audit_report` |
| `audit/services/audit_service.py` | `RiskAuditService` | `risk_audit` |
| `audit/services/data_change_service.py` | `DataChangeService` | `data_change` |
| `audit/services/login_log_service.py` | `LoginLogService` | `login_log` |

---

## 四、crm 插件

| 文件 | 类名 | model |
|------|------|-------|
| `crm/services/activity_service.py` | `ActivityService` | `activity` |
| `crm/services/contact_service.py` | `ContactService` | `contact` |
| `crm/services/crm_config_service.py` | `CrmConfigService` | `crm_config` |
| `crm/services/crm_scheduler_service.py` | `CrmSchedulerService` | `crm_scheduler` |
| `crm/services/follow_up_task_service.py` | `FollowUpTaskService` | `follow_up_task` |
| `crm/services/lead_service.py` | `LeadService` | `lead` |
| `crm/services/opportunity_service.py` | `OpportunityService` | `opportunity` |

---

## 五、customer 插件

| 文件 | 类名 | model |
|------|------|-------|
| `customer/services/customer_service.py` | `CustomerService` | `customer` |
| `customer/services/membership_service.py` | `MembershipService` | `membership` |
| `customer/services/payment_service.py` | `PaymentService` | `payment` |
| `customer/services/purchase_service.py` | `PurchaseService` | `purchase` |

---

## 六、equipment 插件

| 文件 | 类名 | model |
|------|------|-------|
| `equipment/services/equipment_service.py` | `EquipmentService` | `equipment` |
| `equipment/services/equipment_service.py` | `EquipmentMaintenanceService` | `equipment_maintenance` |
| `equipment/services/equipment_service.py` | `EquipmentFaultService` | `equipment_fault` |

---

## 七、finance 插件

| 文件 | 类名 | model |
|------|------|-------|
| `finance/services/account_service.py` | `AccountService` | `account` |
| `finance/services/finance_integration_service.py` | `FinanceIntegrationService` | `finance_integration` |
| `finance/services/integration_account_mapping_service.py` | `IntegrationAccountMappingService` | `integration_account_mapping` |
| `finance/services/integration_config_service.py` | `IntegrationConfigService` | `integration_config` |
| `finance/services/integration_log_service.py` | `IntegrationLogService` | `integration_log` |
| `finance/services/journal_service.py` | `JournalService` | `journal` |
| `finance/services/report_service.py` | `ReportService` | `report` |

---

## 八、inventory 插件

| 文件 | 类名 | model |
|------|------|-------|
| `inventory/services/inventory_service.py` | `LocationService` | `location` |
| `inventory/services/inventory_service.py` | `WarehouseService` | `warehouse` |
| `inventory/services/inventory_service.py` | `PickingTypeService` | `picking_type` |
| `inventory/services/inventory_service.py` | `LotService` | `lot` |
| `inventory/services/inventory_service.py` | `PackageService` | `package` |
| `inventory/services/inventory_service.py` | `PickingService` | `picking` |
| `inventory/services/inventory_service.py` | `MoveService` | `move` |
| `inventory/services/inventory_service.py` | `MoveLineService` | `move_line` |
| `inventory/services/inventory_service.py` | `QuantService` | `quant` |
| `inventory/services/inventory_service.py` | `ReservationService` | `reservation` |

---

## 九、mes 插件

| 文件 | 类名 | model |
|------|------|-------|
| `mes/services/base_data_service.py` | `MaterialService` | `material` |
| `mes/services/base_data_service.py` | `BomService` | `bom` |
| `mes/services/base_data_service.py` | `BomVersionService` | `bom_version` |
| `mes/services/base_data_service.py` | `WorkCenterService` | `work_center` |
| `mes/services/base_data_service.py` | `ProcessService` | `process` |
| `mes/services/base_data_service.py` | `RouteService` | `route` |
| `mes/services/material_flow_service.py` | `MaterialRequisitionService` | `material_requisition` |
| `mes/services/material_flow_service.py` | `MaterialReturnService` | `material_return` |
| `mes/services/material_flow_service.py` | `ProductionReceiptService` | `production_receipt` |
| `mes/services/mes_support_service.py` | `TraceService` | `trace` |
| `mes/services/mes_support_service.py` | `DashboardService` | `dashboard` |
| `mes/services/mes_support_service.py` | `BarcodeService` | `barcode` |
| `mes/services/mes_support_service.py` | `ShiftService` | `shift` |
| `mes/services/mes_support_service.py` | `ExceptionService` | `exception` |
| `mes/services/mes_support_service.py` | `ToolingService` | `tooling` |
| `mes/services/mes_support_service.py` | `EnergyService` | `energy` |
| `mes/services/production_report_service.py` | `ProductionReportService` | `production_report` |
| `mes/services/production_service.py` | `ManufacturingOrderService` | `manufacturing_order` |
| `mes/services/production_service.py` | `WorkOrderService` | `work_order` |

---

## 十、mrp2 插件

| 文件 | 类名 | model |
|------|------|-------|
| `mrp2/services/mrp_service.py` | `SalesForecastService` | `sales_forecast` |
| `mrp2/services/mrp_service.py` | `MpsService` | `mps` |
| `mrp2/services/mrp_service.py` | `MrpService` | `mrp` |
| `mrp2/services/mrp_service.py` | `CrpService` | `crp` |
| `mrp2/services/mrp_service.py` | `MonitorService` | `monitor` |
| `mrp2/services/mrp_service.py` | `AlertService` | `alert` |
| `mrp2/services/planned_order_service.py` | `PlannedOrderService` | `planned_order` |

---

## 十一、product 插件

| 文件 | 类名 | model |
|------|------|-------|
| `product/services/product_service.py` | `ProductService` | `product` |

---

## 十二、purchase 插件

| 文件 | 类名 | model |
|------|------|-------|
| `purchase/services/purchase_service.py` | `SupplierService` | `supplier` |
| `purchase/services/purchase_service.py` | `PurchaseOrderService` | `purchase_order` |
| `purchase/services/purchase_service.py` | `PurchaseReceiptService` | `purchase_receipt` |

---

## 十三、quality 插件

| 文件 | 类名 | model |
|------|------|-------|
| `quality/services/quality_service.py` | `QualityInspectionService` | `quality_inspection` |
| `quality/services/quality_service.py` | `InspectionStandardService` | `inspection_standard` |

---

## 十四、sales 插件

| 文件 | 类名 | model |
|------|------|-------|
| `sales/services/order_service.py` | `OrderService` | `order` |
| `sales/services/sales_service.py` | `SalesService` | `sales` |

---

## 十五、subcontracting 插件

| 文件 | 类名 | model |
|------|------|-------|
| `subcontracting/services/subcontracting_issue_service.py` | `SubcontractingIssueService` | `subcontracting_issue` |
| `subcontracting/services/subcontracting_order_service.py` | `SubcontractingOrderService` | `subcontracting_order` |
| `subcontracting/services/subcontracting_receipt_service.py` | `SubcontractingReceiptService` | `subcontracting_receipt` |
| `subcontracting/services/subcontracting_settlement_service.py` | `SubcontractingSettlementService` | `subcontracting_settlement` |
| `subcontracting/services/subcontracting_transit_service.py` | `SubcontractingTransitService` | `subcontracting_transit` |

---

## 十六、thirdparty 插件

| 文件 | 类名 | model |
|------|------|-------|
| `thirdparty/services/agent_service.py` | `AgentService` | `agent` |
| `thirdparty/services/platform_service.py` | `PlatformService` | `platform` |

---

## 汇总

| 插件 | service 类数 |
|------|-------------|
| agent | 15 |
| audit | 12 |
| crm | 7 |
| customer | 4 |
| equipment | 3 |
| finance | 7 |
| inventory | 10 |
| mes | 19 |
| mrp2 | 7 |
| product | 1 |
| purchase | 3 |
| quality | 2 |
| sales | 2 |
| subcontracting | 5 |
| thirdparty | 2 |
| **合计** | **99** |

> 审批模块（approval）自身不注册业务 model，仅提供框架层能力。
> `wechat_pay`、`qixiang_pay`、`alipay`、`llm` 插件无 service 文件或仅有辅助类，不在此列。
