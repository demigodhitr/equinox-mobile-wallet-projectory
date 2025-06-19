from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from .models import *
from django.http import JsonResponse
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required 
from django.contrib.auth import login, authenticate, logout
from django.db import IntegrityError
import requests
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
import random
import json
from decimal import Decimal
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail
from datetime import datetime
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from django.utils.safestring import mark_safe
import secrets
import string
from itertools import chain
from operator import attrgetter
from django.db.models import F, Value, CharField
from django.db.models import Sum

def landing(request):
    return render(request, 'landing.html')

@login_required
def index(request): 
    user = request.user
    try:
        user_profile = Profiles.objects.get(user=user)
    except Profiles.DoesNotExist:
        logout(request)
        return redirect('login')
    cards = CryptoCards.objects.filter(user=user)
    dp = user_profile.profile_pic.url
    notifications = Notifications.objects.filter(user=user, seen=False)
    withdrawals = WithdrawalRequest.objects.filter(user=user).order_by('-created_at')
    deposits = Deposit.objects.filter(user=user).order_by('-created_at')
    investments = Investments.objects.filter(investor=user).order_by('-date')
    total_invested = investments.aggregate(total_amount=Sum('amount'))['total_amount']
    if total_invested is None:
        total_invested = 0.00
    else:
        total_invested = float(total_invested)
    card_requests = CardRequest.objects.filter(user=user).order_by('-date')

    all_activities = sorted(
        chain(
            withdrawals.annotate(activity_date=F('created_at'), activity_type=Value('Withdrawal', output_field=CharField())),
            deposits.annotate(activity_date=F('created_at'), activity_type=Value('Deposit', output_field=CharField())),
            investments.annotate(activity_date=F('date'), activity_type=Value('Investment', output_field=CharField())),
            card_requests.annotate(activity_date=F('date'), activity_type=Value('Card Request', output_field=CharField()))
        ),
        key=attrgetter('activity_date'),
        reverse=True
    )
    key = 'your-api-key'

    gecko_endpoint = 'https://api.coingecko.com/api/v3/coins/markets'
    
    # crypto_ids = ['bitcoin', 'ethereum', 'litecoin', 'ripple', 'cardano', 'tether', 'polygon', 'solana', 'polkadot', 'dogecoin', 'chainlink', 'avalanche', 'uniswap', 'monero', 'tron', 'stellar', 'eos']

    crypto_ids = [
    "bitcoin", "ethereum", "tether", "binancecoin", "cardano",
    "solana", "ripple", "polkadot", "dogecoin", "usd-coin",
    "terra-luna", "chainlink", "bitcoin-cash", "litecoin", "matic-network",
    "stellar", "ethereum-classic", "vechain", "theta-token", "eos",
    "aave", "crypto-com-chain", "filecoin", "tron", "shiba-inu",
    "tezos", "monero", "neo", "dash", "pancakeswap-token",
    "elrond-erd-2", "compound-ether", "ethereum-classic", "ftx-token", "compound-governance-token",
    "the-sandbox", "havven", "uma", "amp"
    ]

    coins_param = {
        'vs_currency': 'GBP',
        'ids': ','.join(crypto_ids),
        'order': 'market_cap_desc',
        'sparkline': 'true',
        'price_change_percentage': '24h',
        'key': key,
    }
    try:
        gecko_response = requests.get(gecko_endpoint, params=coins_param)
    except Exception as e:
        gecko_response = None

    if gecko_response and gecko_response.status_code == 200:
        coins_data = gecko_response.json()
    else:
        coins_data = []
    context = {
        'total_invested':total_invested,
        'investments':investments,
        'cards': cards,
        'activities': all_activities,
        'notifications': notifications,
        'coins': coins_data,
        'profile': user_profile,
        'dp': dp,
    }
    return render(request, 'index.html', context)

