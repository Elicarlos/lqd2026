"""
Module: Barcode Printer URLS
Project: Django BCP
Copyright: Adlibre Pty Ltd 2012
License: See LICENSE for license information
"""

from django.urls import path

from . import views

# import mdtui.views

app_name = "bcp"

urlpatterns = [
    path("print/<int:id_>/", views.print_barcode, name="print"),
    path("print_get/<int:id_>/", views.print_barcode_get, name="print_get"),

    path(
        "print_embed/<int:id_>/", views.print_barcode_embed_example, name="print_embed"
    ),
    path("print_qrcode/<int:id_>/", views.print_qrcode, name="print_qrcode"),
    path("generate/<int:id_>/", views.generate, name="generate"),
    path(
        "check_task_status/<str:task_id>/",
        views.check_task_status,
        name="check_task_status",
    ),
    path(
        "serve_pdf_from_task/<str:task_id>/",
        views.serve_pdf_from_task,
        name="serve_pdf_from_task",
    ),
    path("confirm_print/<int:id_>/", views.confirm_print, name="confirm_print"),
    path(
        "check_print_status/<int:id_>/",
        views.check_print_status,
        name="check_print_status",
    ),
    path(
        "clear_print_session/<int:id_>/",
        views.clear_print_session,
        name="clear_print_session",
    ),
]
# handler404 = 'participante.views.not_found_page_view'
# handler500 = 'participante.views.server_error_view'
