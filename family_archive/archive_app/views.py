from django.http import HttpResponse
from django.shortcuts import redirect, render

from .forms import MediaFileForm
from .models import MediaFile


def home_page(request):
    return render(request, 'archive_app/home_page.html')


def media_upload(request):
    form = MediaFileForm()

    if request.method == 'POST':
        form = MediaFileForm(request.POST, request.FILES)
        images = request.FILES.getlist('media_path')
        if form.is_valid():
            for i in images:
                print(i)
                MediaFile.objects.create(media_path=i)
            # TODO make better
            return HttpResponse('<h1>Form saved.</h1>')

    context = {'form': form}
    return render(request, 'archive_app/media_upload_form.html', context)

def success(request):
    return HttpResponse('<h1>Form saved.</h1>')


def family_tree(request):
    return render(request, 'archive_app/family_tree.html')