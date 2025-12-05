from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """
    Hierarchical product categories.
    Examples: Pintura > Tinta > Tinta para Tecido
    """
    name = models.CharField(
        max_length=200,
        verbose_name='Nome'
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name='Slug'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Categoria Pai'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Descrição'
    )
    image = models.ImageField(
        upload_to='categories/',
        blank=True,
        null=True,
        verbose_name='Imagem'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem de exibição'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
    
    def __str__(self):
        return self.full_path
    
    @property
    def full_path(self):
        """Returns the full category path: Parent > Child > Grandchild"""
        ancestors = self.get_ancestors()
        path = [a.name for a in ancestors] + [self.name]
        return ' > '.join(path)
    
    def get_ancestors(self):
        """Returns list of all ancestor categories, from root to immediate parent."""
        ancestors = []
        current = self.parent
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors
    
    def get_descendants(self):
        """Returns all descendant categories (children, grandchildren, etc.)"""
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants
    
    @property
    def level(self):
        """Returns the depth level (0 for root categories)."""
        return len(self.get_ancestors())
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure unique slug
            base_slug = self.slug
            counter = 1
            while Category.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)
