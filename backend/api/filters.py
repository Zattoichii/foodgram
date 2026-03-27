import django_filters

from recipes.models import Recipe, Tag


class RecipeFilter(django_filters.FilterSet):
    tags = django_filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    author = django_filters.NumberFilter(field_name='author__id')
    is_favorited = django_filters.NumberFilter(method='filter_is_favorited')
    is_in_shopping_cart = django_filters.NumberFilter(method='filter_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ('author', 'tags')

    def filter_is_favorited(self, queryset, name, value):
        request = self.request
        if request.user.is_anonymous:
            return queryset.none() if value == 1 else queryset
        if value == 1:
            return queryset.filter(favorited_by__user=request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        request = self.request
        if request.user.is_anonymous:
            return queryset.none() if value == 1 else queryset
        if value == 1:
            return queryset.filter(in_shopping_carts__user=request.user)
        return queryset