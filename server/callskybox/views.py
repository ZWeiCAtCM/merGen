from django.http import JsonResponse

def generate_from_skybox(request):
    return JsonResponse({"panoramic": "skybox-panoramic"})
def doodle_from_skybox(request):
    return JsonResponse({"doodle": "skybox-doodle"})
def inpainting_from_skybox(request):
    return JsonResponse({"inpainting": "skybox-inpainting"})