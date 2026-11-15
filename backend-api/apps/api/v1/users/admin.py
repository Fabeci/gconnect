from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Student, Alumni, InstitutionAdmin, Enterprise

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('username', 'email', 'role', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name', 'phone_number', 'photo')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Rôle', {'fields': ('role',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'is_active'),
        }),
    )

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'date_of_birth', 'student_id')
    search_fields = ('user__username', 'student_id')
    filter_horizontal = ('interests', 'preferences', 'sectors', 'skills')

@admin.register(Alumni)
class AlumniAdmin(admin.ModelAdmin):
    list_display = ('user', 'institution', 'promotion', 'graduation_date')
    search_fields = ('user__username', 'institution__name')
    filter_horizontal = ('interests', 'preferences', 'sectors', 'skills')

@admin.register(InstitutionAdmin)
class InstitutionAdminAdmin(admin.ModelAdmin):  # Nom changé pour éviter conflit avec le modèle Institution
    list_display = ('user', 'institution')
    search_fields = ('user__username', 'institution__name')

@admin.register(Enterprise)
class EnterpriseAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'sector')
    search_fields = ('company_name', 'sector')