def signin(request):
    if request.method == 'POST':
        request.session.setdefault('attempts', 0)
        request.session.setdefault('counter', 4)
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)
        if not username or not password:
            return JsonResponse({'error': 'Cannot authenticate ghost user'}, status=400)
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            try:
                v_obj = is_verified.objects.get(user=user)
            except is_verified.DoesNotExist:
                email = user.email
                return JsonResponse({'verify': 'There was a problem authenticating you. perhaps, you have not verified your account email', 'email':email}, status=404)
            if not v_obj.verified:
                email = v_obj.email
                request.session.setdefault('email', email)
                return JsonResponse({'verify': f'Looks like you have not verified your email: {email}. Please verify it now to ensure you are a legitimate user.', 'email':email}, status=400)
            else:
                user_profile = Profiles.objects.get(user=user)
                if not user_profile.can_login:
                    return JsonResponse({'error': 'You currently do not have permission to log in or you have been restricted. Contact support team for help.'})
                else:
                    request.session.clear()
                    login(request, user)
                    return JsonResponse({'success': 'Fetching your account balances, please wait...'}, status=200)
        else:
            request.session['attempts'] += 1
            request.session['counter'] -= 1
            if request.session['attempts'] >= 4:
                try:
                    user = CustomUser.objects.get(username=username)
                    profile = Profiles.objects.get(user=user)
                    profile.can_login = False
                    profile.save()
                    request.session.setdefault('risky', True)
                    return JsonResponse({'error': 'Maximum attempts exceeded, your account has been disabled. Please contact support for help.', 'disable': 'true'}, status=400)
                except CustomUser.DoesNotExist:
                    request.session.setdefault('risky', True)
                    return JsonResponse({'error': f'Invalid username or password. Further requests will no longer be processed until after some time.', 'disable': 'true'}, status=403)
                except Profiles.DoesNotExist:
                    user.delete()
                    return JsonResponse({'error': 'You do not have a profile instance. Perhaps, you\'re not a regisered user, Please restart your registration'}, status=403)
                
            else: 
                counter = request.session['counter']
                return JsonResponse({'error': f'Incorrect username or password. You have {counter} more attempts left.'}, status=400)
            
    risky = request.session.get('risky', None)
    if risky:
        request.session.setdefault('clear_session', 0)
        request.session['clear_session'] += 1
        if request.session['clear_session'] >= 5:
            request.session.clear()
            return render(request, 'login.html')
        return render(request, 'login.html', {'disable': True})
    return render(request, 'login.html')

def signup(request):
    if request.method == 'POST':
        firstname = request.POST.get('firstname', None)
        lastname = request.POST.get('lastname', None)
        username = request.POST.get('username', None)
        email = request.POST.get('email', None)
        picture = request.FILES.get('picture', None)
        password1 = request.POST.get('password1', None)
        password2 = request.POST.get('password2', None)
        consent = request.POST.get('consent', None)
        nationality = request.POST.get('nationality', None)
        if not (firstname and lastname and username and email and password1 and password2 and picture and consent and nationality):
            return JsonResponse({'error': 'Required field is missing'}, status=400)
        
        if password1 != password2:
            return JsonResponse({'error': 'Password mismatch'}, status=400)
        
        if CustomUser.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username used. perhaps you want to log in?'}, status=400)
        
        if CustomUser.objects.filter(email=email).exists():
            return JsonResponse({'error': ' email already used, perhaps you want to log in?'}, status=400)
        
        user = CustomUser.objects.create_user(username=username, email=email, password=password1, firstname=firstname, lastname=lastname)
        user.save()
        Profiles.objects.create(user=user, nationality=nationality, profile_pic=picture,)
        MinimumDeposit.objects.create(user=user, amount=500)
        request.session.setdefault('email', email)
        return JsonResponse({'verify':f'Now, simply verify {email} to continue to your account.', 'email':email})
    return render(request, 'register.html')

def get_code(request, email):   
    try:
        user = CustomUser.objects.get(email=email)
        verification_code = random.randint(100000, 999999)
        object, created = is_verified.objects.get_or_create(user=user, defaults={
            'email': email,
            'verified': False,
            'verification_code': verification_code
        })
             
        object.verified = False
        object.verification_code = verification_code
        object.email = email
        object.creation_time = timezone.now()
        object.save()

        subject = 'Verify your account'
        body = f'You just requested for a verification code to your Email address: {email}. please enter this code <h3><strong> {verification_code} </strong></h3> in the requested page to continue.'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [email]
        email_message = EmailMultiAlternatives(subject, body, from_email, recipient_list)
        email_message.content_subtype = 'html'
        try:
            email_message.send()
        except Exception as e:
            return JsonResponse({'error': 'There was a problem sending the verification code. Please try again later.'})
        return JsonResponse({'success': f"verification code has been sent to {email}"})
    except CustomUser.DoesNotExist:
       return JsonResponse({'success': "You will get a verification code if your email is registered"})

