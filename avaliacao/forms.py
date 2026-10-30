from django import forms

from .models import AvaliacaoTurma


class AvaliacaoTurmaForm(forms.ModelForm):
    class Meta:
        model = AvaliacaoTurma
        fields = [
            'classificacao',
            'comentarios',
            'destaques_positivos',
            'destaques_negativos',
            'comentario_destaques',
        ]
        widgets = {
            'classificacao': forms.RadioSelect,
            'comentarios': forms.Textarea(attrs={'rows': 3}),
            'destaques_positivos': forms.Textarea(attrs={'rows': 3}),
            'destaques_negativos': forms.Textarea(attrs={'rows': 3}),
            'comentario_destaques': forms.Textarea(attrs={'rows': 3}),
        }
