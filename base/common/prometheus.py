from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST, push_to_gateway, CollectorRegistry
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
import time
import os
import asyncio
from typing import Dict, Callable


class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.registry = CollectorRegistry()
        
        self.request_counter = Counter(
            'http_requests_total',
            'Total HTTP Requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP Request Duration',
            ['method', 'endpoint'],
            registry=self.registry,
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )
        
        self.active_requests = Gauge(
            'http_active_requests',
            'Active HTTP Requests',
            registry=self.registry
        )
        
        self.response_size = Histogram(
            'http_response_size_bytes',
            'HTTP Response Size',
            ['method', 'endpoint'],
            registry=self.registry
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method
        endpoint = request.url.path
        
        if endpoint == '/metrics':
            return await call_next(request)
        
        self.active_requests.inc()
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            content_length = int(response.headers.get('content-length', 0))
        except Exception as e:
            status_code = 500
            content_length = 0
            raise
        finally:
            duration = time.time() - start_time
            self.active_requests.dec()
            self.request_counter.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
            self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
            self.response_size.labels(method=method, endpoint=endpoint).observe(content_length)
        
        return response


async def metrics_endpoint(request: Request) -> Response:
    from base.common.setting import settings
    
    if not getattr(settings, 'PROMETHEUS_ENABLED', False):
        return Response(status_code=404, content="Prometheus endpoint not enabled")
    
    from base.common.prometheus import prometheus_middleware
    
    data = generate_latest(prometheus_middleware.registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


prometheus_middleware = PrometheusMiddleware.__new__(PrometheusMiddleware)


def push_metrics():
    """推送指标到 Pushgateway"""
    from base.common.setting import settings
    from loguru import logger
    
    if not getattr(settings, 'PROMETHEUS_PUSH_ENABLED', False):
        return
    
    pushgateway_url = getattr(settings, 'PROMETHEUS_PUSHGATEWAY', 'localhost:9091')
    job_name = getattr(settings, 'app_name', 'aipaneladmin')
    
    try:
        push_to_gateway(
            pushgateway_url,
            job=job_name,
            registry=prometheus_middleware.registry
        )
        logger.debug(f"Metrics pushed to Pushgateway: {pushgateway_url}")
    except Exception as e:
        logger.error(f"Failed to push metrics to Pushgateway: {e}")


async def start_push_worker():
    """启动定时推送任务"""
    from base.common.setting import settings
    from loguru import logger
    
    if not getattr(settings, 'PROMETHEUS_PUSH_ENABLED', False):
        return
    
    push_interval = getattr(settings, 'PROMETHEUS_PUSH_INTERVAL', 10)
    logger.info(f"Starting Prometheus push worker, interval: {push_interval}s")
    
    while True:
        try:
            push_metrics()
        except Exception as e:
            logger.error(f"Error in push worker: {e}")
        
        await asyncio.sleep(push_interval)