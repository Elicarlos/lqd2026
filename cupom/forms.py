from django import forms

from .models import Cupom


class AddCupomForm(forms.Form):
    class Meta:
        model = Cupom
        fields = "__all__"


class EditCupomForm(forms.Form):
    class Meta:
        model = Cupom
        fields = "__all__"
        widgets = {
            "user": forms.HiddenInput,
        }