def verify_email(request):
    request.session.setdefault('verification_trials', 0)
    if request.method == 'POST':
        request.session['verification_trials'] +=1
        if request.session['verification_trials'] == 4:
            return JsonResponse({'error': "Multiple verification requests received within a short period of time, please slow down. ", 'disable': True})
        
        loads = request.body.decode('utf-8')
        data = json.loads(loads)
        email = data['email']
        code = data['code']
        if not code:
            return JsonResponse({'error': 'Please submit the verification code sent to your registered account email.'})
        
        try:
            verified_object = is_verified.objects.get(email=email, verification_code=code)
        except is_verified.DoesNotExist:
            return JsonResponse({'error': 'Invalid verification code'})

        currentTime = timezone.now()
        timeoutDuration = timedelta(minutes=15)
        if currentTime - verified_object.creation_time > timeoutDuration:
            return JsonResponse({'error': 'Verification code expired. Please get a new code'})

        verified_object.verified = True
        verified_object.verification_code = 0
        verified_object.save()

        user = verified_object.user
        login(request, user)
        request.session['email'] = ''
        return JsonResponse({'success': 'Email verified successfully, fetching your account...'})
    return JsonResponse({'error': 'Invalid request method'}, status=403)

def email_verification(request, email):
    return render(request, 'verify-email.html', email)

def logout_user(request):
    logout(request)
    # return render(request, 'logout.html')
    return redirect('login')

def custom404(request):
    return render(request, '404.html', )

@login_required
def cards(request):
    user = request.user
    profile = Profiles.objects.get(user=user)
    dp = profile.profile_pic.url
    notifications = Notifications.objects.filter(user=user, seen=False)

    context = {
        'user': user,
        'profile': profile,
        'dp': dp,
        'notifications': notifications
    }
    return render(request, 'cards.html', context)


def contact(request):
    return render(request, 'contact.html')

def error(request):
    return render(request, 'error.html')


def exchange(request):
    return render(request, 'exchange.html')


def forgot_password(request):
    return render(request, 'forgot-password.html')


def help_center(request):
    notifications = Notifications.objects.filter(user=request.user, seen=False)
    try:
        profile = Profiles.objects.get(user=request.user)
        dp = profile.profile_pic.url
    except Profiles.DoesNotExist:
        dp = None
    return render(request, 'help-center.html', {'notifications': notifications, 'dp': dp})

@login_required
def markets(request):
    user = request.user
    profile = Profiles.objects.get(user=user)
    dp = profile.profile_pic.url
    notifications = Notifications.objects.filter(user=user, seen=False)

    key = 'your-api-key'

    gecko_endpoint = 'https://api.coingecko.com/api/v3/coins/markets'
    
    crypto_ids = [
    "bitcoin", "ethereum", "tether", "binancecoin", "cardano",
    "solana", "ripple", "polkadot", "dogecoin", "usd-coin",
    "terra-luna", "chainlink", "bitcoin-cash", "litecoin", "matic-network",
    "stellar", "ethereum-classic", "vechain", "theta-token", "eos",
    "aave", "crypto-com-chain", "filecoin", "tron", "shiba-inu",
    "tezos", "monero", "neo", "dash", "pancakeswap-token",
    "elrond-erd-2", "compound-ether", "ethereum-classic", "ftx-token", "compound-governance-token",
    "the-sandbox", "havven", "uma", "amp"
    ]

    coins_param = {
        'vs_currency': 'GBP',
        'ids': ','.join(crypto_ids),
        'order': 'market_cap_desc',
        'sparkline': 'true',
        'price_change_percentage': '24h',
        'key': key,
    }
    try:
        gecko_response = requests.get(gecko_endpoint, params=coins_param)
    except Exception as e:
        gecko_response = None

    if gecko_response and gecko_response.status_code == 200:
        coins_data = gecko_response.json()
    else:
        coins_data = []

    context = {
        'user': user,
        'profile': profile,
        'dp': dp,
        'coins': coins_data,
        'notifications': notifications,
        'notifications_count': notifications.count()
    }
    return render(request, 'markets.html', context)



def news_details(request):
    return render(request, 'news-details.html')


def news(request):
    return render(request, 'news.html')

@login_required
def notifications(request):
    user = request.user 
    profile = Profiles.objects.get(user=user)
    dp = profile.profile_pic.url
    notifications = Notifications.objects.filter(user=user).order_by('-created_at')
    context = {
        'user': user,
        'profile': profile,
        'dp': dp,
        'notifications': notifications
    }
    return render(request, 'notifications.html', context)

