from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from .forms import MediaFileForm
from .models import MediaFile, FamilyMember, Post


def home_page(request):
    return render(request, 'archive_app/home_page.html')


def media_upload(request):
    form = MediaFileForm()

    if request.method == 'POST':
        form = MediaFileForm(request.POST, request.FILES)
        input_files = request.FILES.getlist('media_path')
        media_files = []
        print(input_files)
        print(type(input_files))
        for input_file in input_files:
            print(input_file)
            media_files.append(MediaFile.objects.create(media_path=input_file))
        return redirect('media_add_details', media_files=media_files)

    context = {'form': form}
    return render(request, 'archive_app/media_upload_form.html', context)


def media_add_details(request):
    media = request.GET.get('media_files')
    context = {'media': media}
    return render(request, 'archive_app/gallery.html', context)


def success(request):
    return HttpResponse('<h1>Form saved.</h1>')


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ['content', 'images']
    success_url = reverse_lazy('post_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


def family_tree(request):
    family_members = FamilyMember.objects.all()
    family_member_dict_strs = []
    for fm in family_members:
        this_str = f"{{ id: {fm.id}, gender: '{fm.get_gender_display()}', name: '{fm.full_name}'"
        if len(str(fm.profile_picture)) == 0:
            this_str += f", image: '/static/default_profile.jpg'"
        else:
            this_str += f", image: '{fm.profile_picture.url}'"

        # partners
        if fm.partner is not None:
            if fm.partner2 is None:
                # only one partner
                this_str += f", pids: [{fm.partner.id}]"
            else:
                this_str += f", pids: [{fm.partner.id}, {fm.partner2.id}]"
            # Marriage one
            this_str += f", partner: '{fm.partner.full_name}'"
            if fm.marriage_date is not None:
                this_str += f", marriage_date: '{fm.marriage_date}'"
            if fm.marriage_location is not None:
                this_str += f', marriage_location: "{fm.marriage_location}"'

            if fm.partner2 is not None:
                # Marriage two
                this_str += f", second_partner: '{fm.partner2.full_name}'"
                if fm.marriage_date2 is not None:
                    this_str += f", second_marriage_date: '{fm.marriage_date2}'"
                if fm.marriage_location2 is not None:
                    this_str += f', second_marriage_location: "{fm.marriage_location2}"'

        # parents
        if fm.father is not None:
            this_str += f", fid: {fm.father.id}"
            this_str += f", father: '{fm.father.full_name}'"
        if fm.mother is not None:
            this_str += f", mid: {fm.mother.id}"
            this_str += f", mother: '{fm.mother.full_name}'"

        # birth and death
        if fm.birth_date is not None:
            this_str += f", birthDate: '{fm.birth_date}'"
        if fm.birth_location is not None:
            this_str += f', birth_location: "{fm.birth_location}"'
        if fm.death_date is not None:
            this_str += f", deathDate: '{fm.death_date}'"

        # Contact info
        if fm.email is not None:
            this_str += f", email: '{fm.email}'"
        if fm.phone_number is not None:
            this_str += f", phone_number: '{fm.phone_number}'"

        # finish
        this_str += "},"
        family_member_dict_strs.append(this_str)
    context = {
        'family_members': family_member_dict_strs,
    }
    return render(request, 'archive_app/family_tree.html', context)