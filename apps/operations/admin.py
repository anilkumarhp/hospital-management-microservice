# apps/operations/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import Organization, Branch, PhoneNumber, UserProfile

# Define an inline admin descriptor for UserProfile
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'

# Define a new User admin that includes the profile inline
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

# Re-register the built-in User model with our custom UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'created_at')
    search_fields = ('name',)

class PhoneNumberInline(admin.TabularInline):
    model = PhoneNumber
    extra = 1

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'city')
    list_select_related = ('organization',)
    search_fields = ('name', 'organization__name')
    inlines = [PhoneNumberInline,]

# Notice there is NO separate admin.site.register(UserProfile) here.
# It is handled by the UserAdmin inline above.