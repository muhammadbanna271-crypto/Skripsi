from django.db import models


class BaseManager(models.Manager):

    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)