"""Custom middleware for request tracking and logging."""
import time
import uuid
import logging

logger = logging.getLogger("django.request")


class RequestIdMiddleware:
    """Middleware to add X-Request-ID to requests and responses."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.request_id = request_id
        
        # Process request
        response = self.get_response(request)
        
        # Add request ID to response
        response["X-Request-ID"] = request_id
        
        return response


class AccessLogMiddleware:
    """Middleware to log all requests in JSON format."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Record start time
        start_time = time.time()
        
        # Process request
        response = self.get_response(request)
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log request details
        log_extra = {
            "request_id": getattr(request, "request_id", None),
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        }
        
        # Add user ID if authenticated
        if hasattr(request, "user") and request.user.is_authenticated:
            log_extra["user_id"] = request.user.id
        
        # Log the request
        logger.info(
            f"{request.method} {request.path} {response.status_code} {duration_ms}ms",
            extra=log_extra
        )
        
        return response

