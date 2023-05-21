from django.http import HttpResponse
from django.shortcuts import redirect, render

from .forms import MediaFileForm
from .models import MediaFile, FamilyMember


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
    family_members = FamilyMember.objects.all()
    family_member_dict_strs = []
    for fm in family_members:
        this_str = f"{{ id: {fm.id}, gender: '{fm.get_gender_display()}', name: '{fm.full_name}'"

        # partners
        if fm.partner is not None:
            if fm.partner2 is None:
                # only one partner
                this_str += f", pids: [{fm.partner.id}]"
            else:
                this_str += f", pids: [{fm.partner.id}, {fm.partner2.id}]"

        # parents
        if fm.father is not None:
            this_str += f", fid: {fm.father.id}"
        if fm.mother is not None:
            this_str += f", mid: {fm.mother.id}"

        # birth and death
        if fm.birth_date is not None:
            this_str += f", birthDate: {fm.birth_date}"
        if fm.death_date is not None:
            this_str += f",deathDate: {fm.death_date}"

        # finish
        this_str += "},"
        family_member_dict_strs.append(this_str)
    context = {
        'family_members': family_member_dict_strs,
    }
    return render(request, 'archive_app/family_tree.html', context)