import random

from django.db import models
from django.utils import timezone
from faker import Faker


class DjangoFaker:
    def __init__(self):
        self.faker = Faker()

    def get_all_fields(self, model):
        fields = [
            field
            for field in model._meta.get_fields()
            if isinstance(field, models.Field)
            and (
                not field.auto_created
                and not field.has_default()
                and not isinstance(field, models.AutoField)
            )
        ]
        return fields

    def get_fake_data(self, field, instance=None):
        name = field.name
        if isinstance(field, models.CharField) or isinstance(field, models.TextField):
            value = ""
            if "email" in name:
                value = self.faker.email()
            elif "username" in name:
                value = self.faker.user_name()
            elif "first_name" in name:
                value = self.faker.first_name()
            elif "last_name" in name:
                value = self.faker.last_name()
            elif "password" in name:
                value = self.faker.password()
            elif "phone" in name:
                value = self.faker.phone_number()
            elif "address" in name:
                value = self.faker.address()
            elif "city" in name:
                value = self.faker.city()
            elif "country" in name:
                value = self.faker.country()
            elif "postal" in name:
                value = self.faker.postalcode()
            elif "street" in name:
                value = self.faker.street_address()
            else:
                value = " ".join(self.faker.words(nb=2))
            return value[0 : field.max_length]

        elif isinstance(field, models.EmailField):
            return self.faker.email()

        elif isinstance(field, models.PositiveIntegerField):
            return self.faker.random_int(min=1, max=100)

        elif isinstance(field, models.IntegerField) or isinstance(
            field, models.DecimalField
        ):
            decimal = self.faker.pydecimal(
                left_digits=(field.max_digits - field.decimal_places),
                right_digits=field.decimal_places,
                positive=True,
            )
            return decimal

        elif isinstance(field, models.DateField):
            return self.faker.date()

        elif isinstance(field, models.DateTimeField):
            return self.faker.date_time(tzinfo=timezone.get_current_timezone())

        elif isinstance(field, models.ForeignKey) or isinstance(
            field, models.OneToOneField
        ):
            related_model = field.related_model
            related_objects = list(related_model.objects.all())
            if related_objects:
                return random.choice(related_objects)
            else:
                if field.model is field.related_model:
                    return None
                fields = self.get_all_fields(related_model)
                data = {}
                for field in fields:
                    if not isinstance(field, models.ManyToManyField):
                        data[f"{field.name}"] = self.get_fake_data(field)

                obj = related_model.objects.create(**data)
                for field in fields:
                    if isinstance(field, models.ManyToManyField):
                        self.get_fake_data(field, instance=obj)
                return obj

        elif isinstance(field, models.ManyToManyField):
            if instance:
                related_model = field.related_model
                related_objects = list(related_model.objects.all())
                if related_objects:
                    chosen = random.sample(
                        related_objects, k=min(1, len(related_objects))
                    )
                    getattr(instance, field.name).set(chosen)
                else:
                    data = {}
                    fields = self.get_all_fields(related_model)
                    for field in fields:
                        if not isinstance(field, models.ManyToManyField):
                            data[f"{field.name}"] = self.get_fake_data(field)

                    new_objs = related_model.objects.create(**data)
                    getattr(instance, field.name).set(new_objs)

        return self.faker.word()
