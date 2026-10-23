from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from threading import Thread

from apps.master.models import Variable as MasterVariable
from apps.slr.models import Article, Factor, Keyword, SLRRun, Variable


@staff_member_required
def dashboard(request):
    latest_run = SLRRun.objects.first()
    keyword_results = []
    keywords = Keyword.objects.filter(article__sources__run=latest_run).distinct() if latest_run else Keyword.objects.none()
    for row in keywords.values("normalized_name").annotate(study_count=Count("article", distinct=True)).order_by("-study_count", "normalized_name")[:20]:
        journals = keywords.filter(normalized_name=row["normalized_name"]).exclude(article__journal="").values_list("article__journal", flat=True).distinct()[:5]
        keyword_results.append({**row, "journals": list(journals)})
    return render(request, "slr/dashboard.html", {
        "runs": SLRRun.objects.select_related("master_variable")[:20],
        "master_variables": MasterVariable.objects.filter(is_active=True).order_by("order", "code", "name"),
        "articles": Article.objects.filter(sources__run=latest_run).distinct()[:10] if latest_run else Article.objects.none(),
        "top_factors": Factor.objects.values("normalized_name").order_by("normalized_name")[:10],
        "keyword_results": keyword_results,
        "variable_count": Variable.objects.count(),
        "article_count": Article.objects.filter(sources__run=latest_run).distinct().count() if latest_run else 0,
        "llm_configured": (settings.SLR_LLM_PROVIDER == "gemini" and bool(settings.GEMINI_API_KEY)) or (settings.SLR_LLM_PROVIDER == "deepseek" and bool(settings.DEEPSEEK_API_KEY)) or (settings.SLR_LLM_PROVIDER == "anthropic" and bool(settings.ANTHROPIC_API_KEY)),
    })


@require_POST
@staff_member_required
def create_run(request):
    if SLRRun.objects.filter(status__in=[SLRRun.STATUS_PENDING, SLRRun.STATUS_RUNNING]).exists():
        messages.warning(request, "An SLR run is already queued or processing. Wait for it to finish before starting another one.")
        return redirect("slr:dashboard")

    try:
        master_variable = MasterVariable.objects.get(
            pk=request.POST.get("master_variable"),
            is_active=True,
        )
    except (MasterVariable.DoesNotExist, TypeError, ValueError):
        messages.error(request, "Select an active Target Master Variable before starting an SLR run.")
        return redirect("slr:dashboard")

    topic = str(master_variable)
    run = SLRRun.objects.create(
        master_variable=master_variable,
        # Keep these established fields populated while the dashboard is now
        # driven solely by its target Master Variable.
        topic=topic,
        search_query=topic,
        keywords=[], providers=["crossref", "semantic_scholar"],
        filters={"year_from": request.POST.get("year_from", "").strip(), "year_to": request.POST.get("year_to", "").strip()},
    )
    # Start only after the run record is committed, so the worker can always
    # load it using its own database connection.
    def launch():
        from apps.slr.services.workflow import run_slr_workflow
        Thread(target=run_slr_workflow, args=(run.pk,), name=f"slr-{run.pk}", daemon=True).start()
    transaction.on_commit(launch)
    return redirect("slr:dashboard")
