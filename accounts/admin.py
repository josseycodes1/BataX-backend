from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserProfile


@admin.register(User)
class BataxUserAdmin(UserAdmin):
    ordering = ['email']
    list_display = ['email', 'role', 'is_active', 'is_verified', 'is_identity_verified']
    search_fields = ['email', 'first_name', 'last_name']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {'fields': ('first_name', 'last_name', 'phone_number', 'state', 'city')}),
        ('Access', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Verification', {'fields': ('is_verified', 'is_phone_verified', 'is_identity_verified')}),
    )
    add_fieldsets = ((None, {'classes': ('wide',), 'fields': ('email', 'password1', 'password2')}),)

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    has_change_permission = has_view_permission
    has_add_permission = has_view_permission
    has_delete_permission = has_view_permission


admin.site.register(UserProfile)
