import uuid

from django.db import models

from common.models import BaseModel


class SLRRun(BaseModel):
    """A reproducible, immutable definition and record of one SLR retrieval."""

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # This identifies the TRIP research variable the run investigates. It is
    # nullable to preserve SLR runs created before target-variable selection.
    master_variable = models.ForeignKey(
        "master.Variable",
        on_delete=models.PROTECT,
        related_name="slr_runs",
        null=True,
        blank=True,
    )
    topic = models.CharField(max_length=255)
    search_query = models.TextField()
    keywords = models.JSONField(default=list, blank=True)
    providers = models.JSONField(default=list)
    filters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    retrieved_count = models.PositiveIntegerField(default=0)
    accepted_count = models.PositiveIntegerField(default=0)
    duplicate_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True, default="")
    execution_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "slr_run"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.topic} ({self.created_at:%Y-%m-%d})"


class Article(BaseModel):
    ACCESS_METADATA_ONLY = "metadata_only"
    ACCESS_ABSTRACT = "abstract_available"
    ACCESS_FULL_TEXT = "full_text_available"
    ACCESS_UNAVAILABLE = "unavailable"
    ACCESS_CHOICES = [
        (ACCESS_METADATA_ONLY, "Metadata only"),
        (ACCESS_ABSTRACT, "Abstract available"),
        (ACCESS_FULL_TEXT, "Full text available"),
        (ACCESS_UNAVAILABLE, "Unavailable"),
    ]

    doi = models.CharField(max_length=255, null=True, blank=True, unique=True, db_index=True)
    source_database = models.CharField(max_length=50, blank=True, default="", db_index=True)
    title = models.TextField()
    normalized_title = models.TextField(db_index=True)
    authors = models.JSONField(default=list, blank=True)
    publication_year = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    journal = models.CharField(max_length=500, blank=True, default="")
    publisher = models.CharField(max_length=500, blank=True, default="")
    abstract = models.TextField(blank=True, default="")
    article_url = models.URLField(max_length=1000, blank=True, default="")
    full_text_url = models.URLField(max_length=1000, blank=True, default="")
    publication_type = models.CharField(max_length=100, blank=True, default="")
    language = models.CharField(max_length=32, blank=True, default="")
    access_status = models.CharField(max_length=30, choices=ACCESS_CHOICES, default=ACCESS_METADATA_ONLY)
    text_status = models.CharField(max_length=30, default="not_requested", db_index=True)
    full_text = models.TextField(blank=True, default="")
    text_error = models.TextField(blank=True, default="")
    metadata_payload = models.JSONField(default=dict, blank=True)
    last_retrieved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "slr_article"
        ordering = ["-publication_year", "title"]

    def __str__(self):
        return self.title[:100]


class ArticleSource(BaseModel):
    RETRIEVED = "retrieved"
    FILTERED = "filtered"
    FAILED = "retrieval_failed"
    STATUS_CHOICES = [(RETRIEVED, "Retrieved"), (FILTERED, "Filtered"), (FAILED, "Retrieval failed")]

    run = models.ForeignKey(SLRRun, on_delete=models.CASCADE, related_name="article_sources")
    article = models.ForeignKey(Article, on_delete=models.SET_NULL, null=True, blank=True, related_name="sources")
    provider = models.CharField(max_length=50, db_index=True)
    provider_article_id = models.CharField(max_length=255)
    source_query = models.TextField(blank=True, default="")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=RETRIEVED)
    raw_payload = models.JSONField(default=dict)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        db_table = "slr_article_source"
        constraints = [models.UniqueConstraint(fields=["run", "provider", "provider_article_id"], name="slr_unique_source_per_run")]


class ScreeningResult(BaseModel):
    PENDING = "pending"
    INCLUDED = "included"
    EXCLUDED = "excluded"
    UNCERTAIN = "uncertain"
    FAILED = "screening_failed"
    STATUS_CHOICES = [(PENDING, "Pending"), (INCLUDED, "Included"), (EXCLUDED, "Excluded"), (UNCERTAIN, "Uncertain"), (FAILED, "Screening failed")]

    article = models.OneToOneField(Article, on_delete=models.CASCADE, related_name="screening")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=PENDING)
    confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    reason = models.TextField(blank=True, default="")
    evidence = models.TextField(blank=True, default="")
    screened_at = models.DateTimeField(null=True, blank=True)


