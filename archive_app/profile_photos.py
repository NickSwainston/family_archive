"""Semi-automatic profile photo picker for family tree members.

For each FamilyMember a staff user can search for candidate photos (SearXNG image search plus photos
already in the archive) and click the right one; it is then saved as their profile_picture.
Nothing is assigned automatically - a person always makes the choice.
"""
import ipaddress
import uuid
import json
import mimetypes
import socket
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST

from .models import FamilyMember, MediaFile

MAX_DOWNLOAD_BYTES = 15 * 1024 * 1024
ARCHIVE_PAGE_SIZE = 24
NO_PHOTO = Q(profile_picture='') | Q(profile_picture__isnull=True)
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic')


class PhotoSearchError(Exception):
    """Shown to the user in the candidates panel."""


# ---------------------------------------------------------------------------
# Image search via SearXNG (self-hosted metasearch, no API key)
# ---------------------------------------------------------------------------

def default_query(member):
    """Name plus birthplace helps disambiguate common names."""
    parts = [member.full_name or '']
    if member.birth_location:
        # First part of the location is usually the town
        parts.append(member.birth_location.split(',')[0].strip())
    return ' '.join(p for p in parts if p)


def web_image_search(query, limit=24):
    """Return [{'thumbnail', 'image_url', 'fallback_url', 'page_url', 'title', 'source'}] from SearXNG.

    Needs `json` listed under search.formats in SearXNG's settings.yml, otherwise it answers 403.
    """
    base = settings.SEARXNG_URL.rstrip('/')
    if not base:
        raise PhotoSearchError('Web search is not configured (set SEARXNG_URL).')
    # Only ask engines that can return photos of real people. The default images category also queries
    # stock/art/icon sources (pexels, openverse, artic, lucide...) that bury the useful results, and
    # passing `categories` alongside `engines` makes SearXNG ignore the engine list - so send engines only.
    params = urllib.parse.urlencode({
        'q': query, 'engines': settings.SEARXNG_IMAGE_ENGINES, 'format': 'json', 'safesearch': 1,
    })
    req = urllib.request.Request(f'{base}/search?{params}', headers={'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        hint = ' (is "json" enabled in SearXNG search.formats?)' if e.code == 403 else ''
        raise PhotoSearchError(f'Web search failed (HTTP {e.code}){hint}.')
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise PhotoSearchError('Could not reach the search service.')

    results, seen = [], set()
    for item in data.get('results', []):
        image_url = item.get('img_src')
        thumbnail = item.get('thumbnail_src') or image_url
        if not image_url or image_url in seen:
            continue
        seen.add(image_url)
        # SearXNG sometimes returns protocol-relative links
        image_url, thumbnail = (u if not u.startswith('//') else 'https:' + u for u in (image_url, thumbnail))
        results.append({
            'thumbnail': thumbnail,
            'image_url': image_url,
            'fallback_url': thumbnail if thumbnail != image_url else '',
            'page_url': item.get('url', ''),
            'title': item.get('title', ''),
            'source': item.get('source') or urllib.parse.urlparse(item.get('url', '')).hostname or item.get('engine', ''),
        })
        if len(results) >= limit:
            break
    return results


# ---------------------------------------------------------------------------
# Safe image download
# ---------------------------------------------------------------------------

def _check_public_host(url):
    """Reject non-http(s) URLs and hosts that resolve to private/internal addresses.

    The server fetches the chosen image itself, so without this a crafted URL could make it
    request internal cluster services (SSRF).
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise PhotoSearchError('Only http(s) image links can be used.')
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80))
    except socket.gaierror:
        raise PhotoSearchError('Could not resolve the image host.')
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise PhotoSearchError('That image link points at a private address.')


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    # Redirects are followed manually so each hop is re-checked by _check_public_host
    def redirect_request(self, *args, **kwargs):
        return None


def download_image(url, max_redirects=3):
    """Fetch an image from the internet; returns (bytes, extension)."""
    opener = urllib.request.build_opener(_NoRedirect)
    for _ in range(max_redirects + 1):
        _check_public_host(url)
        req = urllib.request.Request(url, headers={'User-Agent': 'FamilyArchive/1.0 (profile photo picker)'})
        try:
            resp = opener.open(req, timeout=20)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get('Location'):
                url = urllib.parse.urljoin(url, e.headers['Location'])
                continue
            raise PhotoSearchError(f'Image download failed (HTTP {e.code}).')
        except (urllib.error.URLError, TimeoutError):
            raise PhotoSearchError('Image download failed.')

        with resp:
            content_type = resp.headers.get_content_type()
            if not content_type.startswith('image/'):
                raise PhotoSearchError('That link is not an image.')
            data = resp.read(MAX_DOWNLOAD_BYTES + 1)
        if len(data) > MAX_DOWNLOAD_BYTES:
            raise PhotoSearchError('Image is too large.')
        ext = mimetypes.guess_extension(content_type) or '.jpg'
        return data, ('.jpg' if ext == '.jpe' else ext)
    raise PhotoSearchError('Too many redirects.')


# ---------------------------------------------------------------------------
# Immich face recognition
# ---------------------------------------------------------------------------
# Immich already detects and groups faces; once a person is named in Immich we can show their face
# crop and the photos they appear in. Immich is internal-only and needs an API key, so images are
# proxied through immich_image() rather than linked directly from the browser.
IMMICH_PEOPLE_LIMIT = 3
IMMICH_PHOTOS_PER_PERSON = 12


def _immich_request(path, body=None, accept='application/json'):
    base = settings.IMMICH_URL.rstrip('/')
    if not (base and settings.IMMICH_API_KEY):
        raise PhotoSearchError('Immich is not configured (set IMMICH_URL and IMMICH_API_KEY).')
    headers = {'x-api-key': settings.IMMICH_API_KEY, 'Accept': accept}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(f'{base}/api{path}', data=data, headers=headers)
    try:
        return urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise PhotoSearchError(f'Immich refused the API key (HTTP {e.code}); it needs person.read, asset.read and asset.view.')
        raise PhotoSearchError(f'Immich request failed (HTTP {e.code}).')
    except (urllib.error.URLError, TimeoutError):
        raise PhotoSearchError('Could not reach Immich.')


def _immich_json(path, body=None):
    with _immich_request(path, body) as resp:
        return json.load(resp)


def immich_find_people(name):
    """Named Immich people matching `name`; falls back to first + last name (skips middle names)."""
    tried, people = [], []
    words = name.split()
    for candidate in (name, f'{words[0]} {words[-1]}' if len(words) > 2 else None):
        if not candidate or candidate in tried:
            continue
        tried.append(candidate)
        found = _immich_json('/search/person?' + urllib.parse.urlencode({'name': candidate, 'withHidden': 'false'}))
        people = [p for p in found if p.get('name')]
        if people:
            break
    return people[:IMMICH_PEOPLE_LIMIT]


def immich_person_photos(person_id):
    """Most recent photos Immich has tagged with this person."""
    body = {'personIds': [person_id], 'type': 'IMAGE', 'size': IMMICH_PHOTOS_PER_PERSON, 'order': 'desc'}
    items = _immich_json('/search/metadata', body).get('assets', {}).get('items', [])
    return [{'id': a['id'], 'taken': (a.get('localDateTime') or a.get('fileCreatedAt') or '')[:10]} for a in items]


def immich_candidates(name):
    """[{'person': {...}, 'photos': [...]}, ...] for the template."""
    return [{'person': p, 'photos': immich_person_photos(p['id'])} for p in immich_find_people(name)]


def immich_image_bytes(kind, object_id):
    """Fetch a face crop ('face') or a large preview of a photo ('photo'); returns (bytes, content_type)."""
    try:
        object_id = str(uuid.UUID(object_id))  # Immich ids are UUIDs; also stops path tricks in the URL
    except ValueError:
        raise PhotoSearchError('Bad Immich id.')
    path = {'face': f'/people/{object_id}/thumbnail', 'photo': f'/assets/{object_id}/thumbnail?size=preview'}.get(kind)
    if path is None:
        raise PhotoSearchError('Unknown Immich image type.')
    with _immich_request(path, accept='image/*') as resp:
        content_type = resp.headers.get_content_type()
        data = resp.read(MAX_DOWNLOAD_BYTES + 1)
    if not content_type.startswith('image/') or len(data) > MAX_DOWNLOAD_BYTES:
        raise PhotoSearchError('Immich did not return a usable image.')
    return data, content_type


# ---------------------------------------------------------------------------
# Views (staff only: changing everyone's profile photo is an admin task)
# ---------------------------------------------------------------------------

@staff_member_required
def profile_photos(request):
    show_all = request.GET.get('all') == '1'
    members = FamilyMember.objects.order_by('full_name')
    if not show_all:
        members = members.filter(NO_PHOTO)
    context = {
        'members': members,
        'show_all': show_all,
        'missing_count': FamilyMember.objects.filter(NO_PHOTO).count(),
        'total_count': FamilyMember.objects.count(),
    }
    return render(request, 'archive_app/profile_photos.html', context)


@staff_member_required
def profile_photo_candidates(request, member_id):
    """htmx partial: Immich face matches + web results, or (source=archive) a page of archive photos."""
    member = get_object_or_404(FamilyMember, pk=member_id)
    source = request.GET.get('source', 'immich')
    query = request.GET.get('q', '').strip() or default_query(member)
    immich_name = request.GET.get('name', '').strip() or (member.full_name or '')

    immich_results, immich_error, web_results, web_error = [], None, [], None
    archive, page = [], max(int(request.GET.get('page', '1') or 1), 1)
    if source == 'archive':
        archive = [
            m for m in MediaFile.objects.order_by('-date_taken', '-id')
            [(page - 1) * ARCHIVE_PAGE_SIZE: page * ARCHIVE_PAGE_SIZE]
            if (m.media_path.name or '').lower().endswith(IMAGE_EXTENSIONS)
        ]
    else:
        if immich_name:
            try:
                immich_results = immich_candidates(immich_name)
            except PhotoSearchError as e:
                immich_error = str(e)
        try:
            web_results = web_image_search(query)
        except PhotoSearchError as e:
            web_error = str(e)

    context = {
        'member': member,
        'source': source,
        'query': query,
        'immich_name': immich_name,
        'immich_results': immich_results,
        'immich_error': immich_error,
        'web_results': web_results,
        'web_error': web_error,
        'archive': archive,
        'archive_page': page,
        'archive_has_more': source == 'archive' and MediaFile.objects.count() > page * ARCHIVE_PAGE_SIZE,
    }
    return render(request, 'archive_app/_profile_photo_candidates.html', context)


@staff_member_required
@require_POST
def set_profile_photo(request, member_id):
    """Save the chosen candidate (archive media_id, or web image_url) as the profile picture."""
    member = get_object_or_404(FamilyMember, pk=member_id)
    error = None
    try:
        if request.POST.get('media_id'):
            media = get_object_or_404(MediaFile, pk=request.POST['media_id'])
            with media.media_path.open('rb') as f:
                data = f.read()
            ext = '.' + media.media_path.name.rsplit('.', 1)[-1].lower()
        elif request.POST.get('immich_kind'):
            data, content_type = immich_image_bytes(request.POST['immich_kind'], request.POST.get('immich_id', ''))
            ext = mimetypes.guess_extension(content_type) or '.jpg'
            ext = '.jpg' if ext == '.jpe' else ext
        elif request.POST.get('image_url'):
            try:
                data, ext = download_image(request.POST['image_url'])
            except PhotoSearchError:
                # Many sites block hotlinking; the search engine's thumbnail is smaller but usually works
                if not request.POST.get('fallback_url'):
                    raise
                data, ext = download_image(request.POST['fallback_url'])
        else:
            return HttpResponseBadRequest('Nothing selected.')

        old = member.profile_picture.name if member.profile_picture else None
        member.profile_picture.save(f'profile_{member.id}{ext}', ContentFile(data), save=True)
        # Remove the replaced file, unless it's shared with an archive MediaFile
        if old and old != member.profile_picture.name and not MediaFile.objects.filter(media_path=old).exists():
            member.profile_picture.storage.delete(old)
    except PhotoSearchError as e:
        error = str(e)

    response = render(request, 'archive_app/_profile_photo_card.html', {'member': member, 'error': error})
    if not error:
        # htmx fires this as a DOM event; the family tree page listens for it to swap the photo in place
        response['HX-Trigger'] = json.dumps({
            'profilePhotoChanged': {'id': str(member.id), 'url': member.profile_picture.url},
        })
    return response


@staff_member_required
@cache_control(private=True, max_age=3600)
def immich_image(request, kind, object_id):
    """Pass an Immich face crop / photo preview through to the browser (Immich needs the API key)."""
    try:
        data, content_type = immich_image_bytes(kind, object_id)
    except PhotoSearchError:
        raise Http404
    return HttpResponse(data, content_type=content_type)
