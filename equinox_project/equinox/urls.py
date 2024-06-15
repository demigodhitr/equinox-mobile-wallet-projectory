from django.urls import path
from . import views



urlpatterns = [
    path('', views.landing, name='landing'),
    path('home/', views.index, name='home'),
    path('register/', views.signup, name='register'),
    path('login/', views.signin, name='login'),
    path('get_code/<str:email>', views.get_code, name='get_code'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('logout/', views.logout_user, name='logout'),
    path('cards/', views.cards, name='cards'),
    path('contact/', views.contact, name='contact'),
    path('error/', views.error, name='error'),
    path('exchange/', views.exchange, name='exchange'),
    path('help_center/', views.help_center, name='help_center'),
    path('markets/', views.markets, name='markets'),
    path('news_details/', views.news_details, name='news_details'),
    path('news', views.news, name='news'),
    path('notifications/', views.notifications, name='notifications'),
    path('success/', views.success, name='success'),
    path('pages/', views.pages, name='pages'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.prefs, name='settings'),
    path('tradingview/<str:coin_id>/', views.tradingview, name='tradingview'),
    path('wallet/', views.wallet, name='wallet'),
    path('invest/', views.invest, name='invest'),
    path('withdraw/', views.withdraw, name='withdraw'),
    path('withdrawal/', views.withdrawal, name='withdrawal'),
    path('getcard/', views.get_card, name='getcard'),
    path('get_details/<str:id>/', views.get_details, name='get_details'),
    path('email_verification/<str:email>/', views.email_verification, name='email_verification'),
    path('terms-of-service/',  views.terms, name='terms'),
    path('verification/', views.verification, name='verification'),
    



    #Password Reset urls.
    path('reset_password/', views.custom_password_reset, name='password_reset'),
    path('reset_password_done/', views.custom_password_reset_done, name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.custom_password_reset_confirm, name='password_reset_confirm'),
    path('reset_password_complete/', views.custom_password_reset_complete, name='password_reset_complete'),



]