from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('portal', '0001_initial')]
    operations = [
        migrations.AddField(
            model_name='experimento',
            name='ajuste_id',
            field=models.UUIDField(editable=False, null=True),
        ),
    ]
