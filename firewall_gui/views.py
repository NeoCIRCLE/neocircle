from django.http import HttpResponse

def index(request):
    return HttpResponse("Ez itt a bd tuzfaladminja.")
