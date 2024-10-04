from django.http import JsonResponse

class CustomResponseMiddleware:
    """
    This middleware handles format for success/error responses to enable seamless integration with FE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return self.process_response(request, response)

    def process_response(self, request, response):
        excluded_paths = ["/swagger/", "/docs/"]

        if request.path in excluded_paths:
            return response

        # For DRF responses
        if hasattr(response, "data"):
            is_success = response.status_code >= 200 and response.status_code < 300
            data = {
                "success": is_success,
                "data": response.data if is_success else None,
                "errors": response.data if not is_success else None,
                "status": response.status_code,
            }
            return JsonResponse(data, status=response.status_code)
        # For regular Django HTTP Responses
        return response
