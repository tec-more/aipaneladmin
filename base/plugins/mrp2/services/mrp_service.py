from typing import Optional, List, Tuple, Dict, Any
from decimal import Decimal
from datetime import datetime, date, timedelta

try:
    from base.plugins.mrp2.models.mrp_models import (
        SalesForecast, SalesForecastDetail,
        MasterProductionSchedule, MPSDetail,
        MRPCalculation, MRPResultDetail,
        CapacityRequirementPlan, CRPDetail,
        PlanExecutionMonitor, MRPExceptionAlert
    )
    from base.plugins.mrp2.schemas.mrp_schema import (
        SalesForecastCreate, SalesForecastUpdate,
        MPSCreate, MPSUpdate,
        MRPCalculationCreate,
        CRPCreate,
        MonitorCreate,
        AlertCreate,
        MRPCalculateRequest,
        CRPCalculateRequest
    )
    try:
        from base.plugins.mes.models.base_data import Bom, WorkCenter, Route, RouteProcess
        MES_AVAILABLE = True
    except ImportError:
        Bom = None
        WorkCenter = None
        Route = None
        RouteProcess = None
        MES_AVAILABLE = False
except ImportError:
    from typing import Any
    from datetime import datetime
    from decimal import Decimal

    class BaseModelMock:
        id = 1
        created_at = datetime.now()
        updated_at = datetime.now()

        async def save(self):
            pass

        async def update_from_dict(self, data):
            for key, value in data.items():
                setattr(self, key, value)
            return self

    class SalesForecast(BaseModelMock):
        def __init__(self, **kwargs):
            super().__init__()
            for key, value in kwargs.items():
                setattr(self, key, value)

        @classmethod
        async def create(cls, **kwargs):
            return cls(**kwargs)

        @classmethod
        async def filter(cls, **kwargs):
            class MockQuerySet:
                async def first(self): return None
                async def exists(self): return False
                async def delete(self): return 0
                async def count(self): return 0
                async def offset(self, n): return self
                async def limit(self, n): return self
                async def order_by(self, order): return self
                def filter(self, **kwargs): return self
                def exclude(self, **kwargs): return self
                def all(self): return []
                def distinct(self): return self
            return MockQuerySet()

        async def to_dict(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    class SalesForecastDetail(SalesForecast): pass
    class MasterProductionSchedule(SalesForecast): pass
    class MPSDetail(SalesForecast): pass
    class MRPCalculation(SalesForecast): pass
    class MRPResultDetail(SalesForecast): pass
    class CapacityRequirementPlan(SalesForecast): pass
    class CRPDetail(SalesForecast): pass
    class PlanExecutionMonitor(SalesForecast): pass
    class MRPExceptionAlert(SalesForecast): pass

    class SalesForecastCreate:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class SalesForecastUpdate(SalesForecastCreate):
        def model_dump(self, exclude_none=False):
            return {k: v for k, v in self.__dict__.items() if v is not None}

    class MPSCreate(SalesForecastCreate): pass
    class MPSUpdate(SalesForecastUpdate): pass
    class MRPCalculationCreate(SalesForecastCreate): pass
    class CRPCreate(SalesForecastCreate): pass
    class MonitorCreate(SalesForecastCreate): pass
    class AlertCreate(SalesForecastCreate): pass

    MES_AVAILABLE = False


class SalesForecastService:
    @staticmethod
    async def get_by_id(forecast_id: int) -> Optional[SalesForecast]:
        return await SalesForecast.filter(id=forecast_id).first()

    @staticmethod
    async def get_by_code(forecast_code: str) -> Optional[SalesForecast]:
        return await SalesForecast.filter(forecast_code=forecast_code).first()

    @staticmethod
    async def create_forecast(data: SalesForecastCreate) -> SalesForecast:
        if await SalesForecastService.check_code_exists(data.forecast_code):
            raise ValueError("预测编号已存在")
        return await SalesForecast.create(**data.__dict__)

    @staticmethod
    async def update_forecast(forecast_id: int, data: SalesForecastUpdate) -> Optional[SalesForecast]:
        forecast = await SalesForecast.filter(id=forecast_id).first()
        if not forecast:
            return None
        if data.forecast_code and data.forecast_code != forecast.forecast_code:
            if await SalesForecastService.check_code_exists(data.forecast_code, exclude_id=forecast_id):
                raise ValueError("预测编号已被使用")
        update_data = data.model_dump(exclude_none=True)
        await forecast.update_from_dict(update_data).save()
        return forecast

    @staticmethod
    async def delete_forecast(forecast_id: int) -> bool:
        await SalesForecastDetail.filter(forecast_id=forecast_id).delete()
        deleted_count = await SalesForecast.filter(id=forecast_id).delete()
        return deleted_count > 0

    @staticmethod
    async def get_list(
        page: int = 1, page_size: int = 10,
        forecast_code: Optional[str] = None,
        forecast_name: Optional[str] = None,
        forecast_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Tuple[List[SalesForecast], int]:
        query = SalesForecast.all()
        if forecast_code:
            query = query.filter(forecast_code__icontains=forecast_code)
        if forecast_name:
            query = query.filter(forecast_name__icontains=forecast_name)
        if forecast_type:
            query = query.filter(forecast_type=forecast_type)
        if status:
            query = query.filter(status=status)
        if start_date:
            query = query.filter(start_date__gte=start_date)
        if end_date:
            query = query.filter(end_date__lte=end_date)
        total = await query.count()
        offset = (page - 1) * page_size
        items = await query.offset(offset).limit(page_size).order_by('-created_at')
        return items, total

    @staticmethod
    async def check_code_exists(code: str, exclude_id: Optional[int] = None) -> bool:
        query = SalesForecast.filter(forecast_code=code)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    @staticmethod
    async def get_forecast_details(forecast_id: int) -> List[SalesForecastDetail]:
        forecast = await SalesForecastService.get_by_id(forecast_id)
        if not forecast:
            return []
        return await SalesForecastDetail.filter(forecast_id=forecast_id).order_by('period_start', 'product_code')

    @staticmethod
    async def create_forecast_detail(data: dict) -> SalesForecastDetail:
        forecast = await SalesForecastService.get_by_id(data.get('forecast_id'))
        if not forecast:
            raise ValueError("预测不存在")
        data['forecast_code'] = forecast.forecast_code
        return await SalesForecastDetail.create(**data)

    @staticmethod
    async def update_forecast_detail(detail_id: int, data: dict) -> Optional[SalesForecastDetail]:
        detail = await SalesForecastDetail.filter(id=detail_id).first()
        if not detail:
            return None
        update_data = {k: v for k, v in data.items() if v is not None}
        await detail.update_from_dict(update_data).save()
        return detail

    @staticmethod
    async def delete_forecast_detail(detail_id: int) -> bool:
        deleted_count = await SalesForecastDetail.filter(id=detail_id).delete()
        return deleted_count > 0

    @staticmethod
    async def submit_for_review(forecast_id: int) -> Optional[SalesForecast]:
        forecast = await SalesForecastService.get_by_id(forecast_id)
        if not forecast:
            return None
        if forecast.status != "draft":
            raise ValueError("只能提交草稿状态的预测")
        forecast.status = "review"
        await forecast.save()
        return forecast

    @staticmethod
    async def approve_forecast(forecast_id: int) -> Optional[SalesForecast]:
        forecast = await SalesForecastService.get_by_id(forecast_id)
        if not forecast:
            return None
        if forecast.status != "review":
            raise ValueError("只能审批审核中的预测")
        forecast.status = "approved"
        await forecast.save()
        return forecast

    @staticmethod
    async def reject_forecast(forecast_id: int) -> Optional[SalesForecast]:
        forecast = await SalesForecastService.get_by_id(forecast_id)
        if not forecast:
            return None
        if forecast.status != "review":
            raise ValueError("只能驳回审核中的预测")
        forecast.status = "draft"
        await forecast.save()
        return forecast

    @staticmethod
    async def generate_from_history(product_code: str, months: int = 6) -> Dict[str, Any]:
        result = []
        today = date.today()
        for i in range(months, 0, -1):
            month_start = date(today.year, today.month - i, 1)
            if month_start.month == 12:
                month_end = date(today.year - i + 1, 12, 31)
            else:
                next_month = month_start.replace(month=month_start.month + 1)
                month_end = next_month - timedelta(days=1)
            result.append({
                "period_start": month_start,
                "period_end": month_end,
                "forecast_quantity": 0,
                "unit": "件",
                "confidence": 70
            })
        return {"product_code": product_code, "historical_data": result}


class MPSService:
    @staticmethod
    async def get_by_id(mps_id: int) -> Optional[MasterProductionSchedule]:
        return await MasterProductionSchedule.filter(id=mps_id).first()

    @staticmethod
    async def get_by_code(mps_code: str) -> Optional[MasterProductionSchedule]:
        return await MasterProductionSchedule.filter(mps_code=mps_code).first()

    @staticmethod
    async def create_mps(data: MPSCreate) -> MasterProductionSchedule:
        if await MPSService.check_code_exists(data.mps_code):
            raise ValueError("MPS编号已存在")
        return await MasterProductionSchedule.create(**data.__dict__)

    @staticmethod
    async def update_mps(mps_id: int, data: MPSUpdate) -> Optional[MasterProductionSchedule]:
        mps = await MasterProductionSchedule.filter(id=mps_id).first()
        if not mps:
            return None
        if data.mps_code and data.mps_code != mps.mps_code:
            if await MPSService.check_code_exists(data.mps_code, exclude_id=mps_id):
                raise ValueError("MPS编号已被使用")
        update_data = data.model_dump(exclude_none=True)
        old_code = mps.mps_code
        await mps.update_from_dict(update_data).save()
        if 'mps_code' in update_data and update_data['mps_code'] != old_code:
            await MPSDetail.filter(mps_code=old_code).update(mps_code=update_data['mps_code'])
        return mps

    @staticmethod
    async def delete_mps(mps_id: int) -> bool:
        mps = await MPSService.get_by_id(mps_id)
        if not mps:
            return False
        await MPSDetail.filter(mps_id=mps_id).delete()
        await MRPCalculation.filter(mps_id=mps_id).delete()
        await CapacityRequirementPlan.filter(mps_id=mps_id).delete()
        await PlanExecutionMonitor.filter(mps_id=mps_id).delete()
        await MasterProductionSchedule.filter(id=mps_id).delete()
        return True

    @staticmethod
    async def get_list(
        page: int = 1, page_size: int = 10,
        mps_code: Optional[str] = None,
        mps_name: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Tuple[List[MasterProductionSchedule], int]:
        query = MasterProductionSchedule.all()
        if mps_code:
            query = query.filter(mps_code__icontains=mps_code)
        if mps_name:
            query = query.filter(mps_name__icontains=mps_name)
        if status:
            query = query.filter(status=status)
        if start_date:
            query = query.filter(start_date__gte=start_date)
        if end_date:
            query = query.filter(end_date__lte=end_date)
        total = await query.count()
        offset = (page - 1) * page_size
        items = await query.offset(offset).limit(page_size).order_by('-created_at')
        return items, total

    @staticmethod
    async def check_code_exists(code: str, exclude_id: Optional[int] = None) -> bool:
        query = MasterProductionSchedule.filter(mps_code=code)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    @staticmethod
    async def get_mps_details(mps_id: int) -> List[MPSDetail]:
        mps = await MPSService.get_by_id(mps_id)
        if not mps:
            return []
        return await MPSDetail.filter(mps_id=mps_id).order_by('period_start', 'product_code')

    @staticmethod
    async def create_mps_detail(data: dict) -> MPSDetail:
        mps = await MPSService.get_by_id(data.get('mps_id'))
        if not mps:
            raise ValueError("MPS不存在")
        data['mps_code'] = mps.mps_code
        data['planned_inventory'] = data.get('planned_quantity', 0) - data.get('production_quantity', 0)
        return await MPSDetail.create(**data)

    @staticmethod
    async def update_mps_detail(detail_id: int, data: dict) -> Optional[MPSDetail]:
        detail = await MPSDetail.filter(id=detail_id).first()
        if not detail:
            return None
        update_data = {k: v for k, v in data.items() if v is not None}
        if 'planned_quantity' in update_data or 'production_quantity' in update_data:
            planned_qty = update_data.get('planned_quantity', detail.planned_quantity)
            prod_qty = update_data.get('production_quantity', detail.production_quantity)
            update_data['planned_inventory'] = planned_qty - prod_qty
        await detail.update_from_dict(update_data).save()
        return detail

    @staticmethod
    async def delete_mps_detail(detail_id: int) -> bool:
        deleted_count = await MPSDetail.filter(id=detail_id).delete()
        return deleted_count > 0

    @staticmethod
    async def submit_for_review(mps_id: int) -> Optional[MasterProductionSchedule]:
        mps = await MPSService.get_by_id(mps_id)
        if not mps:
            return None
        if mps.status != "draft":
            raise ValueError("只能提交草稿状态的MPS")
        mps.status = "review"
        await mps.save()
        return mps

    @staticmethod
    async def approve_mps(mps_id: int) -> Optional[MasterProductionSchedule]:
        mps = await MPSService.get_by_id(mps_id)
        if not mps:
            return None
        if mps.status != "review":
            raise ValueError("只能审批审核中的MPS")
        mps.status = "approved"
        await mps.save()
        return mps

    @staticmethod
    async def release_mps(mps_id: int) -> Optional[MasterProductionSchedule]:
        mps = await MPSService.get_by_id(mps_id)
        if not mps:
            return None
        if mps.status != "approved":
            raise ValueError("只能发布已审批的MPS")
        mps.status = "released"
        await mps.save()
        return mps

    @staticmethod
    async def generate_from_forecast(forecast_id: int) -> Dict[str, Any]:
        forecast = await SalesForecastService.get_by_id(forecast_id)
        if not forecast:
            raise ValueError("销售预测不存在")
        if forecast.status != "approved":
            raise ValueError("只能基于已审批的销售预测生成MPS")

        details = await SalesForecastService.get_forecast_details(forecast_id)
        mps_details = []
        for detail in details:
            mps_details.append({
                "product_id": detail.product_id,
                "product_code": detail.product_code,
                "product_name": detail.product_name,
                "period_start": detail.period_start,
                "period_end": detail.period_end,
                "forecast_quantity": detail.forecast_quantity,
                "planned_quantity": detail.forecast_quantity,
                "unit": detail.unit,
                "safety_stock": 0
            })
        return {
            "forecast_id": forecast_id,
            "forecast_code": forecast.forecast_code,
            "start_date": forecast.start_date,
            "end_date": forecast.end_date,
            "details": mps_details
        }


class MRPService:
    @staticmethod
    async def get_by_id(mrp_id: int) -> Optional[MRPCalculation]:
        return await MRPCalculation.filter(id=mrp_id).first()

    @staticmethod
    async def get_by_code(mrp_code: str) -> Optional[MRPCalculation]:
        return await MRPCalculation.filter(mrp_code=mrp_code).first()

    @staticmethod
    async def create_mrp(data: MRPCalculationCreate) -> MRPCalculation:
        if await MRPService.check_code_exists(data.mrp_code):
            raise ValueError("MRP编号已存在")
        data_dict = data.__dict__.copy()
        data_dict['calculation_date'] = datetime.now()
        return await MRPCalculation.create(**data_dict)

    @staticmethod
    async def delete_mrp(mrp_id: int) -> bool:
        mrp = await MRPService.get_by_id(mrp_id)
        if not mrp:
            return False
        await MRPResultDetail.filter(mrp_id=mrp_id).delete()
        await CapacityRequirementPlan.filter(mrp_id=mrp_id).delete()
        await MRPCalculation.filter(id=mrp_id).delete()
        return True

    @staticmethod
    async def get_list(
        page: int = 1, page_size: int = 10,
        mrp_code: Optional[str] = None,
        mrp_name: Optional[str] = None,
        status: Optional[str] = None,
        mps_code: Optional[str] = None
    ) -> Tuple[List[MRPCalculation], int]:
        query = MRPCalculation.all()
        if mrp_code:
            query = query.filter(mrp_code__icontains=mrp_code)
        if mrp_name:
            query = query.filter(mrp_name__icontains=mrp_name)
        if status:
            query = query.filter(status=status)
        if mps_code:
            query = query.filter(mps_code=mps_code)
        total = await query.count()
        offset = (page - 1) * page_size
        items = await query.offset(offset).limit(page_size).order_by('-created_at')
        return items, total

    @staticmethod
    async def check_code_exists(code: str, exclude_id: Optional[int] = None) -> bool:
        query = MRPCalculation.filter(mrp_code=code)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    @staticmethod
    async def get_mrp_details(mrp_id: int) -> List[MRPResultDetail]:
        mrp = await MRPService.get_by_id(mrp_id)
        if not mrp:
            return []
        return await MRPResultDetail.filter(mrp_id=mrp_id).order_by('level', 'product_code', 'period_start')

    @staticmethod
    async def calculate_mrp(request: MRPCalculateRequest) -> MRPCalculation:
        mps = None
        if request.mps_id:
            mps = await MPSService.get_by_id(request.mps_id)
        elif request.mps_code:
            mps = await MPSService.get_by_code(request.mps_code)

        if not mps:
            raise ValueError("MPS不存在")

        mrp_code = f"MRP{datetime.now().strftime('%Y%m%d%H%M%S')}"
        mrp = await MRPCalculation.create(
            mrp_code=mrp_code,
            mrp_name=f"MRP计算_{mps.mps_code}",
            mps_id=mps.id,
            mps_code=mps.mps_code,
            calculation_date=datetime.now(),
            status="calculating",
            start_date=request.start_date or mps.start_date,
            end_date=request.end_date or mps.end_date,
            net_requirement_only=request.net_requirement_only,
            include_safety_stock=request.include_safety_stock,
            include_wip=request.include_wip
        )

        try:
            mps_details = await MPSService.get_mps_details(mps.id)
            results = []
            total_items = 0
            unique_materials = 0

            if MES_AVAILABLE and Bom is not None:
                for detail in mps_details:
                    flattened_bom = await MRPService._get_flattened_bom(
                        detail.product_code,
                        detail.planned_quantity,
                        detail.period_start,
                        detail.period_end,
                        mrp.id,
                        mrp_code
                    )
                    results.extend(flattened_bom)

            for result in results:
                await MRPResultDetail.create(**result)

            total_items = len(results)
            material_codes = set(r['product_code'] for r in results)
            unique_materials = len(material_codes)

            calculation_result = {
                "total_items": total_items,
                "unique_materials": unique_materials,
                "mps_code": mps.mps_code,
                "start_date": str(request.start_date or mps.start_date),
                "end_date": str(request.end_date or mps.end_date)
            }

            mrp.status = "complete"
            mrp.calculation_result = calculation_result
            await mrp.save()

        except Exception as e:
            mrp.status = "failed"
            mrp.error_message = str(e)
            await mrp.save()
            raise

        return mrp

    @staticmethod
    async def _get_flattened_bom(
        product_code: str,
        quantity: Decimal,
        period_start: date,
        period_end: date,
        mrp_id: int,
        mrp_code: str,
        level: int = 1,
        parent_item_code: Optional[str] = None,
        max_level: int = 10
    ) -> List[Dict[str, Any]]:
        if level > max_level:
            return []

        results = []
        boms = await Bom.filter(product_code=product_code, is_active=True).order_by('level')

        for bom in boms:
            bom_qty = bom.quantity * quantity
            scrap_qty = bom_qty * bom.scrap_rate
            total_qty = bom_qty + scrap_qty

            result_item = {
                "mrp_id": mrp_id,
                "mrp_code": mrp_code,
                "level": level,
                "product_id": bom.item_id,
                "product_code": bom.item_code,
                "product_name": bom.item_name,
                "period_start": period_start,
                "period_end": period_end,
                "gross_requirement": total_qty,
                "scheduled_receipts": Decimal("0"),
                "projected_available": Decimal("0"),
                "net_requirement": total_qty,
                "planned_order_receipt": total_qty,
                "planned_order_release": total_qty,
                "lot_size": Decimal("1"),
                "lead_time": 7,
                "safety_stock": Decimal("0"),
                "unit": bom.unit,
                "parent_item_code": parent_item_code or product_code,
                "bom_quantity": bom.quantity
            }

            results.append(result_item)

            children = await MRPService._get_flattened_bom(
                bom.item_code,
                total_qty,
                period_start,
                period_end,
                mrp_id,
                mrp_code,
                level + 1,
                product_code,
                max_level
            )
            results.extend(children)

        return results


class CRPService:
    @staticmethod
    async def get_by_id(crp_id: int) -> Optional[CapacityRequirementPlan]:
        return await CapacityRequirementPlan.filter(id=crp_id).first()

    @staticmethod
    async def get_by_code(crp_code: str) -> Optional[CapacityRequirementPlan]:
        return await CapacityRequirementPlan.filter(crp_code=crp_code).first()

    @staticmethod
    async def create_crp(data: CRPCreate) -> CapacityRequirementPlan:
        if await CRPService.check_code_exists(data.crp_code):
            raise ValueError("CRP编号已存在")
        data_dict = data.__dict__.copy()
        data_dict['calculation_date'] = datetime.now()
        return await CapacityRequirementPlan.create(**data_dict)

    @staticmethod
    async def delete_crp(crp_id: int) -> bool:
        crp = await CRPService.get_by_id(crp_id)
        if not crp:
            return False
        await CRPDetail.filter(crp_id=crp_id).delete()
        await CapacityRequirementPlan.filter(id=crp_id).delete()
        return True

    @staticmethod
    async def get_list(
        page: int = 1, page_size: int = 10,
        crp_code: Optional[str] = None,
        crp_name: Optional[str] = None,
        status: Optional[str] = None
    ) -> Tuple[List[CapacityRequirementPlan], int]:
        query = CapacityRequirementPlan.all()
        if crp_code:
            query = query.filter(crp_code__icontains=crp_code)
        if crp_name:
            query = query.filter(crp_name__icontains=crp_name)
        if status:
            query = query.filter(status=status)
        total = await query.count()
        offset = (page - 1) * page_size
        items = await query.offset(offset).limit(page_size).order_by('-created_at')
        return items, total

    @staticmethod
    async def check_code_exists(code: str, exclude_id: Optional[int] = None) -> bool:
        query = CapacityRequirementPlan.filter(crp_code=code)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    @staticmethod
    async def get_crp_details(crp_id: int) -> List[CRPDetail]:
        crp = await CRPService.get_by_id(crp_id)
        if not crp:
            return []
        return await CRPDetail.filter(crp_id=crp_id).order_by('work_center_code', 'period_start')

    @staticmethod
    async def calculate_crp(request: CRPCalculateRequest) -> CapacityRequirementPlan:
        mrp = None
        if request.mrp_id:
            mrp = await MRPService.get_by_id(request.mrp_id)
        elif request.mrp_code:
            mrp = await MRPService.get_by_code(request.mrp_code)

        if not mrp:
            raise ValueError("MRP不存在")
        if mrp.status != "complete":
            raise ValueError("只能基于已完成的MRP计算CRP")

        crp_code = f"CRP{datetime.now().strftime('%Y%m%d%H%M%S')}"
        crp = await CapacityRequirementPlan.create(
            crp_code=crp_code,
            crp_name=f"CRP计算_{mrp.mrp_code}",
            mrp_id=mrp.id,
            mrp_code=mrp.mrp_code,
            mps_id=mrp.mps_id,
            mps_code=mrp.mps_code,
            status="calculating",
            start_date=request.start_date or mrp.start_date,
            end_date=request.end_date or mrp.end_date,
            calculation_date=datetime.now()
        )

        try:
            mrp_details = await MRPService.get_mrp_details(mrp.id)
            work_center_requirements = {}

            if MES_AVAILABLE and Route is not None and RouteProcess is not None and WorkCenter is not None:
                for detail in mrp_details:
                    route = await Route.filter(product_code=detail.product_code, is_active=True).first()
                    if route:
                        route_processes = await RouteProcess.filter(route_code=route.route_code).order_by('sequence')
                        for rp in route_processes:
                            wc_key = rp.work_center_code
                            if wc_key not in work_center_requirements:
                                wc = await WorkCenter.filter(work_center_code=wc_key).first()
                                work_center_requirements[wc_key] = {
                                    "work_center_code": wc_key,
                                    "work_center_name": wc.work_center_name if wc else wc_key,
                                    "required_capacity": Decimal("0"),
                                    "details": []
                                }
                            work_center_requirements[wc_key]["required_capacity"] += detail.planned_order_release * Decimal("0.5")

            bottleneck_wcs = []
            total_required = Decimal("0")
            total_available = Decimal("0")

            for wc_code, req in work_center_requirements.items():
                available_capacity = Decimal("480")
                utilization = (req["required_capacity"] / available_capacity) * 100 if available_capacity > 0 else 0
                is_overloaded = utilization > 100
                overload_hours = max(Decimal("0"), req["required_capacity"] - available_capacity)

                if is_overloaded:
                    bottleneck_wcs.append({
                        "work_center_code": wc_code,
                        "work_center_name": req["work_center_name"],
                        "utilization": float(utilization),
                        "overload_hours": float(overload_hours)
                    })

                crp_detail = await CRPDetail.create(
                    crp_id=crp.id,
                    crp_code=crp_code,
                    work_center_code=wc_code,
                    work_center_name=req["work_center_name"],
                    period_start=request.start_date or mrp.start_date,
                    period_end=request.end_date or mrp.end_date,
                    available_capacity=available_capacity,
                    required_capacity=req["required_capacity"],
                    capacity_utilization=utilization,
                    is_overloaded=is_overloaded,
                    overload_hours=overload_hours,
                    detail_items=req["details"]
                )

                total_required += req["required_capacity"]
                total_available += available_capacity

            overall_utilization = (total_required / total_available) * 100 if total_available > 0 else 0

            calculation_summary = {
                "total_work_centers": len(work_center_requirements),
                "bottleneck_count": len(bottleneck_wcs),
                "total_required_hours": float(total_required),
                "total_available_hours": float(total_available),
                "overall_utilization": float(overall_utilization)
            }

            crp.status = "complete"
            crp.overall_capacity_utilization = overall_utilization
            crp.bottleneck_work_centers = bottleneck_wcs
            crp.calculation_summary = calculation_summary
            await crp.save()

        except Exception as e:
            crp.status = "failed"
            crp.error_message = str(e)
            await crp.save()
            raise

        return crp


class MonitorService:
    @staticmethod
    async def get_by_id(monitor_id: int) -> Optional[PlanExecutionMonitor]:
        return await PlanExecutionMonitor.filter(id=monitor_id).first()

    @staticmethod
    async def get_by_code(monitor_code: str) -> Optional[PlanExecutionMonitor]:
        return await PlanExecutionMonitor.filter(monitor_code=monitor_code).first()

    @staticmethod
    async def create_monitor(data: MonitorCreate) -> PlanExecutionMonitor:
        if await MonitorService.check_code_exists(data.monitor_code):
            raise ValueError("监控编号已存在")
        return await PlanExecutionMonitor.create(**data.__dict__)

    @staticmethod
    async def update_monitor(monitor_id: int, data: dict) -> Optional[PlanExecutionMonitor]:
        monitor = await PlanExecutionMonitor.filter(id=monitor_id).first()
        if not monitor:
            return None
        update_data = {k: v for k, v in data.items() if v is not None}
        await monitor.update_from_dict(update_data).save()
        return monitor

    @staticmethod
    async def delete_monitor(monitor_id: int) -> bool:
        deleted_count = await PlanExecutionMonitor.filter(id=monitor_id).delete()
        return deleted_count > 0

    @staticmethod
    async def get_list(
        page: int = 1, page_size: int = 10,
        monitor_code: Optional[str] = None,
        monitor_name: Optional[str] = None,
        status: Optional[str] = None
    ) -> Tuple[List[PlanExecutionMonitor], int]:
        query = PlanExecutionMonitor.all()
        if monitor_code:
            query = query.filter(monitor_code__icontains=monitor_code)
        if monitor_name:
            query = query.filter(monitor_name__icontains=monitor_name)
        if status:
            query = query.filter(status=status)
        total = await query.count()
        offset = (page - 1) * page_size
        items = await query.offset(offset).limit(page_size).order_by('-created_at')
        return items, total

    @staticmethod
    async def check_code_exists(code: str, exclude_id: Optional[int] = None) -> bool:
        query = PlanExecutionMonitor.filter(monitor_code=code)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    @staticmethod
    async def update_metrics(monitor_id: int) -> Optional[PlanExecutionMonitor]:
        monitor = await MonitorService.get_by_id(monitor_id)
        if not monitor:
            return None

        mps_details = []
        if monitor.mps_id:
            mps_details = await MPSService.get_mps_details(monitor.mps_id)

        total_planned = Decimal("0")
        total_production = Decimal("0")
        completed_count = 0
        total_count = len(mps_details)

        for detail in mps_details:
            total_planned += detail.planned_quantity
            total_production += detail.production_quantity
            if detail.production_quantity >= detail.planned_quantity:
                completed_count += 1

        overall_progress = (total_production / total_planned) * 100 if total_planned > 0 else 0
        on_time_rate = (completed_count / total_count) * 100 if total_count > 0 else 0

        alert_count = await MRPExceptionAlert.filter(monitor_id=monitor_id, alert_status="active").count()
        exception_count = await MRPExceptionAlert.filter(monitor_id=monitor_id, alert_level="critical", alert_status="active").count()

        metrics_summary = {
            "total_planned_quantity": float(total_planned),
            "total_production_quantity": float(total_production),
            "completed_items": completed_count,
            "total_items": total_count
        }

        monitor.overall_progress = overall_progress
        monitor.on_time_rate = on_time_rate
        monitor.quality_rate = Decimal("98")
        monitor.efficiency_rate = Decimal("95")
        monitor.alert_count = alert_count
        monitor.exception_count = exception_count
        monitor.metrics_summary = metrics_summary
        await monitor.save()

        return monitor

    @staticmethod
    async def pause_monitor(monitor_id: int) -> Optional[PlanExecutionMonitor]:
        monitor = await MonitorService.get_by_id(monitor_id)
        if not monitor:
            return None
        if monitor.status != "running":
            raise ValueError("只能暂停运行中的监控")
        monitor.status = "paused"
        await monitor.save()
        return monitor

    @staticmethod
    async def resume_monitor(monitor_id: int) -> Optional[PlanExecutionMonitor]:
        monitor = await MonitorService.get_by_id(monitor_id)
        if not monitor:
            return None
        if monitor.status != "paused":
            raise ValueError("只能恢复已暂停的监控")
        monitor.status = "running"
        await monitor.save()
        return monitor

    @staticmethod
    async def get_stats() -> Dict[str, Any]:
        total_plans = await PlanExecutionMonitor.all().count()
        completed_plans = await PlanExecutionMonitor.filter(status="completed").count()
        exception_count = await MRPExceptionAlert.filter(alert_status="active").count()
        
        all_monitors = await PlanExecutionMonitor.all()
        total_progress = sum(m.overall_progress for m in all_monitors)
        progress_rate = int(total_progress / len(all_monitors)) if all_monitors else 0

        return {
            "total_plans": total_plans,
            "completed_plans": completed_plans,
            "exception_count": exception_count,
            "progress_rate": progress_rate
        }


class AlertService:
    @staticmethod
    async def get_by_id(alert_id: int) -> Optional[MRPExceptionAlert]:
        return await MRPExceptionAlert.filter(id=alert_id).first()

    @staticmethod
    async def get_by_code(alert_code: str) -> Optional[MRPExceptionAlert]:
        return await MRPExceptionAlert.filter(alert_code=alert_code).first()

    @staticmethod
    async def create_alert(data: AlertCreate) -> MRPExceptionAlert:
        if await AlertService.check_code_exists(data.alert_code):
            raise ValueError("告警编号已存在")
        return await MRPExceptionAlert.create(**data.__dict__)

    @staticmethod
    async def update_alert(alert_id: int, data: dict) -> Optional[MRPExceptionAlert]:
        alert = await MRPExceptionAlert.filter(id=alert_id).first()
        if not alert:
            return None
        update_data = {k: v for k, v in data.items() if v is not None}
        await alert.update_from_dict(update_data).save()
        return alert

    @staticmethod
    async def delete_alert(alert_id: int) -> bool:
        deleted_count = await MRPExceptionAlert.filter(id=alert_id).delete()
        return deleted_count > 0

    @staticmethod
    async def get_list(
        page: int = 1, page_size: int = 10,
        alert_code: Optional[str] = None,
        alert_type: Optional[str] = None,
        alert_level: Optional[str] = None,
        alert_status: Optional[str] = None
    ) -> Tuple[List[MRPExceptionAlert], int]:
        query = MRPExceptionAlert.all()
        if alert_code:
            query = query.filter(alert_code__icontains=alert_code)
        if alert_type:
            query = query.filter(alert_type=alert_type)
        if alert_level:
            query = query.filter(alert_level=alert_level)
        if alert_status:
            query = query.filter(alert_status=alert_status)
        total = await query.count()
        offset = (page - 1) * page_size
        items = await query.offset(offset).limit(page_size).order_by('-created_at')
        return items, total

    @staticmethod
    async def check_code_exists(code: str, exclude_id: Optional[int] = None) -> bool:
        query = MRPExceptionAlert.filter(alert_code=code)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    @staticmethod
    async def resolve_alert(alert_id: int, resolved_by: str, resolved_note: str = "") -> Optional[MRPExceptionAlert]:
        alert = await AlertService.get_by_id(alert_id)
        if not alert:
            return None
        if alert.alert_status == "resolved":
            raise ValueError("告警已处理")
        alert.alert_status = "resolved"
        alert.resolved_by = resolved_by
        alert.resolved_at = datetime.now()
        alert.resolved_note = resolved_note
        await alert.save()
        return alert

    @staticmethod
    async def get_active_alerts(monitor_id: Optional[int] = None) -> List[MRPExceptionAlert]:
        query = MRPExceptionAlert.filter(alert_status="active")
        if monitor_id:
            query = query.filter(monitor_id=monitor_id)
        return await query.order_by('-created_at')