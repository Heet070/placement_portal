from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0008_remove_student_placed_profile_offer_type_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[('admin', 'Admin'), ('super_admin', 'Super Admin')],
                    default='admin', max_length=20
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reset_token', models.CharField(blank=True, max_length=128, null=True)),
                ('reset_token_expires', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_admins',
                    to=settings.AUTH_USER_MODEL
                )),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='admin_profile',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'db_table': 'admin_profile',
            },
        ),
    ]
