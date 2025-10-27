# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0005_course_enrollment_count'),
    ]

    operations = [
        migrations.RenameField(
            model_name='course',
            old_name='enrollment_count',
            new_name='registration_count',
        ),
    ]
