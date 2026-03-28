from django.db import models


class Page(models.Model):
    """
    Simple CMS-style page.
    Use for: About, Getting Started, Equipment, etc.
    """
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    body = models.TextField(blank=True)

    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title


class RuleSection(models.Model):
    """
    Rules content grouped into ordered sections.
    """
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    body = models.TextField(blank=True)

    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self) -> str:
        return f"{self.order}. {self.title}"
