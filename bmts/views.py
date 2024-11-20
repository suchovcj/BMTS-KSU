from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import StaffLoginForm
from .forms import MaintenanceTicketForm
from django.contrib import messages
from .models import MaintenanceTicket
from django.db.models import Q
from django.utils import timezone


@login_required
def index(request):
    # Get 3 most recent tickets
    recent_tickets = MaintenanceTicket.objects.all().order_by('-date_submitted')[:3]
    
    context = {
        'recent_tickets': recent_tickets,
        # ... other context items ...
    }
    return render(request, 'bmts/index.html', context)

@login_required
def open_tickets(request):
    if request.method == 'POST':
        ticket_ids = request.POST.getlist('ticket_ids')
        if ticket_ids:
            # Update tickets with current timestamp when closing
            MaintenanceTicket.objects.filter(id__in=ticket_ids).update(
                status='Closed',
                date_closed=timezone.now()
            )
            messages.success(request, f'{len(ticket_ids)} ticket(s) marked as closed.')
        return redirect('bmts:open_tickets')

    # Get filter parameters
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-date_submitted')
    date_filter = request.GET.get('date_filter', 'all')

    # Base queryset
    tickets = MaintenanceTicket.objects.filter(status='Open')

    # Apply search filter
    if search_query:
        tickets = tickets.filter(
            Q(ticket_number__icontains=search_query) |
            Q(bathroom_number__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Apply date filter
    from datetime import datetime, timedelta
    today = datetime.now().date()
    if date_filter == 'today':
        tickets = tickets.filter(date_submitted__date=today)
    elif date_filter == 'week':
        week_ago = today - timedelta(days=7)
        tickets = tickets.filter(date_submitted__date__gte=week_ago)
    elif date_filter == 'month':
        month_ago = today - timedelta(days=30)
        tickets = tickets.filter(date_submitted__date__gte=month_ago)

    # Apply sorting
    tickets = tickets.order_by(sort_by)

    context = {
        'tickets': tickets,
        'search_query': search_query,
        'sort_by': sort_by,
        'date_filter': date_filter,
    }
    return render(request, 'bmts/open_tickets.html', context)

@login_required
def closed_tickets(request):
    # Similar filtering logic as open_tickets
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-date_submitted')
    date_filter = request.GET.get('date_filter', 'all')

    tickets = MaintenanceTicket.objects.filter(status='Closed')

    if search_query:
        tickets = tickets.filter(
            Q(ticket_number__icontains=search_query) |
            Q(bathroom_number__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    from datetime import datetime, timedelta
    today = datetime.now().date()
    if date_filter == 'today':
        tickets = tickets.filter(date_submitted__date=today)
    elif date_filter == 'week':
        week_ago = today - timedelta(days=7)
        tickets = tickets.filter(date_submitted__date__gte=week_ago)
    elif date_filter == 'month':
        month_ago = today - timedelta(days=30)
        tickets = tickets.filter(date_submitted__date__gte=month_ago)

    tickets = tickets.order_by(sort_by)

    context = {
        'tickets': tickets,
        'search_query': search_query,
        'sort_by': sort_by,
        'date_filter': date_filter,
    }
    return render(request, 'bmts/closed_tickets.html', context)

@login_required
def staff(request):
    return render(request, 'bmts/staff.html')

@login_required
def reports(request):
    return render(request, 'bmts/reports.html')

@login_required
def map(request):
    return render(request, 'bmts/map.html')

def login_view(request):
    if request.method == 'POST':
        form = StaffLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('bmts:index')
    else:
        form = StaffLoginForm()
    return render(request, 'bmts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('bmts:login')

@login_required
def create_ticket(request):
    if request.method == 'POST':
        form = MaintenanceTicketForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Maintenance ticket submitted successfully!')
            return redirect('bmts:index')  # or wherever you want to redirect after submission
    else:
        form = MaintenanceTicketForm()
    
    return render(request, 'bmts/create_ticket.html', {'form': form})