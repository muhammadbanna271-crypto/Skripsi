import uuid

from django.db import models


def new_execution_id():
    return str(uuid.uuid4())


class ExecutionLog(models.Model):
    """Satu baris per eksekusi import tervalidasi."""

    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED_SCHEMA = "failed_schema"
    STATUS_FAILED_PROCESS = "failed_process"

    STATUS_CHOICES = [
        (STATUS_RUNNING, "Berjalan"),
        (STATUS_SUCCESS, "Berhasil"),
        (STATUS_FAILED_SCHEMA, "Gagal schema"),
        (STATUS_FAILED_PROCESS, "Gagal proses"),
    ]

    execution_id = models.CharField(
        max_length=36,
        unique=True,
        default=new_execution_id,
    )

    survey = models.ForeignKey(
        "survey.Survey",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)

    source_filename = models.CharField(max_length=255, blank=True)
    source_sha256 = models.CharField(max_length=64, blank=True)
    rules_version = models.CharField(max_length=20)

    n_input = models.PositiveIntegerField(default=0)
    # Lolos P1.
    n_accepted = models.PositiveIntegerField(default=0)
    # Ditolak di P1 + P2.
    n_rejected = models.PositiveIntegerField(default=0)
    n_rejected_p1 = models.PositiveIntegerField(default=0)
    n_rejected_p2 = models.PositiveIntegerField(default=0)
    # Lolos P1 tetapi tidak ditemukan di database setelah simpan.
    n_lost = models.PositiveIntegerField(default=0)
    # Tersimpan dan terverifikasi sama dengan sumber (lolos P2).
    n_output = models.PositiveIntegerField(default=0)
    # N_input - (N_output + N_ditolak); null bila schema gagal.
    delta_n = models.IntegerField(null=True, blank=True)

    output_summary = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RUNNING,
    )
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "dq_execution_log"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.execution_id} [{self.status}]"


class RejectionLog(models.Model):
    """Satu baris per pelanggaran (satu rekaman bisa punya banyak)."""

    execution = models.ForeignKey(
        ExecutionLog,
        on_delete=models.CASCADE,
        related_name="rejections",
    )

    respondent_id = models.CharField(max_length=64, blank=True)
    source_row = models.PositiveIntegerField()
    column_name = models.CharField(max_length=64)
    original_value = models.TextField(blank=True)
    value_type = models.CharField(max_length=32, blank=True)
    dimension = models.CharField(max_length=20)
    rule = models.CharField(max_length=64)
    checkpoint = models.CharField(max_length=2)
    reason = models.TextField()
    # P2: nilai di database (discrepancy) dan tindakan terhadap rekaman.
    db_value = models.TextField(blank=True)
    record_action = models.CharField(max_length=40, blank=True)
    # P1 uniqueness: baris kemunculan pertama yang dipertahankan.
    related_row = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "dq_rejection_log"
        ordering = ["execution_id", "checkpoint", "source_row", "id"]
        indexes = [
            models.Index(fields=["execution", "checkpoint", "dimension"]),
        ]

    def __str__(self):
        return (
            f"{self.checkpoint} baris {self.source_row} "
            f"{self.column_name}: {self.rule}"
        )


class QualityScore(models.Model):
    """Q = n_satisfied / n_checked per execution, checkpoint, dimensi."""

    execution = models.ForeignKey(
        ExecutionLog,
        on_delete=models.CASCADE,
        related_name="quality_scores",
    )

    checkpoint = models.CharField(max_length=2)
    dimension = models.CharField(max_length=20)
    n_checked = models.PositiveIntegerField()
    n_satisfied = models.PositiveIntegerField()
    # Null bila n_checked == 0.
    score = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "dq_quality_score"
        unique_together = ("execution", "checkpoint", "dimension")
        ordering = ["execution_id", "checkpoint", "dimension"]

    def __str__(self):
        return f"{self.checkpoint} {self.dimension}: {self.score}"
