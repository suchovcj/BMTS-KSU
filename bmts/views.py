from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import StaffLoginForm
from .forms import MaintenanceTicketForm
from django.contrib import messages
from .models import MaintenanceTicket, Staff, Building, Bathroom, QRCode
from django.db.models import F, Q, Count
from django.utils import timezone
from django.contrib.auth import get_user_model  # Add this line
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.core.files.base import ContentFile
import qrcode
from io import BytesIO
from django.db.models import Count
from django.db.models.functions import TruncDate
import csv
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import json

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
    # If user is not admin, redirect to staff dashboard
    if not request.user.is_superuser:
        return redirect('bmts:staff_dashboard')
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
                # Redirect based on user role
                if user.is_superuser:
                    return redirect('bmts:index')
                else:
                    return redirect('bmts:staff_dashboard')
    else:
        form = StaffLoginForm()
    return render(request, 'bmts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('bmts:login')

# views.py
def create_ticket(request):
    if request.method == 'POST':
        try:
            MaintenanceTicket.objects.create(
                bathroom_number=request.POST.get('bathroom-number'),
                email=request.POST.get('email'),
                description=request.POST.get('description'),
                status='Open'
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return render(request, 'bmts/create_ticket.html')

@login_required
def open_tickets(request):
    if request.method == 'POST':
        ticket_ids = request.POST.getlist('ticket_ids')
        if ticket_ids:
            MaintenanceTicket.objects.filter(id__in=ticket_ids).update(
                status='Closed',
                date_closed=timezone.now(),
                closed_by=request.user
            )
            messages.success(request, f'{len(ticket_ids)} ticket(s) marked as closed.')
        return redirect('bmts:open_tickets')

    tickets = MaintenanceTicket.objects.filter(status='Open').order_by('-date_submitted')
    return render(request, 'bmts/open_tickets.html', {'tickets': tickets})

@login_required
def facilities(request):
    # Get initial querysets
    buildings = Building.objects.all().order_by('name')
    bathrooms = Bathroom.objects.all().order_by('building__name', 'floor')

    # Handle search
    search_query = request.GET.get('search', '')
    if search_query:
        buildings = buildings.filter(
            Q(name__icontains=search_query) |
            Q(building_id__icontains=search_query) |
            Q(description__icontains=search_query)
        )
        bathrooms = bathrooms.filter(
            Q(name__icontains=search_query) |
            Q(bathroom_number__icontains=search_query) |
            Q(building__name__icontains=search_query)
        )

    # Handle building filter
    building_filter = request.GET.get('building_filter', '')
    if building_filter:
        bathrooms = bathrooms.filter(building_id=building_filter)

    # Handle floor filter
    floor_filter = request.GET.get('floor_filter', '')
    if floor_filter:
        bathrooms = bathrooms.filter(floor=floor_filter)

    # Handle POST requests
    if request.method == 'POST':
        if 'add_building' in request.POST:
            try:
                Building.objects.create(
                    name=request.POST.get('building_name'),
                    description=request.POST.get('building_description'),
                    building_id=request.POST.get('building_id'),
                    number_of_floors=request.POST.get('number_of_floors'),
                    number_of_bathrooms=request.POST.get('number_of_bathrooms')
                )
                messages.success(request, 'Building added successfully.')
            except Exception as e:
                messages.error(request, f'Error adding building: {str(e)}')
            return redirect('bmts:facilities')

        elif 'add_bathroom' in request.POST:
            try:
                building = Building.objects.get(id=request.POST.get('building'))
                Bathroom.objects.create(
                    name=request.POST.get('bathroom_name'),
                    bathroom_number=request.POST.get('bathroom_number'),
                    building=building,
                    floor=request.POST.get('floor')
                )
                messages.success(request, 'Bathroom added successfully.')
            except Exception as e:
                messages.error(request, f'Error adding bathroom: {str(e)}')
            return redirect('bmts:facilities')

        elif 'edit_building' in request.POST:
            try:
                building = get_object_or_404(Building, id=request.POST.get('building_id'))
                building.name = request.POST.get('building_name')
                building.description = request.POST.get('building_description')
                building.building_id = request.POST.get('building_id_number')
                building.number_of_floors = request.POST.get('number_of_floors')
                building.number_of_bathrooms = request.POST.get('number_of_bathrooms')
                building.save()
                messages.success(request, 'Building updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating building: {str(e)}')
            return redirect('bmts:facilities')

        elif 'edit_bathroom' in request.POST:
            try:
                bathroom = get_object_or_404(Bathroom, id=request.POST.get('bathroom_id'))
                bathroom.name = request.POST.get('bathroom_name')
                bathroom.bathroom_number = request.POST.get('bathroom_number')
                bathroom.building_id = request.POST.get('building')
                bathroom.floor = request.POST.get('floor')
                bathroom.save()
                messages.success(request, 'Bathroom updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating bathroom: {str(e)}')
            return redirect('bmts:facilities')

        elif 'delete_building' in request.POST:
            try:
                building = get_object_or_404(Building, id=request.POST.get('building_id'))
                building.delete()
                messages.success(request, 'Building deleted successfully.')
            except Exception as e:
                messages.error(request, f'Error deleting building: {str(e)}')
            return redirect('bmts:facilities')

        elif 'delete_bathroom' in request.POST:
            try:
                bathroom = get_object_or_404(Bathroom, id=request.POST.get('bathroom_id'))
                bathroom.delete()
                messages.success(request, 'Bathroom deleted successfully.')
            except Exception as e:
                messages.error(request, f'Error deleting bathroom: {str(e)}')
            return redirect('bmts:facilities')

    # Get unique floors for filter
    floor_choices = bathrooms.values_list('floor', flat=True).distinct().order_by('floor')

    context = {
        'buildings': buildings,
        'bathrooms': bathrooms,
        'floor_choices': floor_choices,
        'search_query': search_query,
        'building_filter': building_filter,
        'floor_filter': floor_filter,
    }
    return render(request, 'bmts/facilities.html', context)
 
@login_required
def qr_codes(request):
    bathrooms = Bathroom.objects.all().order_by('building__name', 'bathroom_number')
    qr_codes = QRCode.objects.all().order_by('-created_at')

    if request.method == 'POST':
        if 'generate_qr' in request.POST:
            try:
                bathroom_id = request.POST.get('bathroom')
                bathroom = Bathroom.objects.get(id=bathroom_id)
                base_url = request.build_absolute_uri('/').rstrip('/')
                qr_url = f"{base_url}/maintenance-request/{bathroom.id}/"
                
                # Generate QR code image
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(qr_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Save to BytesIO
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                
                # Create QR code object
                qr_code = QRCode(
                    bathroom=bathroom,
                    title=f"Maintenance Request - {bathroom.building.name} Bathroom {bathroom.bathroom_number}",
                    description=f"Scan for maintenance request - {bathroom.building.name} - {bathroom.bathroom_number}",
                    url=qr_url
                )
                
                # Save file
                file_name = f'qr-{bathroom.building.name}-{bathroom.bathroom_number}.png'
                qr_code.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=True)
                messages.success(request, 'QR Code generated successfully.')
            except Exception as e:
                messages.error(request, f'Error generating QR code: {str(e)}')
            return redirect('bmts:qr_codes')

    return render(request, 'bmts/qr_codes.html', {
        'bathrooms': bathrooms,
        'qr_codes': qr_codes
    })

@login_required
def print_qr_codes(request):
    if request.method == 'POST':
        selected_codes = request.POST.getlist('selected_codes')
        qr_codes = QRCode.objects.filter(id__in=selected_codes)
        return render(request, 'bmts/print_qr_codes.html', {'qr_codes': qr_codes})
    return redirect('bmts:qr_codes')


@login_required
def reports(request):
    # Basic counts and initial data
    total_tickets_count = MaintenanceTicket.objects.count()
    closed_tickets = MaintenanceTicket.objects.filter(
        status='Closed',
        date_closed__isnull=False
    )

    # Average resolution time calculation
    avg_resolution_display = "N/A"
    if closed_tickets.exists():
        total_resolution_time = timedelta(0)
        for ticket in closed_tickets:
            resolution_time = ticket.date_closed - ticket.date_submitted
            total_resolution_time += resolution_time
        avg_resolution_time = total_resolution_time / closed_tickets.count()
        avg_resolution_hours = avg_resolution_time.total_seconds() / 3600
        
        if avg_resolution_hours >= 24:
            avg_resolution_display = f"{int(avg_resolution_hours/24)}d {int(avg_resolution_hours%24)}h"
        else:
            avg_resolution_display = f"{int(avg_resolution_hours)}h"

    # Resolution rate
    resolution_rate = (closed_tickets.count() / total_tickets_count * 100) if total_tickets_count > 0 else 0

    # Weekly comparison
    this_week = timezone.now().date() - timedelta(days=7)
    last_week = this_week - timedelta(days=7)
    
    tickets_this_week = MaintenanceTicket.objects.filter(
        date_submitted__gte=this_week
    ).count()
    
    tickets_last_week = MaintenanceTicket.objects.filter(
        date_submitted__gte=last_week,
        date_submitted__lt=this_week
    ).count()
    
    tickets_week_change = (
        ((tickets_this_week - tickets_last_week) / tickets_last_week * 100)
        if tickets_last_week > 0 else 0
    )

    # Staff Performance Report
    staff_performance = (
        MaintenanceTicket.objects
        .filter(status='Closed')
        .values('closed_by__first_name', 'closed_by__last_name')
        .annotate(tickets_closed=Count('id'))
        .order_by('-tickets_closed')
    )

    # Bathroom Activity Report
    bathroom_activity = (
        MaintenanceTicket.objects
        .values('bathroom_number')
        .annotate(total_tickets=Count('id'))
        .order_by('-total_tickets')
    )

    # Daily trend data (last 14 days)
    daily_trend = (
        MaintenanceTicket.objects
        .filter(date_submitted__gte=timezone.now() - timedelta(days=14))
        .annotate(date=TruncDate('date_submitted'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    # Convert dates to strings for JSON serialization
    daily_trend_data = [
        {
            'date': item['date'].strftime('%Y-%m-%d'),
            'count': item['count']
        } for item in daily_trend
    ]

    # Resolution time distribution
    resolution_distribution = {
        '< 1 day': closed_tickets.filter(date_closed__lt=F('date_submitted') + timedelta(days=1)).count(),
        '1-2 days': closed_tickets.filter(
            date_closed__gte=F('date_submitted') + timedelta(days=1),
            date_closed__lt=F('date_submitted') + timedelta(days=2)
        ).count(),
        '2-3 days': closed_tickets.filter(
            date_closed__gte=F('date_submitted') + timedelta(days=2),
            date_closed__lt=F('date_submitted') + timedelta(days=3)
        ).count(),
        '3+ days': closed_tickets.filter(
            date_closed__gte=F('date_submitted') + timedelta(days=3)
        ).count()
    }
    
    status_counts = {
        'Open': MaintenanceTicket.objects.filter(status='Open').count(),
        'Closed': MaintenanceTicket.objects.filter(status='Closed').count()
    }

    status_data = [
        {'name': status, 'value': count}
        for status, count in status_counts.items()
    ]

    # Prepare the context
    context = {
        'staff_performance': staff_performance,
        'bathroom_activity': bathroom_activity,
        'total_tickets_count': total_tickets_count,
        'avg_resolution_time': avg_resolution_display,
        'resolution_rate': resolution_rate,
        'tickets_this_week': tickets_this_week,
        'tickets_week_change': tickets_week_change,
        'daily_trend_json': json.dumps(daily_trend_data),
        'resolution_distribution_json': json.dumps([
            {'name': k, 'value': v} for k, v in resolution_distribution.items()
        ]),
        'staff_performance_json': json.dumps(list(staff_performance)),
        'bathroom_activity_json': json.dumps(list(bathroom_activity)),
        'status_data_json': json.dumps(status_data)
    }

    return render(request, 'bmts/reports.html', context)

@login_required
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bmts_report.csv"'

    writer = csv.writer(response)
    
    # Write Staff Performance
    writer.writerow(['Staff Performance Report'])
    writer.writerow(['Staff Member', 'Tickets Closed'])
    staff_performance = (
        MaintenanceTicket.objects
        .filter(status='Closed')
        .values('closed_by__first_name', 'closed_by__last_name')
        .annotate(tickets_closed=Count('id'))
    )
    for staff in staff_performance:
        writer.writerow([
            f"{staff['closed_by__first_name']} {staff['closed_by__last_name']}",
            staff['tickets_closed']
        ])
    
    writer.writerow([])  # Empty row for spacing
    
    # Write Bathroom Activity
    writer.writerow(['Bathroom Activity Report'])
    writer.writerow(['Bathroom Number', 'Total Tickets'])
    bathroom_activity = (
        MaintenanceTicket.objects
        .values('bathroom_number')
        .annotate(total_tickets=Count('id'))
    )
    for bathroom in bathroom_activity:
        writer.writerow([
            bathroom['bathroom_number'],
            bathroom['total_tickets']
        ])

    return response

@login_required
def export_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="bmts_report.pdf"'
    
    # Create PDF document
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []

    # Staff Performance Data
    staff_performance = (
        MaintenanceTicket.objects
        .filter(status='Closed')
        .values('closed_by__first_name', 'closed_by__last_name')
        .annotate(tickets_closed=Count('id'))
    )
    
    staff_data = [['Staff Member', 'Tickets Closed']]
    for staff in staff_performance:
        staff_data.append([
            f"{staff['closed_by__first_name']} {staff['closed_by__last_name']}",
            str(staff['tickets_closed'])
        ])

    # Bathroom Activity Data
    bathroom_activity = (
        MaintenanceTicket.objects
        .values('bathroom_number')
        .annotate(total_tickets=Count('id'))
    )
    
    bathroom_data = [['Bathroom Number', 'Total Tickets']]
    for bathroom in bathroom_activity:
        bathroom_data.append([
            bathroom['bathroom_number'],
            str(bathroom['total_tickets'])
        ])

    # Create and style tables
    staff_table = Table(staff_data)
    staff_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    bathroom_table = Table(bathroom_data)
    bathroom_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(staff_table)
    elements.append(bathroom_table)
    
    doc.build(elements)
    return response

@login_required
def staff_dashboard(request):
    # Get basic stats for staff
    pending_tickets_count = MaintenanceTicket.objects.filter(status='Open').count()
    recent_tickets = MaintenanceTicket.objects.all().order_by('-date_submitted')[:5]
    today = timezone.now().date()
    today_closed_count = MaintenanceTicket.objects.filter(
        status='Closed',
        date_closed__date=today
    ).count()

    context = {
        'pending_tickets_count': pending_tickets_count,
        'recent_tickets': recent_tickets,
        'today_closed_count': today_closed_count,
    }
    return render(request, 'bmts/staff_dashboard.html', context)
    