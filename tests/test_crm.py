import sys
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, r'D:\Programs\fastapi\aipaneladmin')

from tortoise import Tortoise
from base.common.setting import settings
from base.plugins.crm.models.lead import Lead, LeadStatus
from base.plugins.crm.models.opportunity import Opportunity, OpportunityStatus
from base.plugins.crm.models.opportunity_stage import OpportunityStage
from base.plugins.crm.models.stage_change_log import StageChangeLog
from base.plugins.crm.models.activity import Activity, ActivityType
from base.plugins.crm.models.contact import Contact
from base.plugins.crm.models.follow_up_task import FollowUpTask, TaskStatus
from base.plugins.crm.models.lead_source import LeadSource
from base.plugins.crm.models.crm_config import CrmConfig
from base.plugins.crm.schemas.lead_schema import LeadCreate, LeadUpdate, LeadListQuery
from base.plugins.crm.schemas.opportunity_schema import OpportunityCreate, OpportunityAdvanceRequest, OpportunityWinRequest, OpportunityLoseRequest
from base.plugins.crm.schemas.activity_schema import ActivityCreate
from base.plugins.crm.schemas.contact_schema import ContactCreate
from base.plugins.crm.schemas.task_schema import FollowUpTaskCreate, TaskCompleteRequest
from base.plugins.crm.services.lead_service import LeadService
from base.plugins.crm.services.opportunity_service import OpportunityService
from base.plugins.crm.services.activity_service import ActivityService
from base.plugins.crm.services.contact_service import ContactService
from base.plugins.crm.services.follow_up_task_service import FollowUpTaskService
from base.plugins.crm.services.crm_config_service import CrmConfigService
from base.plugins.crm.services.crm_stats_service import CrmStatsService
from base.plugins.crm.services.crm_data_filter import get_crm_data_filter
from base.plugins.crm.services.crm_scheduler_service import CrmSchedulerService

passed = 0
failed = 0


async def test(name, func):
    global passed, failed
    try:
        await func()
        print(f"  PASS: {name}")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {name} - {e}")
        failed += 1


