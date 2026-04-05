from django.db.models import Sum, Count
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from api.filters import RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (
    AvatarSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    ShortRecipeSerializer,
    SubscriptionSerializer,
    TagSerializer,
    SubscribeSerializer,
    FavoriteSerializer,
    ShoppingCartSerializer,
)
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from users.models import Subscription, User


class UserViewSet(DjoserUserViewSet):
    permission_classes = (permissions.AllowAny,)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscriptions(self, request):
        authors = User.objects.filter(
            subscribers__user=request.user
        ).annotate(
            recipes_count=Count('recipes', distinct=True)
        )
        page = self.paginate_queryset(authors)
        serializer = SubscriptionSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscribe(self, request, id=None):
        author = self.get_object()

        serializer = SubscribeSerializer(
            data={},
            context={
                'request': request,
                'author': author,
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        author = User.objects.annotate(
            recipes_count=Count('recipes', distinct=True)
        ).get(pk=author.pk)

        serializer = SubscriptionSerializer(
            author,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id=None):
        author = self.get_object()
        subscription = Subscription.objects.filter(
            user=request.user,
            author=author
        )

        if not subscription.exists():
            return Response(
                {'errors': 'Подписка не найдена.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('put',),
        permission_classes=(permissions.IsAuthenticated,),
        url_path='me/avatar'
    )
    def avatar(self, request):
        serializer = AvatarSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        request.user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None
    filter_backends = (SearchFilter,)
    search_fields = ('^name',)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().select_related(
        'author'
    ).prefetch_related(
        'tags',
        'recipe_ingredients__ingredient',
    )
    permission_classes = (IsAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update', 'update'):
            return RecipeWriteSerializer
        return RecipeReadSerializer

    @staticmethod
    def _add_user_recipe_relation(request, recipe, serializer_class):
        serializer = serializer_class(
            data={},
            context={
                'request': request,
                'recipe': recipe,
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            ShortRecipeSerializer(recipe, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @staticmethod
    def _delete_user_recipe_relation(request, recipe, model, error_message):
        deleted_count, _ = model.objects.filter(
            user=request.user,
            recipe=recipe
        ).delete()

        if not deleted_count:
            return Response(
                {'errors': error_message},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        return self._add_user_recipe_relation(
            request,
            recipe,
            FavoriteSerializer
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        recipe = self.get_object()
        return self._delete_user_recipe_relation(
            request,
            recipe,
            Favorite,
            'Рецепт не найден в избранном.'
        )

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        return self._add_user_recipe_relation(
            request,
            recipe,
            ShoppingCartSerializer
        )

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        return self._delete_user_recipe_relation(
            request,
            recipe,
            ShoppingCart,
            'Рецепт не найден в списке покупок.'
        )

    @action(
        detail=True,
        methods=('get',),
        permission_classes=(permissions.AllowAny,),
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = request.build_absolute_uri(f'/s/{recipe.short_code}/')
        return Response(
            {'short-link': short_link},
            status=status.HTTP_200_OK
        )

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,),
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__in_shopping_carts__user=request.user)
            .values(
                'ingredient__name',
                'ingredient__measurement_unit'
            )
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )

        lines = ['Список покупок:\n']

        for item in ingredients:
            name = item['ingredient__name']
            unit = item['ingredient__measurement_unit']
            amount = item['total_amount']
            lines.append(f'{name} ({unit}) — {amount}')

        shopping_list = '\n'.join(lines)

        response = HttpResponse(
            shopping_list,
            content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = \
            'attachment; filename="shopping_list.txt"'
        return response


def redirect_short_link(request, short_code):
    recipe = get_object_or_404(Recipe, short_code=short_code)
    return HttpResponseRedirect(f'/recipes/{recipe.id}')
