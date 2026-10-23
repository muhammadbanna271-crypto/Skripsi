from django.contrib import admin

from apps.slr.models import Article, ArticleSource, Extraction, ScreeningResult, SLRRun


@admin.register(SLRRun)
class SLRRunAdmin(admin.ModelAdmin):
    list_display = ("topic", "status", "retrieved_count", "accepted_count", "created_at")
    list_filter = ("status",)
    search_fields = ("topic", "search_query")
    readonly_fields = ("id", "created_at", "updated_at", "started_at", "finished_at")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "publication_year", "doi", "source_database", "access_status")
    list_filter = ("source_database", "access_status", "publication_year")
    search_fields = ("title", "doi", "journal", "publisher")


admin.site.register(ArticleSource)
admin.site.register(ScreeningResult)
admin.site.register(Extraction)