async def run_tests():
    await Tortoise.init(config=settings.TORTOISE_ORM)

    # Clean test data
    await Activity.all().delete()
    await StageChangeLog.all().delete()
    await FollowUpTask.all().delete()
    await Opportunity.all().delete()
    await Contact.all().delete()
    await Lead.all().delete()

    USER_ID = 1

    print("\n=== 1. Config Service Tests ===")
    await test("get_stages", lambda: CrmConfigService.get_stages())
    stages = await CrmConfigService.get_stages()
    assert len(stages) == 6, f"Expected 6 stages, got {len(stages)}"
    print(f"  INFO: {len(stages)} stages loaded")

    await test("get_lead_sources", lambda: CrmConfigService.get_lead_sources())
    sources = await CrmConfigService.get_lead_sources()
    assert len(sources) == 5, f"Expected 5 sources, got {len(sources)}"

    await test("get_settings", lambda: CrmConfigService.get_settings())
    settings_data = await CrmConfigService.get_settings()
    assert settings_data.auto_recycle_days == 30
    assert settings_data.stale_warning_days == 14

    print("\n=== 2. Lead Service Tests ===")

    async def test_create_lead():
        data = LeadCreate(name="张三", phone="13800138001", company="测试公司", source="website")
        lead = await LeadService.create_lead(data, USER_ID)
        assert lead.id is not None
        assert lead.status == LeadStatus.NEW
        assert lead.name == "张三"

    await test("create_lead", test_create_lead)

    async def test_duplicate_lead():
        data = LeadCreate(name="张三2", phone="13800138001", source="website")
        try:
            await LeadService.create_lead(data, USER_ID)
            raise AssertionError("Should have raised duplicate error")
        except ValueError as e:
            assert "DUPLICATE" in str(e)

    await test("duplicate_lead_rejected", test_duplicate_lead)

    async def test_get_lead_list():
        query = LeadListQuery(page=1, page_size=10)
        leads, total = await LeadService.get_lead_list(query, USER_ID)
        assert total >= 1
        assert len(leads) >= 1

    await test("get_lead_list", test_get_lead_list)

    async def test_update_lead():
        lead = await Lead.filter(phone="13800138001").first()
        data = LeadUpdate(company="新公司")
        updated = await LeadService.update_lead(lead.id, data)
        assert updated.company == "新公司"

    await test("update_lead", test_update_lead)

    async def test_assign_lead():
        lead = await Lead.filter(phone="13800138001").first()
        assigned = await LeadService.assign_lead(lead.id, USER_ID)
        assert assigned.assigned_to == USER_ID

    await test("assign_lead", test_assign_lead)

    print("\n=== 3. Activity + Lead Status Transition Tests ===")

    async def test_create_activity_auto_contacted():
        lead = await Lead.filter(phone="13800138001").first()
        assert lead.status == LeadStatus.NEW
        data = ActivityCreate(
            type="call", subject="首次电话沟通",
            activity_time=datetime.now(), lead_id=lead.id
        )
        activity = await ActivityService.create_activity(data, USER_ID)
        assert activity.id is not None
        lead_refreshed = await Lead.get_or_none(id=lead.id)
        assert lead_refreshed.status == LeadStatus.CONTACTED

    await test("create_activity_auto_contacted", test_create_activity_auto_contacted)

    print("\n=== 4. Lead Convert Tests ===")

    async def test_convert_lead():
        lead = await Lead.filter(phone="13800138001").first()
        assert lead.status == LeadStatus.CONTACTED
        converted = await LeadService.convert_lead(lead.id, USER_ID)
        assert converted.status == LeadStatus.CONVERTED
        assert converted.customer_id is not None

    await test("convert_lead", test_convert_lead)

    async def test_convert_new_lead_fails():
        data = LeadCreate(name="李四", phone="13800138002", source="referral")
        lead = await LeadService.create_lead(data, USER_ID)
        try:
            await LeadService.convert_lead(lead.id, USER_ID)
            raise AssertionError("Should fail - lead not contacted")
        except ValueError as e:
            assert "STATUS_ERROR" in str(e)

    await test("convert_new_lead_fails", test_convert_new_lead_fails)

    async def test_delete_converted_lead_fails():
        lead = await Lead.filter(phone="13800138001").first()
        try:
            await LeadService.delete_lead(lead.id)
            raise AssertionError("Should fail - converted lead")
        except ValueError as e:
            assert "CONVERTED" in str(e)

    await test("delete_converted_lead_fails", test_delete_converted_lead_fails)

    print("\n=== 5. Opportunity Service Tests ===")

    lead = await Lead.filter(phone="13800138001").first()
    customer_id = lead.customer_id if lead and lead.customer_id else 1

    async def test_create_opportunity():
        data = OpportunityCreate(
            name="测试商机", customer_id=customer_id,
            stage="initial_contact", expected_amount=Decimal("50000"),
            assigned_to=USER_ID
        )
        opp = await OpportunityService.create_opportunity(data, USER_ID)
        assert opp.id is not None
        assert opp.status == OpportunityStatus.ACTIVE
        assert opp.stage == "initial_contact"

    await test("create_opportunity", test_create_opportunity)

    opp = await Opportunity.filter(name="测试商机").first()

    async def test_advance_stage():
        data = OpportunityAdvanceRequest(to_stage="requirement_confirmation", remark="推进到需求确认")
        updated = await OpportunityService.advance_stage(opp.id, data, USER_ID)
        assert updated.stage == "requirement_confirmation"
        log = await StageChangeLog.filter(opportunity_id=opp.id).first()
        assert log.from_stage == "initial_contact"
        assert log.to_stage == "requirement_confirmation"

    await test("advance_stage", test_advance_stage)

    async def test_rollback_stage_fails():
        data = OpportunityAdvanceRequest(to_stage="initial_contact")
        try:
            await OpportunityService.advance_stage(opp.id, data, USER_ID)
            raise AssertionError("Should fail - rollback not allowed")
        except ValueError as e:
            assert "ROLLBACK" in str(e)

    await test("rollback_stage_fails", test_rollback_stage_fails)

    async def test_mark_won():
        win_data = OpportunityWinRequest(actual_amount=Decimal("45000"), create_order=False)
        won = await OpportunityService.mark_won(opp.id, win_data, USER_ID)
        assert won.status == OpportunityStatus.WON
        assert won.actual_amount == Decimal("45000")
        assert won.won_at is not None

    await test("mark_won", test_mark_won)

    async def test_delete_won_opp_fails():
        try:
            await OpportunityService.delete_opportunity(opp.id)
            raise AssertionError("Should fail - won opp")
        except ValueError as e:
            assert "CLOSED" in str(e)

    await test("delete_won_opp_fails", test_delete_won_opp_fails)

    print("\n=== 6. Opportunity Lose Tests ===")

    async def test_create_and_lose_opportunity():
        data = OpportunityCreate(
            name="输单商机", customer_id=customer_id,
            stage="initial_contact", expected_amount=Decimal("30000"),
            assigned_to=USER_ID
        )
        opp2 = await OpportunityService.create_opportunity(data, USER_ID)
        lose_data = OpportunityLoseRequest(lost_reason="客户预算不足")
        lost = await OpportunityService.mark_lost(opp2.id, lose_data, USER_ID)
        assert lost.status == OpportunityStatus.LOST
        assert lost.lost_reason == "客户预算不足"

    await test("create_and_lose_opportunity", test_create_and_lose_opportunity)

    print("\n=== 7. Kanban View Tests ===")

    async def test_kanban_view():
        kanban = await OpportunityService.get_kanban_view(USER_ID)
        assert isinstance(kanban, list)
        assert len(kanban) > 0
        for item in kanban:
            assert "stage_code" in item
            assert "stage_name" in item
            assert "opportunities" in item

    await test("kanban_view", test_kanban_view)

    print("\n=== 8. Contact Service Tests ===")

    async def test_create_contact():
        data = ContactCreate(
            customer_id=customer_id, name="王五",
            phone="13900139001", position="技术总监", is_primary=True
        )
        contact = await ContactService.create_contact(data)
        assert contact.id is not None
        assert contact.is_primary is True

    await test("create_contact", test_create_contact)

    async def test_duplicate_contact():
        data = ContactCreate(
            customer_id=customer_id, name="王五2",
            phone="13900139001"
        )
        try:
            await ContactService.create_contact(data)
            raise AssertionError("Should fail - duplicate phone")
        except ValueError as e:
            assert "DUPLICATE" in str(e)

    await test("duplicate_contact_rejected", test_duplicate_contact)

    contact = await Contact.filter(phone="13900139001").first()

    async def test_set_primary():
        data = ContactCreate(
            customer_id=customer_id, name="赵六",
            phone="13900139002", is_primary=True
        )
        new_contact = await ContactService.create_contact(data)
        refreshed = await ContactService.set_primary(new_contact.id)
        assert refreshed.is_primary is True
        old_contact = await Contact.get_or_none(id=contact.id)
        assert old_contact.is_primary is False

    await test("set_primary", test_set_primary)

    print("\n=== 9. FollowUpTask Service Tests ===")

    async def test_create_task():
        lead_for_task = await Lead.filter(phone="13800138002").first()
        data = FollowUpTaskCreate(
            title="跟进李四", assigned_to=USER_ID,
            due_date=datetime.now() + timedelta(days=3),
            lead_id=lead_for_task.id
        )
        task = await FollowUpTaskService.create_task(data, USER_ID)
        assert task.id is not None
        assert task.status == TaskStatus.TODO

    await test("create_task", test_create_task)

    async def test_complete_task():
        task = await FollowUpTask.filter(title="跟进李四").first()
        complete_data = TaskCompleteRequest(create_activity=True, activity_content="已完成跟进")
        completed = await FollowUpTaskService.complete_task(task.id, complete_data, USER_ID)
        assert completed.status == TaskStatus.COMPLETED
        assert completed.completed_at is not None
        activity = await Activity.filter(lead_id=task.lead_id, subject__icontains="完成").first()
        assert activity is not None

    await test("complete_task_with_activity", test_complete_task)

    async def test_get_my_tasks():
        tasks = await FollowUpTaskService.get_my_tasks(USER_ID)
        assert isinstance(tasks, list)

    await test("get_my_tasks", test_get_my_tasks)

    print("\n=== 10. Stats Service Tests ===")

    async def test_funnel_stats():
        stats = await CrmStatsService.get_funnel_stats(USER_ID)
        assert stats.total_opportunities >= 0
        assert len(stats.stages) > 0

    await test("funnel_stats", test_funnel_stats)

    async def test_lead_source_stats():
        stats = await CrmStatsService.get_lead_source_stats(USER_ID)
        assert len(stats.sources) > 0

    await test("lead_source_stats", test_lead_source_stats)

    async def test_sales_performance():
        stats = await CrmStatsService.get_sales_performance(USER_ID)
        assert isinstance(stats.performances, list)

    await test("sales_performance", test_sales_performance)

    print("\n=== 11. Data Filter Tests ===")

    async def test_data_filter_admin():
        data_filter = await get_crm_data_filter(USER_ID)
        assert isinstance(data_filter, dict)

    await test("data_filter", test_data_filter_admin)

    print("\n=== 12. Scheduler Service Tests ===")

    async def test_auto_recycle():
        count = await CrmSchedulerService.auto_recycle_leads()
        assert isinstance(count, int)

    await test("auto_recycle_leads", test_auto_recycle)

    async def test_mark_overdue_tasks():
        count = await CrmSchedulerService.mark_overdue_tasks()
        assert isinstance(count, int)

    await test("mark_overdue_tasks", test_mark_overdue_tasks)

    await Tortoise.close_connections()

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")


asyncio.run(run_tests())