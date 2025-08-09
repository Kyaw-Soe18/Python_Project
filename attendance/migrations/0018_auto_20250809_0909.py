from django.db import migrations

def fill_section(apps, schema_editor):
    Course = apps.get_model('attendance', 'Course')
    Course.objects.filter(section__isnull=True).update(section='E-000')

class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0017_alter_course_section'),  # use your latest migration here
    ]

    operations = [
        migrations.RunPython(fill_section),
    ]
