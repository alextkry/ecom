# Generated manually

from django.db import migrations, models
import django.db.models.deletion


def delete_global_options(apps, schema_editor):
    """Delete any AttributeOptions without a product (global options)."""
    AttributeOption = apps.get_model('catalog', 'AttributeOption')
    AttributeOption.objects.filter(product__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0006_add_product_to_attribute_option'),
    ]

    operations = [
        # First, delete any remaining global options
        migrations.RunPython(delete_global_options, migrations.RunPython.noop),
        
        # Then make the product field required
        migrations.AlterField(
            model_name='attributeoption',
            name='product',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='attribute_options',
                to='catalog.product',
                verbose_name='Produto'
            ),
        ),
    ]
