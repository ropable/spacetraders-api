from django.conf import settings


def template_context(request):
    """Extra context variables for every template."""
    context = {
        "LANGUAGE_CODE": settings.LANGUAGE_CODE,
    }
    context.update(settings.STATIC_CONTEXT_VARS)
    return context
