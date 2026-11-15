from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic.edit import CreateView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.urls import reverse, reverse_lazy
from django.views.static import serve

from datetime import datetime
from itertools import groupby

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Prefetch

from .forms import MediaFileForm, EventForm
from .models import MediaFile, FamilyMember, Post, UploadedBy, Event


def is_ajax(request):
    """True for the per-file uploads sent by static/js/media.js."""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def save_uploaded_media(user, files):
    """Store uploaded files as MediaFile rows sharing one UploadedBy record."""
    uploaded_by = UploadedBy.objects.create(user=user, date=datetime.now())
    return [
        MediaFile.objects.create(uploaded_by=uploaded_by, date_taken=None, media_path=f)
        for f in files
    ]


def home_page(request):
    posts = Post.objects.all()[:10]  # Get 10 most recent posts
    context = {
        'posts': posts,
    }
    return render(request, 'archive_app/home_page.html', context)


@login_required
def gallery(request):
    if request.method == 'POST':
        images = request.FILES.getlist('images')

        uploaded = save_uploaded_media(request.user, images)
        if is_ajax(request):
            return JsonResponse({'ids': [m.id for m in uploaded]})
        uploaded_images = MediaFile.objects.filter(id__in=[m.id for m in uploaded])
        return tag_images_form(request, uploaded_images=uploaded_images)
    else:
        images = MediaFile.objects.all()
        context = {'images': images}
        return render(request, 'archive_app/gallery.html', context)


@login_required
def tag_images_form(request, uploaded_images=None):
    if uploaded_images is None:
        ids = [int(i) for i in request.GET.get('ids', '').split(',') if i.isdigit()]
        uploaded_images = MediaFile.objects.filter(id__in=ids, uploaded_by__user=request.user).order_by('id')
    if not uploaded_images:
        return redirect('/gallery/')

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

    return render(request, 'archive_app/tag_images_form.html', {'image_forms': [(image, form)]})


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

    roots = list(
        FamilyMember.objects.filter(full_name__in=['Anthony Swainston', 'Bella Swainston'])
        .values_list('id', flat=True)
    )

    context = {
        'family_members': family_member_dict_strs,
        'roots': roots,
    }
    return render(request, 'archive_app/family_tree.html', context)


# ---------------------------------------------------------------------------
# Event timeline
# ---------------------------------------------------------------------------

def _can_edit_event(user, event):
    return user.is_superuser or (event.created_by_id is not None and event.created_by_id == user.id)


@login_required
def timeline(request):
    events = (
        Event.objects
        .annotate(image_count=Count('images'))
        .prefetch_related(Prefetch('images', queryset=MediaFile.objects.order_by('date_taken', 'id')))
        .select_related('cover')
        # Explicit: Meta.ordering is ignored on GROUP BY (annotate/Count) queries
        .order_by('-start_date', '-id')
    )
    # Group into [(year, [events...]), ...] for the year markers; events are already newest first
    years = [(year, list(group)) for year, group in groupby(events, key=lambda e: e.start_date.year)]
    return render(request, 'archive_app/timeline.html', {'years': years})


@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event.objects.select_related('created_by'), pk=event_id)

    if request.method == 'POST':
        # Any logged-in family member can add photos to an event
        files = request.FILES.getlist('images')
        uploaded = save_uploaded_media(request.user, files) if files else []
        event.images.add(*uploaded)
        if is_ajax(request):
            return JsonResponse({'ids': [m.id for m in uploaded]})
        if files:
            messages.success(request, f"Added {len(files)} file{'s' if len(files) != 1 else ''}.")
        return redirect('event_detail', event_id=event.id)

    images = event.images.select_related('uploaded_by__user').order_by('date_taken', 'id')
    context = {
        'event': event,
        'images': images,
        'can_edit': _can_edit_event(request.user, event),
    }
    return render(request, 'archive_app/event_detail.html', context)


@login_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            if is_ajax(request):
                # The browser creates the event first, then uploads each photo to the event page
                url = reverse('event_detail', args=[event.id])
                return JsonResponse({'upload_url': url, 'redirect': url})
            files = request.FILES.getlist('images')
            if files:
                event.images.add(*save_uploaded_media(request.user, files))
            return redirect('event_detail', event_id=event.id)
        if is_ajax(request):
            return JsonResponse({'errors': form.errors}, status=400)
    else:
        form = EventForm()
    return render(request, 'archive_app/event_form.html', {'form': form, 'event': None})


@login_required
def event_edit(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if not _can_edit_event(request.user, event):
        raise PermissionDenied

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm(instance=event)
    return render(request, 'archive_app/event_form.html', {'form': form, 'event': event})


def serve_media(request, path):
    """Serve an uploaded file from MEDIA_ROOT (read per request so tests can override it)."""
    return serve(request, path, document_root=settings.MEDIA_ROOT)
