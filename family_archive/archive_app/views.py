from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from datetime import datetime

from .forms import MediaFileForm
from .models import MediaFile, FamilyMember, Post, UploadedBy


def home_page(request):
    return render(request, 'archive_app/home_page.html')


def gallery(request):
    if request.method == 'POST':
        images = request.FILES.getlist('images')

        uploaded_by = UploadedBy.objects.create(
            user=request.user,
            date=datetime.now(),
        )
        for image in images:
            MediaFile.objects.create(
                uploaded_by=uploaded_by,
                date_taken=None,
                media_path=image,
            )

        uploaded_images = MediaFile.objects.filter(uploaded_by=uploaded_by)
        return tag_images_form(request, uploaded_images=uploaded_images)
    else:
        images = MediaFile.objects.all()
        context = {'images': images}
        return render(request, 'archive_app/gallery.html', context)


def tag_images_form(request, uploaded_images):
    forms = []

    for image in uploaded_images:
        form = MediaFileForm(instance=image)
        forms.append((image, form))

    context = {
        'image_forms': forms,
    }
    return render(request, 'archive_app/tag_images_form.html', context)


def update_image(request, image_id):
    image = get_object_or_404(MediaFile, pk=image_id)

    if request.method == 'POST':
        form = MediaFileForm(request.POST, instance=image)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success'})
    else:
        form = MediaFileForm(instance=image)

    return render(request, 'yourapp/update_date.html', {'form': form})


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