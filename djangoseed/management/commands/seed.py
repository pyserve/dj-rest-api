from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.management.base import BaseCommand, CommandError
from django.db import models
from djangoseed.utils import DjangoFaker
from tqdm import tqdm


class Command(BaseCommand):
    help = "Seed data for the given module."

    def __init__(self):
        self.faker = DjangoFaker()
        super().__init__()

    def add_arguments(self, parser):
        parser.add_argument(
            "app_name",
            type=str,
            choices=[app_config.label for app_config in apps.get_app_configs()],
            help="Name of the app to seed data for (e.g., 'lead')",
        )
        parser.add_argument(
            "--module",
            type=str,
            required=True,
            choices=[model.__name__ for model in apps.get_models()],
            help="Name of the model/module to seed data for (e.g., 'lead')",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=10,
            help="Number of records to create (default: 10)",
        )

    def handle(self, *args, **options):
        app = options.get("app_name")
        module = options.get("module")
        count = options.get("count", 10)
        try:
            model = apps.get_model(app, module)
            model_fields = model._meta.get_fields()
            fields = [
                field
                for field in model_fields
                if isinstance(field, models.Field)
                and (
                    not field.auto_created
                    and not field.has_default()
                    and not isinstance(field, models.AutoField)
                )
            ]
            actual_records_created = 0
            for _ in tqdm(range(count), desc=f"Seeding {model.__name__}"):
                data = {}
                try:
                    for field in fields:
                        if not isinstance(
                            field, models.ManyToManyField
                        ) and not isinstance(field, GenericForeignKey):
                            data[f"{field.name}"] = self.faker.get_fake_data(field)
                    obj = model.objects.create(**data)
                    actual_records_created += 1
                    for field in fields:
                        if isinstance(field, models.ManyToManyField):
                            self.faker.get_fake_data(field, instance=obj)
                except Exception as error:
                    self.stderr.write(str(error))
                    continue
            self.stdout.write(
                f"Successfully!! created {actual_records_created} {model.__name__} records."
            )
        except Exception as error:
            raise CommandError(str(error))