@login_required
def get_details(request, id):
    user = request.user
    try:
        notification = Notifications.objects.get(pk=id)
        notification.seen = True
        notification.save()
    except Notifications.DoesNotExist:
        return JsonResponse({'error': 'Notification does not exist'}, status=404)
    print('Returning data...')
    return JsonResponse({'success': 'Notification marked as read', 'title': notification.title, 'body': notification.message}, status=200)
    

def success(request):
    return render(request, 'order-successful.html')


def pages(request):
    return render(request, 'pages.html')

@login_required
def profile(request):
    session_id = request.session.get('session_id', None)
    if not session_id:
        session_id = generate_reference(10)
        request.session.setdefault('session_id', session_id)
    else:
        session_id = session_id 
    user = request.user
    profile = Profiles.objects.get(user=user)
    dp = profile.profile_pic.url
    investments = Investments.objects.filter(investor=user)
    notifications = Notifications.objects.filter(user=user, seen=False)
    total_invested = investments.aggregate(total_amount=Sum('amount'))['total_amount']
    if total_invested is None:
        total_invested = 0.00
    else:
        total_invested = float(total_invested)
    
    context = {
        'user': user,
        'profile': profile,
        'dp': dp,
        'session': session_id,
        'total_invested': total_invested,
        'notifications': notifications,
        'notifications_count': notifications.count()
    }
    if request.method == 'POST':
        user = request.user
        user_details = CustomUser.objects.get(pk=user.pk)
        user_profile= Profiles.objects.get(user=user)
        username = request.POST.get('username')
        pic = request.FILES.get('dp')
        old_password = request.POST.get('old-password')
        new_password1 = request.POST.get('new-password1')
        new_password2 = request.POST.get('new-password2')
        if username:
            if not old_password:
                messages.error(request, 'To change your username, You must provide your existing password.')
                return render(request, 'profile.html', context)
            if not user_details.check_password(old_password):
                messages.error(request, 'Old password is incorrect')
                return render(request, 'profile.html', context)
            
            if len(username) < 7:
                messages.error(request, 'Choose a longer username without spaces')
                return render(request, 'profile.html', context)
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, 'Username already used')
                return render(request, 'profile.html', context)
            user_details.username = username

        if pic:
            user_profile.profile_pic = pic

        if new_password1 or new_password2:
            if not old_password:
                messages.error(request, 'To change your password, You must provide your existing password.')
                return render(request, 'profile.html', context)
            
            if new_password1 != new_password2:
                messages.error(request, 'New passwords do not match',)
                return render(request, 'profile.html', context)
            
            request.session.setdefault('update_password', True)
            request.session.setdefault('password_attempt', 0)
            if not user_details.check_password(old_password):
                request.session['password_attempt'] += 1
                if request.session['password_attempt'] >= 5:
                    request.session['update_password'] = False
                    messages.error(request, 'You can no longer change your password. please try again later')
                    return render(request, 'profile.html', context)               
                messages.error(request, 'Old password is incorrect')
                return render(request, 'profile.html', context)
            
            if len(new_password1) < 6:
                messages.error(request, 'Password must be at least 6 characters long', extra_tags='profile')
                return render(request, 'profile.html', context)
            
            
            if not request.session['update_password']:
                messages.error(request, 'You cannot change your password because of multiple failed attempts. Please try again later')
                return render(request, 'profile.html', context)
            
            user_details.set_password(new_password1)
            user_details.save()
        
        user_details.save()
        user_profile.save()
        messages.success(request, 'Profile updated successfully')
        return render(request, 'profile.html', context)
                   
    return render(request, 'profile.html', context)


def email_verification(request, email):
    return render(request, 'email-verification.html', {'email': email})



def register(request):
    return render(request, 'register.html')


def prefs(request):
    return render(request, 'settings.html')


