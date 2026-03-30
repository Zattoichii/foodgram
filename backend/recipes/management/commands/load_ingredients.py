import json
from pathlib import Path

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загружает ингредиенты из JSON'

    def handle(self, *args, **options):
        file_path = \
            Path(__file__).resolve().parents[4] / 'data' / 'ingredients.json'

        with open(file_path, encoding='utf-8') as file:
            data = json.load(file)

        ingredients_to_create = [
            Ingredient(
                name=item['name'],
                measurement_unit=item['measurement_unit']
            )
            for item in data
        ]

        Ingredient.objects.bulk_create(
            ingredients_to_create,
            ignore_conflicts=True
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Ингредиенты успешно загружены: {len(ingredients_to_create)}'
            )
        )
