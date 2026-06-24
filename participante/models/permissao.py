from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from lojista.models import Lojista
from django.urls import reverse
from django.core import validators
from django.core.mail import EmailMessage
import datetime
from datetime import timedelta
from django.utils import timezone
import logging
from django.utils.timezone import now
from django.db.models import F, ExpressionWrapper, DurationField, Sum
from django.utils.timezone import localtime
from django.contrib.auth import get_user_model

User = get_user_model()




class SystemRole(models.Model):
    """
    Modelo para armazenar funções do sistema.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_system_role = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="roles_created",
    )

    class Meta:
        verbose_name = "Função do Sistema"
        verbose_name_plural = "Funções do Sistema"
        ordering = ["name"]

    def __str__(self):
        return self.name


class SystemPermission(models.Model):
    """
    Modelo para armazenar permissões do sistema.
    """

    CATEGORIES = [
        ("dashboard", "Dashboard"),
        ("documents", "Documentos"),
        ("stores", "Lojistas"),
        ("system", "Sistema"),
        ("jornadas", "Jornadas de Trabalho"),
    ]

    name = models.CharField(max_length=100, unique=True)
    codename = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORIES)
    description = models.TextField(blank=True)
    is_system_permission = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Permissão do Sistema"
        verbose_name_plural = "Permissões do Sistema"
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.get_category_display()} - {self.name}"


class SystemResource(models.Model):
    """
    Modelo para armazenar recursos do sistema.
    """

    name = models.CharField(max_length=100, unique=True)
    codename = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50)
    url = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_system_resource = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Recurso do Sistema"
        verbose_name_plural = "Recursos do Sistema"
        ordering = ["name"]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """
    Modelo para relacionar funções e permissões.
    """

    role = models.ForeignKey(SystemRole, on_delete=models.CASCADE)
    permission = models.ForeignKey(SystemPermission, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["role", "permission"]
        verbose_name = "Permissão da Função"
        verbose_name_plural = "Permissões das Funções"


class RoleResource(models.Model):
    """
    Modelo para relacionar funções e recursos.
    """

    role = models.ForeignKey(SystemRole, on_delete=models.CASCADE)
    resource = models.ForeignKey(SystemResource, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["role", "resource"]
        verbose_name = "Recurso da Função"
        verbose_name_plural = "Recursos das Funções"


class UserRole(models.Model):
    """
    Modelo para relacionar usuários e funções.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.ForeignKey(SystemRole, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="user_roles_created",
    )

    class Meta:
        unique_together = ["user", "role"]
        verbose_name = "Função do Usuário"
        verbose_name_plural = "Funções dos Usuários"


