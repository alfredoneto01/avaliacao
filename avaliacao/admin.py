from django.contrib import admin
from django.utils.html import format_html

from .models import AvaliacaoTurma, Disciplina, Item, Professor, RespostaAluno, Semestre, Turma


def link_publico(obj):
    if not obj.pk:
        return 'Disponível após salvar.'
    url = obj.get_absolute_url()
    return format_html('<a href="{0}" target="_blank">{0}</a>', url)


link_publico.short_description = 'Link do formulário'


class TurmaInline(admin.TabularInline):
    model = Turma
    extra = 0
    show_change_link = True


@admin.register(Semestre)
class SemestreAdmin(admin.ModelAdmin):
    list_display = ['nome', 'aberto']
    list_editable = ['aberto']
    inlines = [TurmaInline]


class DisciplinaInline(admin.TabularInline):
    model = Disciplina
    extra = 1
    autocomplete_fields = ['professor']


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'semestre', link_publico]
    list_filter = ['semestre']
    readonly_fields = [link_publico]
    inlines = [DisciplinaInline]


@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'email', link_publico]
    search_fields = ['nome']
    readonly_fields = [link_publico]


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['texto', 'grupo', 'ordem', 'ativo']
    list_editable = ['ordem', 'ativo']
    list_filter = ['grupo']


@admin.register(RespostaAluno)
class RespostaAlunoAdmin(admin.ModelAdmin):
    list_display = ['pk', 'turma', 'nome', 'criada_em', 'ip_hash', 'descartada']
    list_filter = ['turma__semestre', 'turma', 'descartada']
    list_editable = ['descartada']
    search_fields = ['nome']
    readonly_fields = ['turma', 'nome', 'criada_em', 'ip_hash', 'navegador_hash']

    def has_add_permission(self, request):
        return False


@admin.register(AvaliacaoTurma)
class AvaliacaoTurmaAdmin(admin.ModelAdmin):
    list_display = ['turma', 'professor', 'classificacao', 'atualizada_em']
    list_filter = ['turma__semestre', 'turma', 'professor']

    def has_add_permission(self, request):
        return False
