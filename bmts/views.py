from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import StaffLoginForm
from .forms import MaintenanceTicketForm
from django.contrib import messages
from .models import MaintenanceTicket, Staff
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib.auth import get_user_model  # Add this line
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.contrib.sessions.models import Session
from django.utils import timezone

Staff = get_user_model()  # This gets your custom Staff model

@login_required
def staff_list(request):
    # Get all staff members
    staff_members = Staff.objects.filter(is_staff=True)

    # Get search query
    search_query = request.GET.get('search', '')
    if search_query:
        staff_members = staff_members.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Get role filter
    role_filter = request.GET.get('role', 'all')
    if role_filter == 'admin':
        staff_members = staff_members.filter(is_superuser=True)
    elif role_filter == 'staff':
        staff_members = staff_members.filter(is_superuser=False)

    # Get status filter
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        staff_members = staff_members.filter(is_active=True)
    elif status_filter == 'inactive':
        staff_members = staff_members.filter(is_active=False)

    # Get sorting parameter
    sort_by = request.GET.get('sort', 'date_joined')
    sort_direction = request.GET.get('direction', 'asc')
    
    if sort_by == 'name':
        sort_field = 'first_name'
    elif sort_by == 'email':
        sort_field = 'email'
    elif sort_by == 'role':
        sort_field = 'is_superuser'
    else:
        sort_field = 'date_joined'

    if sort_direction == 'desc':
        sort_field = f'-{sort_field}'
    
    staff_members = staff_members.order_by(sort_field)

    context = {
        'staff_members': staff_members,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'sort_direction': sort_direction
    }
    return render(request, 'bmts/staff.html', context)

@login_required
def add_staff(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')

        try:
            # Check if email already exists
            if Staff.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists.')
                return redirect('bmts:staff')

            staff = Staff.objects.create(
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_staff=True
            )
            staff.set_password(password)
            
            if role == 'admin':
                staff.is_superuser = True
            
            staff.save()
            messages.success(request, 'Staff member added successfully.')
        except Exception as e:
            messages.error(request, f'Error adding staff member: {str(e)}')
        
        return redirect('bmts:staff')
    
    return redirect('bmts:staff')

@login_required
def edit_staff(request, staff_id):
    if request.method == 'POST':
        staff = get_object_or_404(Staff, id=staff_id)
        
        staff.first_name = request.POST.get('first_name')
        staff.last_name = request.POST.get('last_name')
        staff.email = request.POST.get('email')
        
        role = request.POST.get('role')
        if role == 'admin':
            staff.is_superuser = True
            staff.is_staff = True
        else:
            staff.is_superuser = False
            staff.is_staff = True

        # Only update password if a new one is provided
        new_password = request.POST.get('password')
        if new_password:
            staff.set_password(new_password)

        try:
            staff.save()
            messages.success(request, 'Staff member updated successfully.')
        except Exception as e:
            messages.error(request, f'Error updating staff member: {str(e)}')

        return redirect('bmts:staff')
    
    return redirect('bmts:staff')

@login_required
def delete_staff(request, staff_id):
    if request.method == 'POST':
        staff = get_object_or_404(Staff, id=staff_id)
        try:
            staff.delete()
            messages.success(request, 'Staff member deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting staff member: {str(e)}')
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@login_required
def index(request):
    # Get date ranges
    today = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    past_30_days = today - timedelta(days=30)  # Moved this up

    # Active staff count
    active_staff_count = Staff.objects.filter(
        id__in=[request.user.id],
        is_staff=True,
        is_active=True
    ).count()

    # Get pending tickets count and calculate average resolution time
    pending_tickets_count = MaintenanceTicket.objects.filter(status='Open').count()
    closed_tickets = MaintenanceTicket.objects.filter(
        status='Closed',
        date_closed__isnull=False,
        date_submitted__isnull=False
    )

    if closed_tickets.exists():
        total_resolution_time = timedelta()
        ticket_count = 0
        for ticket in closed_tickets:
            resolution_time = ticket.date_closed - ticket.date_submitted
            total_resolution_time += resolution_time
            ticket_count += 1

        avg_resolution_time = total_resolution_time / ticket_count
        total_minutes = int(avg_resolution_time.total_seconds() // 60)
        days = total_minutes // (24 * 60)
        hours = (total_minutes % (24 * 60)) // 60
        minutes = total_minutes % 60

        time_parts = []
        if days > 0:
            time_parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            time_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0 or not time_parts:
            time_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            
        avg_time_display = ", ".join(time_parts)
    else:
        avg_time_display = "No completed tickets"

    # Count tickets submitted today
    today_submitted_count = MaintenanceTicket.objects.filter(
        date_submitted__date=today
    ).count()

    # Calculate submitted tickets average
    submitted_tickets_by_day = MaintenanceTicket.objects.filter(
        date_submitted__gte=past_30_days
    ).dates('date_submitted', 'day')
    
    total_submitted_days = len(set(submitted_tickets_by_day))
    total_submitted = MaintenanceTicket.objects.filter(
        date_submitted__gte=past_30_days
    ).count()

    if total_submitted_days > 0:
        daily_submitted_avg = total_submitted / total_submitted_days
        daily_submitted_avg_display = f"{daily_submitted_avg:.1f}"
    else:
        daily_submitted_avg_display = "0"

    # Count tickets closed today
    today_closed_count = MaintenanceTicket.objects.filter(
        status='Closed',
        date_closed__date=today
    ).count()

    # Calculate closed tickets average
    closed_tickets_by_day = MaintenanceTicket.objects.filter(
        status='Closed',
        date_closed__gte=past_30_days
    ).dates('date_closed', 'day')
    
    total_closed_days = len(set(closed_tickets_by_day))
    total_closed = MaintenanceTicket.objects.filter(
        status='Closed',
        date_closed__gte=past_30_days
    ).count()

    if total_closed_days > 0:
        daily_closed_avg = total_closed / total_closed_days
        daily_avg_display = f"{daily_closed_avg:.1f}"
    else:
        daily_avg_display = "0"

    # Get recent tickets
    recent_tickets = MaintenanceTicket.objects.all().order_by('-date_submitted')[:3]

    context = {
        'active_staff_count': active_staff_count,
        'pending_tickets_count': pending_tickets_count,
        'avg_time_display': avg_time_display,
        'recent_tickets': recent_tickets,
        'today_submitted_count': today_submitted_count,
        'daily_submitted_avg_display': daily_submitted_avg_display,
        'today_closed_count': today_closed_count,
        'daily_avg_display': daily_avg_display,
    }
    return render(request, 'bmts/index.html', context)

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

@login_required
def open_tickets(request):
    if request.method == 'POST':
        ticket_ids = request.POST.getlist('ticket_ids')
        if ticket_ids:
            MaintenanceTicket.objects.filter(id__in=ticket_ids).update(
                status='Closed',
                date_closed=timezone.now()
            )
            messages.success(request, f'{len(ticket_ids)} ticket(s) marked as closed.')
        return redirect('bmts:open_tickets')

    tickets = MaintenanceTicket.objects.filter(status='Open').order_by('-date_submitted')
    return render(request, 'bmts/open_tickets.html', {'tickets': tickets})