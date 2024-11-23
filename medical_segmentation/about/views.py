from django.views.generic.base import TemplateView


class AboutAuthorView(TemplateView):
    """About views."""

    template_name = 'about/author.html'


class AboutTechView(TemplateView):
    """Tech views."""

    template_name = 'about/tech.html'