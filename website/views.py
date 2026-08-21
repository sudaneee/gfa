from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from communication.models import Announcement, Event
from website.content import get_blocks, get_section
from website.models import ContactMessage


def home(request):
    context = {
        'active_page': 'home',
        'announcements': Announcement.objects.filter(is_published=True)[:3],
        'events': Event.objects.filter(date__gte=timezone.localdate())[:3],
        'welcome': get_section('home_welcome'),
        'moral': get_section('home_moral'),
        'parent_portal': get_section('home_parent_portal'),
        'why_choose_us': get_blocks('home', 'why_choose_us'),
        'levels': get_blocks('home', 'levels'),
        'facility_highlights': get_blocks('home', 'facilities'),
        'character_cards': get_blocks('home', 'character'),
    }
    return render(request, 'website/home.html', context)


def about(request):
    context = {
        'active_page': 'about',
        'who_we_are': get_section('about_who_we_are'),
        'stats': get_blocks('about', 'stats'),
        'mission_vision': get_blocks('about', 'mission_vision'),
        'philosophy': get_blocks('about', 'philosophy'),
    }
    return render(request, 'website/about.html', context)


def academics(request):
    from academics.models import Subject

    subjects = Subject.objects.all()
    context = {
        'active_page': 'academics',
        'levels': get_blocks('academics', 'levels'),
        'calendar_cards': get_blocks('academics', 'calendar'),
        'early_subjects': subjects.filter(level__in=['Creche', 'Pre-Nursery', 'Nursery']),
        'primary_subjects': subjects.filter(level='Primary'),
        'secondary_subjects': subjects.filter(level='Secondary'),
    }
    return render(request, 'website/academics.html', context)


def facilities(request):
    context = {
        'active_page': 'facilities',
        'facility_cards': get_blocks('facilities', 'facilities'),
        'activity_cards': get_blocks('facilities', 'activities'),
    }
    return render(request, 'website/facilities.html', context)


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', 'general')
        message = request.POST.get('message', '').strip()

        if name and phone and email and message:
            ContactMessage.objects.create(
                name=name, phone=phone, email=email, subject=subject, message=message,
            )
            messages.success(request, 'Your message has been sent. We will get back to you shortly.')
            return redirect('website:contact')
        messages.error(request, 'Please fill in all required fields.')

    return render(request, 'website/contact.html', {'active_page': 'contact'})


def news_events(request):
    context = {
        'active_page': 'news_events',
        'upcoming_events': Event.objects.filter(date__gte=timezone.localdate()),
        'past_events': Event.objects.filter(date__lt=timezone.localdate()),
    }
    return render(request, 'website/news_events.html', context)