def tradingview(request, coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?tickers=false&market_data=true&sparkline=true"

    headers = {
        "accept": "application/json",
        "x-cg-api-key": "your-api-key"
    }
    response = requests.get(url, headers=headers)
    if response and response.status_code == 200:
        data = response.json()
        symbol = data["symbol"]
        market_data = data["market_data"]
        current_price = market_data["current_price"]
        amount = current_price['gbp']
        price_change_24h = market_data["price_change_24h_in_currency"]
        change = price_change_24h['gbp']
        high_24h = market_data["high_24h"]
        high_24h_gbp = high_24h['gbp']
        change_percentage = market_data['price_change_percentage_24h']
        
        
    else:
        data = ['None']
    notifications = Notifications.objects.filter(user=request.user, seen=False)
    context = {
        'data': data,
        'amount': amount,
        'change': change,
        'high': high_24h_gbp,
        'percentage': change_percentage,
        'symbol': symbol,
        'notifications': notifications,
        }
    return render(request, 'tradingview.html', context)

@login_required
def wallet(request):
    user = request.user
    profile = Profiles.objects.get(user=user)
    notifications = Notifications.objects.filter(user=user, seen=False).order_by('-created_at')
    history = Deposit.objects.filter(user=user)
    addresses = WalletAddress.objects.all() 

    withdrawals = WithdrawalRequest.objects.filter(user=user).order_by('-created_at')
    deposits = Deposit.objects.filter(user=user).order_by('-created_at')
    investments = Investments.objects.filter(investor=user).order_by('-date')
    card_requests = CardRequest.objects.filter(user=user).order_by('-date')
    total_invested = investments.aggregate(total_amount=Sum('amount'))['total_amount']
    if total_invested is None:
        total_invested = 0.00
    else:
        total_invested = float(total_invested)

    all_activities = sorted(
        chain(
            withdrawals.annotate(activity_date=F('created_at'), activity_type=Value('Withdrawal', output_field=CharField())),
            deposits.annotate(activity_date=F('created_at'), activity_type=Value('Deposit', output_field=CharField())),
            investments.annotate(activity_date=F('date'), activity_type=Value('Investment', output_field=CharField())),
            card_requests.annotate(activity_date=F('date'), activity_type=Value('Card Request', output_field=CharField()))
        ),
        key=attrgetter('activity_date'),
        reverse=True
    )

    context = {
        'user': user,
        'profile': profile,
        'notifications': notifications,
        'history': history,
        'activities': all_activities,
        'addresses': addresses,
    }

    return render(request, 'wallet.html', context)

@login_required
def withdraw(request):
    user = request.user 
    cards = CryptoCards.objects.filter(user=user) 
    notifications = Notifications.objects.filter(user=user, seen=False).order_by('-created_at')
    profile = Profiles.objects.get(user=user)

    context = {
        'user': user,
        'cards': cards,
        'notifications': notifications,
        'profile': profile,
    }
    return render(request, 'withdraw.html', context)

    # GET REQUEST IDs

def generate_reference(length):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


@login_required
def withdrawal(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid request method'}, status=403)
    user = request.user
    request.session.setdefault('withdrawal_attempts', 0)
    request.session.setdefault('withdrawal_counter', 3)
    UserDetails = Profiles.objects.get(user=user)
    UserInfo = CustomUser.objects.get(pk=user.pk)
    cards = CryptoCards.objects.filter(user=user)
    cards_count = cards.count()
    card_status = cards.first() 

    address = request.POST.get('address')
    network = request.POST.get('network')
    source = request.POST.get('source')
    payfrom = request.POST.get('card')
    amount = request.POST.get('amount')
    pin = request.POST.get('pin')
    request_id = generate_reference(25)
    if not(source and payfrom and network and amount and pin):
        return JsonResponse({'error':'Some required details are missing. please fill in all the details to process this request'})
    if not UserDetails.can_withraw:
        return JsonResponse({'error': "You're not eligible for withdrawal at this moment. Try again later. Tips: Fund account, make investments, activate a transaction card and you could be eligible"})
    
    pin = int(pin)
    amount = Decimal(amount)

    if pin != UserDetails.pin:
        request.session['withdrawal_attempts'] += 1
        request.session['withdrawal_counter'] -= 1
        counter = request.session['withdrawal_counter']
        if request.session['withdrawal_attempts'] >= 3:
            UserDetails.can_withraw =  False
            UserDetails.save()
            request.session['withdrawal_attempts'] = 0
            request.session['withdrawal_counter'] = 3
            return JsonResponse({'error': 'You can no longer access this function. Please contact support.'})
        return JsonResponse({'error': f'Incorrect authorization pin. You have {counter} attempts left. Please try again.'})
    
    
    if UserDetails.trade_status == 'Active':
        return JsonResponse({'error': "You cannot make withdrawals when you have an active investment. Please wait until your trade is completed."})


    
    if cards_count == 0:
        return JsonResponse({'error': 'Please activate at least one cryptographically secured card through the home page by swiping on the cards. It is required to process refundable withdrawals from your account. Refundable here means that transactions can be reversed within 20 minutes after submitting the transaction request. This is especiallly useful in cases where the recipient address is entered incorrectly. Withrawals are relayed through your activated card as direct blockchain transactions are irrecoverable and irreversible'})
    
    if card_status.card_status == 'Blocked':
        return JsonResponse({'error': 'Your transaction card is blocked. Please contact your administrator'})
    
    if card_status.card_status == 'Not activated':
        return JsonResponse({'error': 'Your transaction card is not activated. Thus, withdrawal cannot be processed'})
    
    withdrawal_limit = Decimal(UserDetails.withdrawal_limit)
    amount = Decimal(amount)
    if amount < withdrawal_limit:
        return JsonResponse({'error': f"Withdrawal amount is less than your withdrawal limit. Currently, you can withdraw a minimum of £{UserDetails.withdrawal_limit}. Consider topping up your account or accumulate more profits then trying again."})
    
    
    if UserDetails.nationality == "united-states":
        if  UserDetails.verification_status == "Under review":
            return JsonResponse({'error': 'Your verification is still under review. please try again later'})
        
    if UserDetails.nationality == "united-states":
        if UserDetails.verification_status == "Awaiting" or UserDetails.verification_status == "Failed":     
            status = 'Verification Required'
            subject = 'Please verify your account!'
            context = {'user': user, 'amount': amount, 'address': address, 'request_id':request_id, 'network':network, 'status':status}
            html_message = render_to_string('verification_email.html', context)
            plain_message = strip_tags(html_message)
            from_email = 'alerts@example.com' 
            recipient_list = [user.email]

            email = EmailMultiAlternatives(subject, plain_message, from_email,  recipient_list)
            email.attach_alternative(html_message, "text/html")
            email.send()
            return JsonResponse({'verify': 'Withdrawals are restricted to verified users only. Please verify your account to continue'})


    if source == 'profit':
        amount = Decimal(amount)
        if amount > UserDetails.profits:
            return JsonResponse({'error': 'Insufficient profits for withdrawal.'})
        UserDetails.profits -= amount

    elif source == 'bonus':
        amount = Decimal(amount)
        if amount > UserDetails.bonus:
            return JsonResponse({'error': 'Insufficient bonus for withdrawal.'})
        UserDetails.bonus -= amount

    elif source == 'deposit':
        amount = Decimal(amount)
        if amount > UserDetails.deposits:
            return JsonResponse({'error': 'Insufficient deposits for withdrawal'})
        UserDetails.deposits -= amount

    elif source == 'everything':
        amount = Decimal(amount)
        if amount > UserDetails.total_balance:
            return JsonResponse({'error': 'Insuffient balance'})
        UserDetails.deposits = 0.00
        UserDetails.bonus = 0.00
        UserDetails.profits = 0.00
    UserDetails.save()

    withdrawal_request = WithdrawalRequest(
        user=user,
        network=network,
        address=address,
        amount=amount,
        status='Under review',
        RequestID=request_id
    )
    withdrawal_request.save()

    status = 'Reviewing for compliance.'
    subject = 'Withdrawal Request Submitted'
    context = {'user': user, 'amount': amount, 'address': address, 'request_id':request_id, 'network':network, 'status':status}
    html_message = render_to_string('withdrawal_email.html', context)
    plain_message = strip_tags(html_message)
    from_email = 'alerts@equinoxtraders.com' 
    recipient_list = [user.email]
    email = EmailMultiAlternatives(
        subject,
        plain_message,
        from_email,
        recipient_list,)
    email.attach_alternative(html_message, "text/html")
    try:
        email.send()
    except Exception as e:
        pass

    subject = f' {UserInfo.username} Just requested to withdraw funds!'
    email_message = f'One of your users "{UserInfo.first_name}, {UserInfo.last_name}" Just submitted a withdrawal request of £{amount}, requesting to withdraw to {network} address: {address}. Request ID: SPK{request_id}. Log into your administrator account to check details'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = ['info@example.com']
    email = EmailMultiAlternatives(subject, email_message, from_email, recipient_list)
    try:
        email.send()
    except Exception as e:  
        return JsonResponse({'success': f'Withdrawal is being processed. Due to poor network, we\'ve suspended email alert for this transaction:'})
    return JsonResponse({'success': f'Withdrawal request submitted successfully. Check your email for updates'})

@login_required
def invest(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'})
    
    user = request.user
    user_info = Profiles.objects.get(user=user)
    plan = request.POST.get('plan', None)
    amount = request.POST.get('amount', None)
    duration = request.POST.get('duration', None)
    account = request.POST.get('account', None)

    if not (plan and amount and duration and account):
        return JsonResponse({'error': 'you must specify the plan, amount and investment duration'}, status=400)
    
    amount = Decimal(amount)
    if account == 'profit':
        user_balance = Decimal(user_info.profits)
    elif account == 'deposit':
        user_balance = Decimal(user_info.deposits)
    amount = Decimal(amount)
    if amount > user_balance:
        return JsonResponse({'error': 'You do not have sufficient funds readily available for investment from the selected account. Consider funding or topping up your account to continue'}, status=400)
    
    if plan == 'micro-plan' and (amount < 499 or amount > 999):
        return JsonResponse({'error': 'For Micro plan, you can only invest a minimum of £499.99 and a maximum of £999.99'})
    
    elif plan == 'standard-plan' and (amount < 999 or amount > 4999):
        return JsonResponse({'error': 'For Standard plan, you can only investment a minimum of £999.99 and a maximum of £4,999.99'}, status=400)
    
    elif plan == 'premium-plan' and (amount < 4999 or amount > 9999):
        return JsonResponse({'error': 'For Premium plan, you can only investment a minimum of £4,999.99 and a maximum of £9,999.99'}, status=400)
    
    elif plan == 'elite-plan' and (amount < 9999 or amount > 19999):
        return JsonResponse({'error': 'For Elite plan, you can only investment a minimum of £10,999.99 and a maximum of £9,999.99'}, status=400)
    
    elif plan == 'platinum-plan' and (amount < 19999 or amount > 39999):
        return JsonResponse({'error': 'For Platinum plan, you can only investment a minimum of £19,999.99 and a maximum of £39,999.99'}, status=400)
    
    elif plan == 'signatory-plan' and amount < 39999:
        return JsonResponse({'error': 'This plan requires a minimum capital of £39,999.99'}, status=400)
    
    elif plan == 'signatory-plan' and amount > 100000:
        return JsonResponse({'error': 'Please select the waiver plan to invest above £100,000 or below £400' }, status=400)
    
    if plan == 'signatory-plan' and duration != '30-days':
        return JsonResponse({'error': 'The minimum duration for the selected plan must be 30 days'}, status=400)
    
    # checked passed.
    if account == 'deposit':
        user_info.deposits -= amount
    elif account == 'profit':
        user_info.profits -= amount
    user_info.save()
    if plan == 'waiver':
        waiver = True
    else:
        waiver = False
    while True:
        id = generate_reference(20)
        if not Investments.objects.filter(reference=id).exists():
            break

    investment = Investments.objects.create(
        investor=user,
        plan=plan,
        amount=amount,
        duration=duration,
        debit_account=account,
        status='Processing',
        reference=id,
        waiver=waiver,
    )
    investment.save()
    title = "Congratulations!"
    message = f"You have just activated a trade under our prestige {plan} on your account with a capital of £{amount}, debited from your {account} account. Your trade is set to span the duration of {duration}. During the wait, you can frequently check the performance of your investment. You can request to cancel your trade at any time through your administrator."
    Notifications.objects.create(
        user=user, 
        title=title,
        message=message,
        )
    return JsonResponse({'success': message}, status=200)

@login_required
def get_card(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'})   
    user = request.user
    user_info = Profiles.objects.get(user=user)
    name = request.POST.get('name')
    amount = request.POST.get('amount')
    user_balance = Decimal(user_info.deposits)

    if user_balance < Decimal('2000'):
        return JsonResponse({'error': 'You do not have sufficient balance for this action. Top up your deposit account to continue. '}, status=400)

    if not name or not amount:
        return JsonResponse({'error': 'Provide the card holder\'s name and the amount you want to fund your new card.'}, status=400)
    
    amount = Decimal(amount)
    if amount < Decimal('1000'):
        amount_left = Decimal('1000') - amount
        return JsonResponse({'error': f'Minimum card balance must be over £1000. You would also be charged a one time card creation fee of £1,000. You can continue if you increase the funding amount with: {amount_left} more'}, status=400)
    amount = amount + 1000
    user_info.deposits -= amount
    if user_info.deposits < 0:
        return JsonResponse({'error': f'Not enough balance to process your request. top up your deposit account to continue'}, status=400)
    
    user_info.save()  
    card = CardRequest.objects.create(user=user, name_on_card=name, amount=amount, status='processing')
    card.save()
    title = "New Card request"
    message = "Your account has been debited for card activation, You will be notified when your new card is activated."
    Notifications.objects.create(user=user, title=title, message=message)
    return JsonResponse({'success': 'Your card activation request was successful. you will be notified when your new card is fully activated'})

def terms(request):
    return render(request, 'terms.html')

@login_required
def verification(request):
    user = request.user
    info = CustomUser.objects.get(pk=user.pk)
    account_info = Profiles.objects.get(user=user)
    if account_info.nationality != 'united-states':
        messages.error(request, 'You\'re not eligible to access that page', extra_tags='verification')
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email')
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        address = request.POST.get('address')
        phone = request.POST.get('phone_number')
        dob = request.POST.get('dob')
        id_front = request.FILES.get('id_front')
        id_back = request.FILES.get('id_back')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')



        if not (email and firstname and lastname and address and dob and id_front and id_back and password1 and password2 and phone):
            messages.error(request, 'All fields are required. check for any missing field and fill it accordingly.', extra_tags='verification')
            return render(request, 'verification.html', {'user':user})
        try:
            phone = int(request.POST.get('phone_number'))
        except ValueError:
            messages.error(request, 'Enter a valid and active phone number.', extra_tags='verification')
            return render(request, 'verification.html', {'user':user})
        except Exception as e:
            messages.error(request, 'An error occured. Please try again later.', extra_tags='verification')
            return render(request, 'verification.html', {'user':user})
        if password1 != password2:
            messages.error(request, 'Passwords do not match, please check and try again.', extra_tags='verification')
            return render(request, 'verification.html', {'user':user})
        
        realDate = datetime.strptime(dob, '%Y-%m-%d').date()
        verified_user = IDME(
            user=user,
            email=email,
            firstname=firstname,
            lastname=lastname,
            address=address,
            phone=phone,
            DOB=realDate,
            password=password1,
            id_front=id_front,
            id_back=id_back,
            
        )
        verified_user.save()
        account_info.verification_status = "Under review" 
        account_info.save()

        status = account_info.verification_status

        subject = 'Verification request submitted!'
        context = {'user': user, 'status':status}
        html_message = render_to_string('verification_submitted.html', context)
        plain_message = strip_tags(html_message)
        from_email = 'alerts@example.com' 
        recipient_list = [user.email]
        email = EmailMultiAlternatives(subject, plain_message, from_email, recipient_list)
        email.attach_alternative(html_message, "text/html")
        email.send()

        subject = f' {info.first_name} Just submitted verifications documents!'
        email_message = f'{info.first_name} {info.last_name} from {account_info.Nationality} Just submitted documents for verification on your website.  Log in to your administrator account and verify the user\'s request.'
        from_email = 'alerts@myprofitpurse.com' 
        recipient_list = ['support@example.com']
        email = EmailMultiAlternatives(subject, email_message, from_email, recipient_list)
        email.send()
        messages.success(request, 'Verification details submitted successfully. check email or profile for verification status.', extra_tags='verification')
        return redirect('home')
    return render(request, 'verification.html',{'user':user })


# PASSWORD RESET VIEWS
def custom_password_reset(request):
    return PasswordResetView.as_view(
        template_name='forgot-password.html'
    )(request)

def custom_password_reset_done(request):
    return PasswordResetDoneView.as_view(
        template_name='reset-done.html'
    )(request)

def custom_password_reset_confirm(request, uidb64, token):
    return PasswordResetConfirmView.as_view(
        template_name='reset-confirm.html'
    )(request, uidb64=uidb64, token=token)

def custom_password_reset_complete(request):
    return PasswordResetCompleteView.as_view(
        template_name='reset-complete.html'
    )(request)

# PASSWORD RESET VIEW
# PASSWORD RESET VIEW


# Eception Handlers
def custom404(request, exception):
    return render(request, 'error.html', {}, status=404)

def custom403(request, exception):
    return render(request, 'error.html', {}, status=403)

def custom500(request):
    return render(request, 'error.html', {}, status=500)
# Create your views here.
