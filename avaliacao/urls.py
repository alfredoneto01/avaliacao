from django.urls import path

from . import views

app_name = 'avaliacao'

urlpatterns = [
    path('a/<uuid:token>/', views.aluno, name='aluno'),
    path('obrigado/', views.obrigado, name='obrigado'),
    path('p/<uuid:token>/', views.professor, name='professor'),
    path('p/<uuid:token>/turma/<int:turma_id>/', views.professor_turma, name='professor_turma'),
    path('', views.painel, name='painel'),
    path('coordenacao/semestre/<int:pk>/', views.relatorio_semestre, name='semestre'),
    path('coordenacao/semestre/<int:pk>/excel/', views.exportar_excel, name='excel'),
    path('coordenacao/turma/<int:pk>/', views.relatorio_turma, name='turma'),
    path('coordenacao/turma/<int:pk>/duplicidades/', views.duplicidades, name='duplicidades'),
    path('coordenacao/resposta/<int:pk>/descartar/', views.alternar_descarte, name='descartar'),
]
