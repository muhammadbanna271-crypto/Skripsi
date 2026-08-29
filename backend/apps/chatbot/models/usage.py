from django.db import models


class ChatbotUsage(models.Model):
    """
    Penghitung pemakaian chatbot per bulan, sebagai lapis
    pengaman KEDUA di sisi aplikasi (lapis pertama & yang paling
    kuat tetap monthly spend limit di console.anthropic.com).

    Perkiraan biaya di sini KASAR (bukan biaya API yang presisi),
    sengaja dibuat dengan margin aman supaya berhenti SEBELUM
    mendekati batas beneran.
    """

    month = models.CharField(
        max_length=7,
        unique=True,
        help_text="Format YYYY-MM",
    )

    message_count = models.PositiveIntegerField(default=0)

    estimated_cost_usd = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=0,
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):

        return f"{self.month} - {self.message_count} pesan"
