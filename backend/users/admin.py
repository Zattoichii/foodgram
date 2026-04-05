from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count

from .models import User, Subscription


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
        'subscribers_count',
        'recipes_count',
    )
    search_fields = (
        'email',
        'username',
    )
    list_filter = (
        'email',
        'username',
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            subscribers_total=Count('subscribers', distinct=True),
            recipes_total=Count('recipes', distinct=True),
        )

    @admin.display(description='Подписчиков')
    def subscribers_count(self, obj):
        return obj.subscribers_total

    @admin.display(description='Рецептов')
    def recipes_count(self, obj):
        return obj.recipes_total


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'author',
    )
    search_fields = (
        'user__username',
        'author__username',
        'user__email',
        'author__email',
    )
