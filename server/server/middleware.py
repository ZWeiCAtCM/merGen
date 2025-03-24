# 在你的项目中创建 middleware.py（或者放在适当位置）
class DisableCSRFMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 对以 /api/llama_gateway/ 开头的请求禁用 CSRF 检查
        if request.path.startswith('/api/llama_gateway/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        response = self.get_response(request)
        return response
