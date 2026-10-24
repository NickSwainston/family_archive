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
    show_contact = request.user.is_authenticated

    def fmt(date):
        return date.strftime('%-d %b %Y') if date else None

    # family-chart wants symmetric relationships, so collect them from both sides
    spouses = {fm.id: [] for fm in family_members}
    children = {fm.id: [] for fm in family_members}
    for fm in family_members:
        for partner_id in (fm.partner_id, fm.partner2_id):
            if partner_id in spouses:
                for a, b in ((fm.id, partner_id), (partner_id, fm.id)):
                    if b not in spouses[a]:
                        spouses[a].append(b)
        for parent_id in (fm.father_id, fm.mother_id):
            if parent_id in children:
                children[parent_id].append(fm.id)

    tree_data = []
    for fm in family_members:
        marriages = []
        for partner, date, location in (
            (fm.partner, fm.marriage_date, fm.marriage_location),
            (fm.partner2, fm.marriage_date2, fm.marriage_location2),
        ):
            if partner is not None:
                marriages.append({'partner': partner.full_name, 'date': fmt(date), 'location': location})
        data = {
            'gender': fm.gender.upper(),
            'name': fm.full_name or '',
            'avatar': fm.profile_picture.url if fm.profile_picture else '',
            'birth_year': fm.birth_date.year if fm.birth_date else None,
            'death_year': fm.death_date.year if fm.death_date else None,
            'birth_date': fmt(fm.birth_date),
            'birth_location': fm.birth_location,
            'death_date': fmt(fm.death_date),
            'marriages': marriages,
        }
        if show_contact:
            data['email'] = fm.email
            data['phone_number'] = fm.phone_number
        tree_data.append({
            'id': str(fm.id),
            'data': data,
            'rels': {
                'parents': [str(p) for p in (fm.father_id, fm.mother_id) if p in spouses],
                'spouses': [str(s) for s in spouses[fm.id]],
                'children': [str(c) for c in children[fm.id]],
            },
        })

    root = FamilyMember.objects.filter(full_name='Anthony Swainston').values_list('id', flat=True).first()

    context = {
        'tree_data': tree_data,
        'main_id': str(root) if root else None,
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
