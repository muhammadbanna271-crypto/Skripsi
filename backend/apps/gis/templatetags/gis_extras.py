from django import template

register = template.Library()


@register.filter
def idr(value):
    """Format angka menjadi Rupiah gaya Indonesia (contoh: Rp15.000)."""
    if value is None:
        return "—"
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return str(value)
    return f"Rp{amount:,}".replace(",", ".")
