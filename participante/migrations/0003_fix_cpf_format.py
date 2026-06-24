from django.db import migrations


def fix_cpf_format(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("participante", "Profile")

    # Fix CPFs in User model
    for user in User.objects.all():
        if user.username:
            user.username = "".join(filter(str.isdigit, user.username))
            user.save()

    # Fix CPFs in Profile model
    for profile in Profile.objects.all():
        if profile.CPF:
            profile.CPF = "".join(filter(str.isdigit, profile.CPF))
            profile.save()


class Migration(migrations.Migration):

    dependencies = [
        ("participante", "0002_roles_and_permissions"),
    ]

    operations = [
        migrations.RunPython(fix_cpf_format),
    ]
