"""Cálculos dos relatórios. Respostas descartadas nunca entram nas contas."""

import hashlib
import hmac
from collections import defaultdict

from django.conf import settings
from django.db.models import Avg, Count

from .models import ESCALA, Item, Nota, RespostaAluno

GRUPOS_PROFESSOR = [Item.Grupo.DIDATICA, Item.Grupo.POSTURA]


def hash_curto(valor):
    """HMAC do valor com a SECRET_KEY: permite comparar sem guardar o original."""
    return hmac.new(settings.SECRET_KEY.encode(), valor.encode(), hashlib.sha256).hexdigest()[:16]


def ip_do_request(request):
    encaminhado = request.META.get('HTTP_X_FORWARDED_FOR')
    if encaminhado:
        return encaminhado.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def notas_validas():
    return Nota.objects.filter(resposta__descartada=False)


def detalhe_disciplina(disciplina):
    """Média e distribuição de cada item, agrupados como no formulário."""
    por_item = {
        linha['item']: linha
        for linha in notas_validas()
        .filter(disciplina=disciplina)
        .values('item')
        .annotate(media=Avg('valor'), total=Count('id'))
    }
    distribuicao = defaultdict(dict)
    for linha in (
        notas_validas().filter(disciplina=disciplina).values('item', 'valor').annotate(n=Count('id'))
    ):
        distribuicao[linha['item']][linha['valor']] = linha['n']

    grupos = []
    for grupo, rotulo in Item.Grupo.choices:
        itens = []
        for item in Item.objects.filter(grupo=grupo):
            dados = por_item.get(item.pk)
            itens.append({
                'texto': item.texto,
                'media': dados['media'] if dados else None,
                'total': dados['total'] if dados else 0,
                'distribuicao': [distribuicao[item.pk].get(v, 0) for v, _ in ESCALA],
            })
        media_grupo = (
            notas_validas()
            .filter(disciplina=disciplina, item__grupo=grupo)
            .aggregate(m=Avg('valor'))['m']
        )
        grupos.append({'rotulo': rotulo, 'itens': itens, 'media': media_grupo})
    return grupos


def medias_por_grupo(notas):
    """{grupo: média} para um queryset de notas."""
    return {
        linha['item__grupo']: linha['media']
        for linha in notas.values('item__grupo').annotate(media=Avg('valor'))
    }


def consolidado_professores(semestre):
    """Uma linha por professor, somando todas as disciplinas dele no semestre."""
    notas = notas_validas().filter(disciplina__turma__semestre=semestre)
    linhas = defaultdict(lambda: {'disciplinas': set(), 'medias': {}})
    for linha in notas.values(
        'disciplina__professor', 'disciplina__professor__nome', 'item__grupo'
    ).annotate(media=Avg('valor')):
        dados = linhas[linha['disciplina__professor']]
        dados['nome'] = linha['disciplina__professor__nome']
        dados['medias'][linha['item__grupo']] = linha['media']
    for linha in notas.values('disciplina__professor', 'disciplina').distinct():
        linhas[linha['disciplina__professor']]['disciplinas'].add(linha['disciplina'])

    resultado = []
    for dados in linhas.values():
        resultado.append({
            'nome': dados['nome'],
            'n_disciplinas': len(dados['disciplinas']),
            'didatica': dados['medias'].get(Item.Grupo.DIDATICA),
            'postura': dados['medias'].get(Item.Grupo.POSTURA),
            'autoavaliacao': dados['medias'].get(Item.Grupo.AUTOAVALIACAO),
        })
    return sorted(resultado, key=lambda r: r['nome'])


def grupos_suspeitos(turma):
    """Respostas da turma que compartilham o mesmo IP (hash), mais recentes primeiro."""
    repetidos = (
        RespostaAluno.objects.filter(turma=turma)
        .values('ip_hash')
        .annotate(n=Count('id'))
        .filter(n__gt=1)
        .values_list('ip_hash', flat=True)
    )
    grupos = []
    for ip_hash in repetidos:
        respostas = list(
            RespostaAluno.objects.filter(turma=turma, ip_hash=ip_hash).order_by('criada_em')
        )
        mesmos_aparelhos = defaultdict(int)
        for r in respostas:
            mesmos_aparelhos[r.navegador_hash] += 1
        for r in respostas:
            r.mesmo_aparelho = mesmos_aparelhos[r.navegador_hash] > 1
        grupos.append({'ip_hash': ip_hash, 'respostas': respostas})
    return grupos
