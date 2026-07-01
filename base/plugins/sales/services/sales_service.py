from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal

try:
    from base.plugins.sales.models.order import CustomerOrder, OrderItem, OrderStatus
    from base.plugins.customer.models.customer import Customer
except ImportError:
    CustomerOrder = None
    OrderItem = None
    OrderStatus = None
    Customer = None


class SalesService:
    @staticmethod
    async def get_sales_overview(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        filters = {"payment_status": OrderStatus.PAID}

        if start_date:
            filters["created_at__gte"] = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
            filters["created_at__gte"] = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

        if end_date:
            end_of_day = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            filters["created_at__lt"] = end_of_day.replace(tzinfo=timezone.utc)

        paid_orders = await CustomerOrder.filter(**filters)

        total_orders = await CustomerOrder.filter(**filters).count()
        total_amount = Decimal("0.00")
        total_items = 0

        for order in paid_orders:
            total_amount += order.final_amount
            items = await OrderItem.filter(order_id=order.id)
            for item in items:
                total_items += item.quantity

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_orders = await CustomerOrder.filter(
            payment_status=OrderStatus.PAID,
            created_at__gte=today_start
        ).count()

        today_amount = Decimal("0.00")
        today_order_list = await CustomerOrder.filter(
            payment_status=OrderStatus.PAID,
            created_at__gte=today_start
        )
        for order in today_order_list:
            today_amount += order.final_amount

        pending_orders = await CustomerOrder.filter(payment_status=OrderStatus.PENDING).count()
        cancelled_orders = await CustomerOrder.filter(payment_status=OrderStatus.CANCELLED).count()

        return {
            "total_orders": total_orders,
            "total_amount": float(total_amount),
            "total_items": total_items,
            "today_orders": today_orders,
            "today_amount": float(today_amount),
            "pending_orders": pending_orders,
            "cancelled_orders": cancelled_orders,
            "start_date": start_date,
            "end_date": end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }

    @staticmethod
    async def get_daily_sales(start_date: str, end_date: str) -> List[Dict[str, Any]]:
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

        current = start
        result = []

        while current < end:
            day_start = current
            day_end = current + timedelta(days=1)

            orders = await CustomerOrder.filter(
                payment_status=OrderStatus.PAID,
                created_at__gte=day_start,
                created_at__lt=day_end
            )

            day_amount = Decimal("0.00")
            day_count = 0
            for order in orders:
                day_amount += order.final_amount
                day_count += 1

            result.append({
                "date": current.strftime("%Y-%m-%d"),
                "orders_count": day_count,
                "amount": float(day_amount)
            })

            current += timedelta(days=1)

        return result

    @staticmethod
    async def get_monthly_sales(year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month

        month_start = datetime(year, month, 1).replace(tzinfo=timezone.utc)
        if month == 12:
            next_month_start = datetime(year + 1, 1, 1).replace(tzinfo=timezone.utc)
        else:
            next_month_start = datetime(year, month + 1, 1).replace(tzinfo=timezone.utc)

        orders = await CustomerOrder.filter(
            payment_status=OrderStatus.PAID,
            created_at__gte=month_start,
            created_at__lt=next_month_start
        )

        total_amount = Decimal("0.00")
        total_count = 0
        daily_data = []

        current = month_start
        while current < next_month_start:
            day_start = current
            day_end = current + timedelta(days=1)

            day_orders = await CustomerOrder.filter(
                payment_status=OrderStatus.PAID,
                created_at__gte=day_start,
                created_at__lt=day_end
            )

            day_amount = Decimal("0.00")
            day_count = 0
            for order in day_orders:
                day_amount += order.final_amount
                day_count += 1

            total_amount += day_amount
            total_count += day_count

            daily_data.append({
                "date": current.strftime("%Y-%m-%d"),
                "day": current.day,
                "orders_count": day_count,
                "amount": float(day_amount)
            })

            current += timedelta(days=1)

        return {
            "year": year,
            "month": month,
            "total_amount": float(total_amount),
            "total_orders": total_count,
            "daily_data": daily_data
        }

    @staticmethod
    async def get_top_products(limit: int = 10, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        filters = {"order__payment_status": OrderStatus.PAID}

        if start_date:
            filters["order__created_at__gte"] = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            filters["order__created_at__gte"] = datetime.now(timezone.utc) - timedelta(days=30)

        if end_date:
            end_of_day = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            filters["order__created_at__lt"] = end_of_day.replace(tzinfo=timezone.utc)

        from tortoise.expressions import Sum, Count

        product_stats = await OrderItem.filter(**filters).annotate(
            total_sales=Sum("total_price"),
            total_quantity=Sum("quantity"),
            order_count=Count("order_id", distinct=True)
        ).group_by("product_name", "product_type").order_by("-total_sales").limit(limit)

        result = []
        for stat in product_stats:
            result.append({
                "product_name": stat.product_name,
                "product_type": stat.product_type,
                "total_sales": float(stat.total_sales) if stat.total_sales else 0.0,
                "total_quantity": stat.total_quantity or 0,
                "order_count": stat.order_count or 0
            })

        return result

    @staticmethod
    async def get_top_customers(limit: int = 10, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        filters = {"payment_status": OrderStatus.PAID}

        if start_date:
            filters["created_at__gte"] = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            filters["created_at__gte"] = datetime.now(timezone.utc) - timedelta(days=30)

        if end_date:
            end_of_day = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            filters["created_at__lt"] = end_of_day.replace(tzinfo=timezone.utc)

        from tortoise.expressions import Sum, Count

        customer_stats = await CustomerOrder.filter(**filters).annotate(
            total_spent=Sum("final_amount"),
            order_count=Count("id")
        ).group_by("customer_id").order_by("-total_spent").limit(limit).prefetch_related("customer")

        result = []
        for stat in customer_stats:
            customer_name = str(stat.customer) if stat.customer else "未知客户"
            customer_phone = stat.customer.phone if stat.customer else None
            result.append({
                "customer_id": stat.customer_id,
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "total_spent": float(stat.total_spent) if stat.total_spent else 0.0,
                "order_count": stat.order_count or 0
            })

        return result

    @staticmethod
    async def get_payment_method_stats(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        filters = {"payment_status": OrderStatus.PAID}

        if start_date:
            filters["created_at__gte"] = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            filters["created_at__gte"] = datetime.now(timezone.utc) - timedelta(days=30)

        if end_date:
            end_of_day = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            filters["created_at__lt"] = end_of_day.replace(tzinfo=timezone.utc)

        from tortoise.expressions import Sum, Count

        payment_stats = await CustomerOrder.filter(**filters).annotate(
            total_amount=Sum("final_amount"),
            order_count=Count("id")
        ).group_by("payment_method")

        result = {}
        total_amount = Decimal("0.00")
        total_count = 0

        for stat in payment_stats:
            method = stat.payment_method.value if hasattr(stat.payment_method, 'value') else stat.payment_method
            amount = float(stat.total_amount) if stat.total_amount else 0.0
            count = stat.order_count or 0

            result[method] = {
                "amount": amount,
                "count": count,
                "percentage": 0.0
            }
            total_amount += stat.total_amount if stat.total_amount else Decimal("0.00")
            total_count += count

        for method in result:
            if total_amount > 0:
                result[method]["percentage"] = round((result[method]["amount"] / float(total_amount)) * 100, 2)

        return {
            "total_amount": float(total_amount),
            "total_orders": total_count,
            "methods": result
        }
