from django import template
from django.utils.html import conditional_escape, format_html, format_html_join
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def bullets(value):
    """Render teks multi-baris: baris biasa jadi paragraf, baris berawalan
    "- " jadi bullet point. Teks satu baris dirender apa adanya."""
    lines = str(value).split("\n")
    if len(lines) == 1:
        return conditional_escape(value)

    parts = []
    items = []

    def flush():
        if items:
            parts.append(
                format_html(
                    '<ul class="mb-1 mt-1">{}</ul>',
                    format_html_join("", "<li>{}</li>", ((i,) for i in items)),
                )
            )
            items.clear()

    for line in lines:
        if line.startswith("- "):
            items.append(line[2:])
        else:
            flush()
            if line.strip():
                parts.append(format_html("<div>{}</div>", line))
    flush()
    return mark_safe("".join(parts))
