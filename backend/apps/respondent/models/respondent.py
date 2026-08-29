from django.db import models

from common.models import BaseModel

from apps.survey.models import SurveyVillage


class Respondent(BaseModel):
    """
    Survey Respondent
    """

    GENDER_CHOICES = (
        ("M", "Male"),
        ("F", "Female"),
    )

    survey_village = models.ForeignKey(
        SurveyVillage,
        on_delete=models.CASCADE,
        related_name="respondents",
    )

    nik = models.CharField(
        max_length=20,
        unique=True,
    )

    name = models.CharField(
        max_length=100,
    )

    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
    )

    birth_date = models.DateField()

    phone = models.CharField(
        max_length=20,
        blank=True,
    )

    address = models.TextField()

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:

        db_table = "respondent"

        ordering = [
            "name",
        ]

    def __str__(self):

        return self.name