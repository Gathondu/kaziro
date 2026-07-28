from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0003_userprofile_profile_embedding"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="cv_original_filename",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