class Extraction(BaseModel):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "extraction_failed"
    UNCERTAIN = "uncertain"
    VALIDATION_FAILED = "validation_failed"
    STATUS_CHOICES = [(PENDING, "Pending"), (COMPLETED, "Completed"), (FAILED, "Extraction failed"), (UNCERTAIN, "Uncertain"), (VALIDATION_FAILED, "Validation failed")]

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="extractions")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=PENDING)
    summary = models.TextField(blank=True, default="")
    confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    validation_status = models.CharField(max_length=30, default="pending")
    provider = models.CharField(max_length=50, blank=True, default="")
    model_name = models.CharField(max_length=100, blank=True, default="")
    prompt_version = models.CharField(max_length=50, blank=True, default="")
    retry_count = models.PositiveIntegerField(default=0)
    processed_at = models.DateTimeField(null=True, blank=True)


class Evidence(BaseModel):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="evidence_items")
    extraction = models.ForeignKey(Extraction, on_delete=models.SET_NULL, null=True, blank=True, related_name="evidence_items")
    snippet = models.TextField()
    section = models.CharField(max_length=255, blank=True, default="")
    page_number = models.PositiveIntegerField(null=True, blank=True)
    source_location = models.CharField(max_length=500, blank=True, default="")
    evidence_type = models.CharField(max_length=50, blank=True, default="")


class Variable(BaseModel):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="slr_variables")
    extraction = models.ForeignKey(Extraction, on_delete=models.SET_NULL, null=True, blank=True, related_name="variables")
    original_name = models.CharField(max_length=500)
    normalized_name = models.CharField(max_length=500, db_index=True)
    variable_role = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(blank=True, default="")
    evidence = models.ForeignKey(Evidence, on_delete=models.PROTECT, related_name="variables")


class Dimension(BaseModel):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="slr_dimensions")
    variable = models.ForeignKey(Variable, on_delete=models.CASCADE, related_name="dimensions")
    original_name = models.CharField(max_length=500)
    normalized_name = models.CharField(max_length=500, db_index=True)
    evidence = models.ForeignKey(Evidence, on_delete=models.PROTECT, related_name="dimensions")


class Indicator(BaseModel):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="slr_indicators")
    variable = models.ForeignKey(Variable, on_delete=models.CASCADE, related_name="indicators")
    dimension = models.ForeignKey(Dimension, on_delete=models.SET_NULL, null=True, blank=True, related_name="indicators")
    original_name = models.CharField(max_length=500)
    normalized_name = models.CharField(max_length=500, db_index=True)
    evidence = models.ForeignKey(Evidence, on_delete=models.PROTECT, related_name="indicators")


class Factor(BaseModel):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="slr_factors")
    extraction = models.ForeignKey(Extraction, on_delete=models.SET_NULL, null=True, blank=True, related_name="factors")
    original_name = models.CharField(max_length=500)
    normalized_name = models.CharField(max_length=500, db_index=True)
    affected_outcome = models.CharField(max_length=500)
    relationship = models.TextField(blank=True, default="")
    evidence = models.ForeignKey(Evidence, on_delete=models.PROTECT, related_name="factors")


class Keyword(BaseModel):
    """A keyword explicitly supported by an article's supplied content."""

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="slr_keywords")
    extraction = models.ForeignKey(Extraction, on_delete=models.SET_NULL, null=True, blank=True, related_name="keywords")
    original_name = models.CharField(max_length=500)
    normalized_name = models.CharField(max_length=500, db_index=True)
    evidence = models.ForeignKey(Evidence, on_delete=models.PROTECT, related_name="keywords")


class Synthesis(BaseModel):
    normalized_concept = models.CharField(max_length=500, db_index=True)
    concept_type = models.CharField(max_length=50)
    supporting_study_count = models.PositiveIntegerField(default=0)
    supporting_articles = models.ManyToManyField(Article, related_name="syntheses", blank=True)
    synthesis_text = models.TextField(blank=True, default="")
    evidence_references = models.ManyToManyField(Evidence, related_name="syntheses", blank=True)
    generated_by = models.CharField(max_length=50, default="deterministic")
