import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Avg, OuterRef, Max, Subquery, Sum, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .forms import CustomUserCreationForm, LoginForm, ProfileForm, ReviewForm, CategoryForm, AddBalanceForm, \
    ProviderForm, MessageForm, BookingForm
from .models import Profile, Provider, Service, Category, Message, Booking, Chat, Notification

logger = logging.getLogger(__name__)

def pendingservices(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return HttpResponseForbidden("You are not authorized to view this page.")
    services_pending = Service.objects.filter(approval='pending approval')
    return render(request, 'pendingservices.html', {'services_pending': services_pending})


def approve_service(request, service_id):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return HttpResponseForbidden("You are not authorized to view this page.")
    if request.method == "POST":
        service = get_object_or_404(Service, id=service_id)
        service.approval = 'approved'
        service.save()

        notification = Notification.objects.create(
            recipient=service.provider.profile,
            message=f"Your service '{service.title}' has been approved by an administrator and is now visible to customers.",
            url = reverse('myservices'),
        )
        # logger.debug(f"Notification created: {notification}")

        return redirect('pendingservices')


def reject_service(request, service_id):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return HttpResponseForbidden("You are not authorized to view this page.")
    if request.method == "POST":
        service = get_object_or_404(Service, id=service_id)
        service.approval = 'not approved'
        service.save()

        Notification.objects.create(
            recipient=service.provider.profile,
            message=f"Your service '{service.title}' has been rejected by an administrator.",
            url=reverse('myservices')
        )

        return redirect('pendingservices')

def users(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return HttpResponseForbidden("You are not authorized to view this page.")
    users = Profile.objects.all()
    return render(request, 'users.html', {'users': users})

def ban_user(request, user_id):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return HttpResponseForbidden("You are not authorized to view this page.")
    if request.method == "POST":
        user = get_object_or_404(User, id=user_id)
        user.delete()  # Remove o usuário e, por cascade, o Profile e o Provider (se existir)
        return redirect('users')

def myservices(request):
    user_profile = get_object_or_404(Profile, user=request.user)
    provider = get_object_or_404(Provider, profile=user_profile)
    categories = Category.objects.all()  # Fetch categories here

    # Receber parâmetros de filtro da URL
    search_name = request.GET.get('search_name', '').strip()
    filter_status = request.GET.get('filter_status', '').strip()

    # Base queryset com os serviços do provedor
    user_services = Service.objects.filter(provider=provider)

    # Filtrar por nome de serviço
    if search_name:
        user_services = user_services.filter(title__icontains=search_name)

    # Preparar a lista de serviços com contagens de reservas
    services_with_counts = []
    for service in user_services:
        bookings_to_approve_count = Booking.objects.filter(
            service=service, status='pending', accepted_at__isnull=True
        ).count()
        bookings_in_progress_count = Booking.objects.filter(
            service=service, status='in_progress', accepted_at__isnull=False
        ).count()

        # Aplicar filtro por status das reservas
        if filter_status == 'bookings_to_approve' and bookings_to_approve_count == 0:
            continue
        elif filter_status == 'bookings_in_progress' and bookings_in_progress_count == 0:
            continue

        services_with_counts.append({
            'service': service,
            'bookings_to_approve_count': bookings_to_approve_count,
            'bookings_in_progress_count': bookings_in_progress_count
        })

    return render(request, 'myservices.html', {
        'services_with_counts': services_with_counts,
        'categories': categories,
    })

def categories(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return HttpResponseForbidden("You are not authorized to view this page.")
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('categories')
    else:
        form = CategoryForm()

    categories = Category.objects.all()
    return render(request, 'categories.html', {'categories': categories, 'form': form})

def providers(request):
    providers = Provider.objects.all()
    return render(request, 'providers.html', {'providers': providers})


def edit_service(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    categories = Category.objects.all()

    if request.method == 'POST':
        service.title = request.POST.get('title')
        service.description = request.POST.get('description')
        service.price = request.POST.get('price')
        service.category_id = request.POST.get('category')

        if 'image' in request.FILES:
            service.image = request.FILES['image']

        service.save()
        return redirect('myservices')

    return render(request, 'myservices.html', {'service': service, 'categories': categories})
    #return redirect('myservices')


@login_required
def add_service(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        duration_minutes = int(request.POST.get('duration', 0))
        category_id = request.POST.get('category')
        image = request.FILES.get('image')

        # Convert duration to timedelta
        duration = timedelta(minutes=duration_minutes)

        # Get the user’s profile and provider
        profile = Profile.objects.get(user=request.user)
        provider, created = Provider.objects.get_or_create(profile=profile)

        # Create and save new service with the correct provider instance
        service = Service(
            provider=provider,
            title=title,
            description=description,
            price=price,
            duration=duration,
            category_id=category_id,
            is_active=True,
            approval='pending approval',
            image=image
        )
        service.save()

        return redirect('myservices')

    return render(request, 'myservices.html', {'categories': categories})

def delete_service(request, service_id):
    service = Service.objects.get(pk=service_id)
    service.delete()
    return redirect('myservices')


def get_service_data(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    categories = Category.objects.all()

    data = {
        'title': service.title,
        'description': service.description,
        'category': service.category.id,
        'price': str(service.price),
        'image': service.image.url if service.image else None,
        'categories': [{'id': cat.id, 'name': cat.name} for cat in categories],
    }
    return JsonResponse(data)


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('/')
            else:
                form.add_error(None, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Account created successfully for {user.username}!")
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, "Error creating account. Please check the inserted data.")
    else:
        form = CustomUserCreationForm()

    return render(request, 'register.html', {'form': form})

@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    messages.success(request, "You have logged out successfully!")
    return redirect('index')


def top_categories(limit=5):
    """Retorna as categorias com mais vendas."""
    return (
        Category.objects.annotate(total_sales=Count('service__booking'))
        .order_by('-total_sales')[:limit]
    )

def leaderboard(limit=5):
    """Retorna os providers com mais vendas (independente do mês)."""
    return (
        Provider.objects.annotate(
            total_sales=Count(
                'services__booking',
                filter=Q(services__booking__status='completed')
            )
        )
        .filter(total_sales__gt=0)
        .order_by('-total_sales')[:limit]
    )

def home(request):
    total_users = User.objects.count()
    total_services = Service.objects.count()
    total_reviews = Booking.objects.filter(status='completed').count()
    total_revenue = Booking.objects.filter(status='completed').aggregate(total=Sum('service__price'))['total'] or 0
    total_providers = Provider.objects.count()
    total_services_provided = Booking.objects.filter(status='completed').count()

    context = {
        'total_users': total_users,
        'total_services': total_services,
        'total_reviews': total_reviews,
        'total_revenue': total_revenue,
        'total_providers': total_providers,
        'total_services_provided': total_services_provided,
        'recent_bookings': Booking.objects.order_by('-created_at')[:5],
        'providers': Provider.objects.annotate(total_sales=Count('services__booking')).order_by('-total_sales')[:3],
    }

    return render(request, 'index.html', context)

def myorders(request):
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return redirect('login')

    # Get bookings grouped by status
    pending_bookings = Booking.objects.filter(customer=request.user.profile, status='pending').select_related('service', 'service__provider')
    in_progress_bookings = Booking.objects.filter(customer=request.user.profile, status='in_progress').select_related('service', 'service__provider')
    completed_bookings = Booking.objects.filter(customer=request.user.profile, status='completed').select_related('service', 'service__provider')
    cancelled_bookings = Booking.objects.filter(customer=request.user.profile, status='cancelled').select_related('service', 'service__provider')

    context = {
        'pending_bookings': pending_bookings,
        'in_progress_bookings': in_progress_bookings,
        'completed_bookings': completed_bookings,
        'cancelled_bookings': cancelled_bookings,
    }
    return render(request, 'myorders.html', context)

def services(request):
    # Get filter parameters from request
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '0')
    sort_option = request.GET.get('sort', '0')

    # Start with approved services only
    services = Service.objects.filter(approval='approved').select_related(
        'provider',
        'provider__profile',
        'provider__profile__user',
        'category'
    ).prefetch_related('provider__reviews')

    # Filter by search query
    if search_query:
        services = services.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )

    # Filter by category if selected
    if category_id and category_id != '0':
        services = services.filter(category_id=category_id)

    # Apply sorting
    if sort_option == '1':  # Most Popular
        services = services.order_by('-popularity')
    elif sort_option == '2':  # Price: Low to High
        services = services.order_by('price')
    elif sort_option == '3':  # Price: High to Low
        services = services.order_by('-price')
    else:  # Most Recent
        services = services.order_by('-created_at')

    services = services.annotate(avg_rating=Avg('provider__reviews__rating'))

    categories = Category.objects.all()
    context = {
        'title': 'Services',
        'services': services,
        'categories': categories,
        'search_query': search_query,
        'category_id': category_id,
        'sort_option': sort_option,
    }
    return render(request, 'services.html', context)

def service_detail(request, service_id):
    service = get_object_or_404(Service, id=service_id, is_active=True, approval='approved')

    # Calcular a média das avaliações do provedor
    avg_rating = service.provider.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    booking_form = BookingForm()

    context = {
        'service': service,
        'avg_rating': avg_rating,
        'booking_form': booking_form,
    }
    return render(request, 'service_detail.html', context)

def booking(request):
    return render(request, 'booking.html')

def profile(request, username):
    # Get the user's profile
    user_profile = get_object_or_404(Profile, user__username=username)

    profile_form = ProfileForm(instance=user_profile)
    provider_form = None
    if hasattr(user_profile, 'provider'):
        provider_form = ProviderForm(instance=user_profile.provider)
    review_form = ReviewForm()
    add_balance_form = AddBalanceForm()

    booking_history = Booking.objects.filter(customer=user_profile).select_related('service').order_by('-created_at')

    provider = user_profile.provider if hasattr(user_profile, 'provider') else None
    is_provider = provider is not None
    approved_services = provider.services.filter(approval='approved') if is_provider else None
    avg_rating = provider.reviews.aggregate(Avg('rating'))['rating__avg'] if is_provider else None
    reviews = provider.reviews.all() if is_provider else None

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = ProfileForm(request.POST, request.FILES, instance=user_profile)
            if profile_form.is_valid():
                profile_form.save()
                return redirect('profile', username=username)

        elif 'update_provider' in request.POST and is_provider:  # Pr
            provider_form = ProviderForm(request.POST, request.FILES, instance=user_profile.provider)
            if provider_form.is_valid():
                provider_form.save()
                return redirect('profile', username=username)

        elif 'add_review' in request.POST and is_provider:  # Review Form
            review_form = ReviewForm(request.POST)
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.provider = provider
                review.reviewer = request.user.profile
                review.save()

                Notification.objects.create(
                    recipient=user_profile.provider.profile,
                    message=f"You have received a new review from {request.user.username} for the service '{review.provider.services.first().title}'.",
                    url=reverse('profile', kwargs={'username': user_profile.user.username})
                )

                return redirect('profile', username=username)

        elif 'add_balance' in request.POST:
            add_balance_form = AddBalanceForm(request.POST)
            if add_balance_form.is_valid():
                amount = add_balance_form.cleaned_data['amount']
                user_profile.wallet += amount
                user_profile.save()
                return redirect('profile', username=username)

    context = {
        'profile': user_profile,
        'is_provider': is_provider,
        'services': approved_services,
        'avg_rating': avg_rating,
        'reviews': reviews,
        'profile_form': profile_form,
        'provider_form': provider_form,
        'review_form': review_form,
        'add_balance_form': add_balance_form,
        'booking_history': booking_history if request.user == user_profile.user else None,
    }
    return render(request, 'profile.html', context)

@login_required
def chat_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    chat, created = Chat.objects.get_or_create(booking=booking)

    # Ensure only the customer or provider can access the chat
    if request.user.profile not in [booking.customer, booking.service.provider.profile]:
        messages.error(request, "You are not authorized to access this chat.")
        return redirect('home')

    # Rename the variable to avoid conflicts with Django messages
    chat_messages = chat.messages.order_by('timestamp')

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.chat = chat
            message.sender = request.user.profile
            message.recipient = (
                booking.service.provider.profile
                if request.user.profile == booking.customer
                else booking.customer
            )
            message.save()

            Notification.objects.create(
                recipient=message.recipient,
                message=f"{message.sender.user.username} sent a new message in the chat for the service '{booking.service.title}'.",
                url = reverse('chat_view', kwargs={'booking_id': booking.id})
            )

            messages.success(request, "Message sent successfully.")
            return redirect('chat_view', booking_id=booking.id)
    else:
        form = MessageForm()

    context = {
        'chat': chat,
        'booking': booking,
        'chat_messages': chat_messages,
        'form': form,
    }
    return render(request, 'chat.html', context)


def message_thread(request, recipient_id):
    recipient = get_object_or_404(Profile, id=recipient_id)
    messages = Message.objects.filter(
        (Q(sender=request.user.profile) & Q(recipient=recipient)) |
        (Q(sender=recipient) & Q(recipient=request.user.profile))
    ).order_by('timestamp')

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user.profile
            message.recipient = recipient
            message.save()
            return redirect('message_thread', recipient_id=recipient_id)
    else:
        form = MessageForm()

    context = {
        'messages': messages,
        'form': form,
        'recipient': recipient,
    }
    return render(request, 'message_thread.html', context)


def edit_profile(request, user_id):
    profile = get_object_or_404(Profile, user__id=user_id)

    # Ensure only the profile owner can edit
    if request.user != profile.user:
        return redirect('profile', username=profile.user.username)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile', username=profile.user.username)
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'profile.html', {'form': form, 'profile': profile})

@login_required
def book_service(request, service_id):
    service = get_object_or_404(Service, id=service_id, is_active=True, approval='approved')
    user_profile = request.user.profile

    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            scheduled_time = form.cleaned_data.get('scheduled_time')

            # Check if the booking time is in the future
            if scheduled_time < now():
                messages.error(request, "You cannot book a service in the past. Please select a valid time.")
                return redirect('service_detail', service_id=service_id)

            # Check if the user has enough balance
            if user_profile.wallet < service.price:
                messages.error(request, "You don't have enough balance to book this service. Please add funds to your wallet.")
                return redirect('service_detail', service_id=service_id)

            user_profile.wallet -= service.price
            user_profile.save()

            # Create the booking
            booking = form.save(commit=False)
            booking.service = service
            booking.customer = user_profile
            booking.save()

            # Notify the provider
            Notification.objects.create(
                recipient=service.provider.profile,
                message=f"New booking for the service '{service.title}'.",
                booking=booking,
                action_required=True,
                url=reverse('pending_bookings', kwargs={'service_id': service.id}),
            )
            messages.success(request, "Booking successful! Your request has been sent to the provider.")
            return redirect('service_detail', service_id=service_id)
        else:
            messages.error(request, "Invalid booking details. Please correct the errors and try again.")
            return redirect('service_detail', service_id=service_id)

    else:
        form = BookingForm()

    return render(request, 'service_detail.html', {'service': service, 'form': form})

@login_required
def update_booking_status(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.user.profile != booking.customer:
        messages.error(request, "You do not have permission to change the status of this booking.")
        return redirect('profile', username=request.user.username)

    if not booking.accepted_at:
        messages.warning(request, "This booking has not been accepted by the provider yet.")
        return redirect('profile', username=request.user.username)

    if booking.status != 'completed':
        booking.status = 'completed'
        booking.save()

        provider_profile = booking.service.provider.profile
        provider_profile.wallet += booking.service.price
        provider_profile.save()

        Notification.objects.create(
            recipient=provider_profile,
            message=f"The booking for the service '{booking.service.title}' has been marked as completed by the customer."
        )

        messages.success(request, "Booking status updated to 'completed' and amount deposited in wallet.")
    else:
        messages.info(request, "This booking has already been marked as completed.")

    return redirect('myorders')


@login_required
def notifications(request):
    user_profile = Profile.objects.get(user=request.user)

    # Count unread notifications
    unread_notifications_count = user_profile.notifications.filter(read=False).count()

    # Get representative notifications with a count
    representative_ids = Notification.objects.filter(
        message=OuterRef('message'),
        read=OuterRef('read'),
        recipient=user_profile
    ).values('id')[:1]

    notifications = (
        user_profile.notifications
        .values('message', 'read', 'url')
        .annotate(
            count=Count('id'),
            latest_created_at=Max('created_at'),
            representative_id=Subquery(representative_ids),
        )
        .order_by('read', '-latest_created_at')
    )

    return render(request, 'notifications.html', {
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    })


@login_required
def mark_notification_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user.profile)
    notification.read = True
    notification.save()
    messages.success(request, "Notification marked as read.")

    # Redirect to the provided URL if it exists
    redirect_url = request.POST.get('redirect', 'notifications')
    return redirect(redirect_url)


@login_required
def pending_bookings(request, service_id):
    service = get_object_or_404(Service, id=service_id, provider__profile__user=request.user)
    pending_bookings = Booking.objects.filter(service=service, status='pending', accepted_at__isnull=True)
    return render(request, 'pending_bookings.html', {'bookings': pending_bookings, 'service': service})

@login_required
def in_progress_bookings(request, service_id):
    service = get_object_or_404(Service, id=service_id, provider__profile__user=request.user)
    in_progress_bookings = Booking.objects.filter(service=service, status='in_progress', accepted_at__isnull=False)
    return render(request, 'in_progress_bookings.html', {'bookings': in_progress_bookings, 'service': service})

@login_required
def accept_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, service__provider__profile__user=request.user)

    # Update the booking status and approval
    booking.accepted_at = timezone.now()
    booking.status = 'in_progress'
    booking.save()

    Notification.objects.create(
        recipient=booking.customer,
        message=f"Your request for the service '{booking.service.title}' has been accepted by the provider and is now in progress.",
        url = reverse('myorders')
    )

    # Confirmation message
    messages.success(request, "Booking accepted successfully.")
    return redirect('pending_bookings', service_id=booking.service.id)

@login_required
def reject_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, service__provider__profile__user=request.user)
    booking.status = 'cancelled'
    booking.save()

    Notification.objects.create(
        recipient=booking.customer,
        message=f"Your request for the service '{booking.service.title}' was rejected by the provider.",
        url = reverse('myorders')
    )

    messages.success(request, "Booking rejected successfully.")
    return redirect('pending_bookings', service_id=booking.service.id)

def user_chats(request):
    profile = request.user.profile
    customer_chats = Chat.objects.filter(
        booking__customer=profile,
        booking__status='in_progress'
    ).select_related('booking__service', 'booking__service__provider')

    provider_chats = Chat.objects.filter(
        booking__service__provider__profile=profile,
        booking__status='in_progress'
    ).select_related('booking__customer')

    context = {
        'customer_chats': customer_chats,
        'provider_chats': provider_chats,
    }
    return render(request, 'user_chats.html', context)
