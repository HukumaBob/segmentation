import csv
import os
from django.core.management.base import BaseCommand, CommandError
from data_preparation.models import Tag, TagsCategory

class Command(BaseCommand):
    help = 'Import tags and their categories from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv', 
            type=str, 
            default='data/tags.csv',  # Путь по умолчанию
            help='Path to the CSV file to import (default: data/tags.csv)'
        )

    def handle(self, *args, **kwargs):
        csv_path = kwargs['csv']

        # Преобразуем путь в абсолютный
        csv_file = os.path.abspath(csv_path)

        if not os.path.exists(csv_file):
            raise CommandError(f"File '{csv_file}' does not exist.")

        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    category_name = row['Tags_category'].strip()
                    code = row['Code_of_tag'].strip()
                    name = row['Name'].strip()
                    description = row['Description'].strip()

                    # Создаем или находим категорию
                    category, _ = TagsCategory.objects.get_or_create(tags_category=category_name)

                    # Обновляем или создаем тег с указанным кодом
                    tag, created = Tag.objects.update_or_create(
                        code=code,
                        category=category,  # Связываем с категорией
                        defaults={
                            'name': name,
                            'description': description,
                        }
                    )

                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Created tag: {name}"))
                    else:
                        self.stdout.write(self.style.SUCCESS(f"Updated tag: {name}"))

        except csv.Error as e:
            raise CommandError(f"Error reading CSV file: {e}")

        self.stdout.write(self.style.SUCCESS('Tags import completed successfully.'))
