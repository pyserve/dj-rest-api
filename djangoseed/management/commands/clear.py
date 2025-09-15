from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from tqdm import tqdm


class Command(BaseCommand):
    help = "Delete all data for the given module."

    def add_arguments(self, parser):
        parser.add_argument(
            "--app",
            type=str,
            required=True,
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

    def handle(self, *args, **options):
        app = options.get("app")
        module = options.get("module")
        try:
            model = apps.get_model(app, module)
            records = model.objects.all()
            for record in tqdm(records):
                record.delete()
            self.stdout.write(
                f"Successfully! deleted {len(records)} {model.__name__} records"
            )
        except LookupError:
            self.stderr.write(f"Model '{module}' does not exist in '{app}'.")
        except Exception as error:
            raise CommandError(str(error))
