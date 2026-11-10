from django import template

register = template.Library()


@register.filter
def cop(value):
    """Formatea un número como peso colombiano: $139.900"""
    try:
        entero = int(round(float(value)))
    except (TypeError, ValueError):
        return value
    # Separar miles manualmente con punto
    formatted = f"{entero:,}".replace(",", ".")
    return f"${formatted}"
