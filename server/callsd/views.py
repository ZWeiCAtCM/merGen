from django.http import JsonResponse

def generate_from_sd(request):
    return JsonResponse({"panoramic": "sd-panoramic"})
def doodle_from_sd(request):
    return JsonResponse({"doodle": "sd-doodle"})
def inpainting_from_sd(request):
    return JsonResponse({"inpainting": "sd-inpainting"})