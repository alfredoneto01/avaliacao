from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Avaliação do Seminário – Coordenação'
admin.site.site_title = 'Avaliação do Seminário'
admin.site.index_title = 'Cadastros'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('avaliacao.urls')),
]
