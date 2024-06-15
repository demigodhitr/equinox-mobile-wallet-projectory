from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin


class AccountInfoInline(admin.StackedInline):
    model = Profiles
    can_delete = True
    extra = 0

class CryptoCardsInline(admin.StackedInline):
    model = CryptoCards
    extra = 0
    

class NotificationsInline(admin.StackedInline):
    model = Notifications
    can_delete = True
    extra = 0

class WithdrawalRequestInline(admin.StackedInline):
    model = WithdrawalRequest
    can_delete = True
    extra = 0

class DepositsInline(admin.StackedInline):
    model = Deposit
    can_delete = True
    extra = 0
class IDMEInline(admin.StackedInline):
    model = IDME
    can_delete = True
    extra = 0

class EmailMessageInline(admin.StackedInline):
    model = send_email
    can_delete = True
    extra = 0

class LimitInline(admin.StackedInline):
    model = MinimumDeposit
    can_delete = True
    extra = 0



class CustomUserAdmin(UserAdmin):
    inlines = [
        AccountInfoInline, 
        CryptoCardsInline, 
        WithdrawalRequestInline, 
        NotificationsInline, 
        DepositsInline,
        IDMEInline,
        EmailMessageInline,
        LimitInline,
        ]


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(
    [WalletAddress, 
     ExchangeRates, 
     MinimumDeposit, 
     Investments, 
     CardRequest])

# Register your models here.
