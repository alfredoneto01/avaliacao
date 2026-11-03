from io import BytesIO

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from openpyxl import Workbook

from . import relatorios
from .forms import AvaliacaoTurmaForm
from .models import ESCALA, AvaliacaoTurma, Item, Nota, Professor, RespostaAluno, Semestre, Turma

# ---------------------------------------------------------------- aluno


def aluno(request, token):
    turma = get_object_or_404(Turma.objects.select_related('semestre'), token=token)
    if not turma.semestre.aberto:
        return render(request, 'avaliacao/fechado.html', {'turma': turma})

    disciplinas = list(turma.disciplinas.select_related('professor'))
    itens = list(Item.objects.filter(ativo=True))
    valores_validos = {str(v) for v, _ in ESCALA}
    marcados, faltando = {}, set()
    nome = request.POST.get('nome', '').strip()[:120]

    if request.method == 'POST':
        for d in disciplinas:
            for i in itens:
                campo = f'n_{d.pk}_{i.pk}'
                valor = request.POST.get(campo)
                if valor in valores_validos:
                    marcados[campo] = valor
                else:
                    faltando.add(d.pk)
        if not faltando:
            with transaction.atomic():
                resposta = RespostaAluno.objects.create(
                    turma=turma,
                    nome=nome,
                    ip_hash=relatorios.hash_curto(relatorios.ip_do_request(request)),
                    navegador_hash=relatorios.hash_curto(request.META.get('HTTP_USER_AGENT', '')),
                )
                Nota.objects.bulk_create(
                    Nota(resposta=resposta, disciplina=d, item=i, valor=int(marcados[f'n_{d.pk}_{i.pk}']))
                    for d in disciplinas
                    for i in itens
                )
            return redirect('avaliacao:obrigado')

    blocos = []
    for d in disciplinas:
        for grupo, rotulo in Item.Grupo.choices:
            linhas = [
                {'item': i, 'campo': f'n_{d.pk}_{i.pk}', 'marcado': marcados.get(f'n_{d.pk}_{i.pk}')}
                for i in itens
                if i.grupo == grupo
            ]
            if linhas:
                blocos.append({
                    'disciplina': d, 'rotulo': rotulo, 'linhas': linhas, 'erro': d.pk in faltando,
                })

    return render(request, 'avaliacao/aluno.html', {
        'turma': turma, 'blocos': blocos, 'escala': ESCALA, 'tem_erro': bool(faltando), 'nome': nome,
    })


def obrigado(request):
    return render(request, 'avaliacao/obrigado.html')


# ---------------------------------------------------------------- professor


def professor(request, token):
    prof = get_object_or_404(Professor, token=token)
    turmas = (
        Turma.objects.filter(disciplinas__professor=prof, semestre__aberto=True)
        .select_related('semestre')
        .distinct()
    )
    respondidas = set(prof.avaliacoes.values_list('turma_id', flat=True))
    return render(request, 'avaliacao/professor.html', {
        'professor': prof,
        'turmas': [(t, t.pk in respondidas) for t in turmas],
    })


def professor_turma(request, token, turma_id):
    prof = get_object_or_404(Professor, token=token)
    turma = get_object_or_404(
        Turma.objects.select_related('semestre').distinct(),
        pk=turma_id, disciplinas__professor=prof,
    )
    if not turma.semestre.aberto:
        return render(request, 'avaliacao/fechado.html', {'turma': turma})

    existente = AvaliacaoTurma.objects.filter(turma=turma, professor=prof).first()
    form = AvaliacaoTurmaForm(request.POST or None, instance=existente)
    if request.method == 'POST' and form.is_valid():
        avaliacao = form.save(commit=False)
        avaliacao.turma, avaliacao.professor = turma, prof
        avaliacao.save()
        messages.success(request, f'Avaliação da turma {turma.nome} salva. Obrigado!')
        return redirect('avaliacao:professor', token=token)

    return render(request, 'avaliacao/professor_turma.html', {
        'professor': prof, 'turma': turma, 'form': form, 'editando': existente is not None,
    })


# ---------------------------------------------------------------- coordenação


@staff_member_required
def painel(request):
    semestres = []
    for s in Semestre.objects.all():
        turmas = []
        for t in s.turmas.all():
            respostas = t.respostas.all()
            professores = Professor.objects.filter(disciplinas__turma=t).distinct()
            responderam = set(t.avaliacoes_professores.values_list('professor_id', flat=True))
            turmas.append({
                'turma': t,
                'link': request.build_absolute_uri(t.get_absolute_url()),
                'n_respostas': respostas.filter(descartada=False).count(),
                'n_descartadas': respostas.filter(descartada=True).count(),
                'n_suspeitos': sum(len(g['respostas']) for g in relatorios.grupos_suspeitos(t)),
                'professores': [(p, p.pk in responderam) for p in professores],
            })
        semestres.append({'semestre': s, 'turmas': turmas})
    return render(request, 'avaliacao/coordenacao/painel.html', {'semestres': semestres})


@staff_member_required
def relatorio_semestre(request, pk):
    semestre = get_object_or_404(Semestre, pk=pk)
    return render(request, 'avaliacao/coordenacao/semestre.html', {
        'semestre': semestre,
        'professores': relatorios.consolidado_professores(semestre),
        'turmas': semestre.turmas.all(),
    })


@staff_member_required
def relatorio_turma(request, pk):
    turma = get_object_or_404(Turma.objects.select_related('semestre'), pk=pk)
    disciplinas = [
        {'disciplina': d, 'grupos': relatorios.detalhe_disciplina(d)}
        for d in turma.disciplinas.select_related('professor')
    ]
    return render(request, 'avaliacao/coordenacao/turma.html', {
        'turma': turma,
        'n_respostas': turma.respostas.filter(descartada=False).count(),
        'disciplinas': disciplinas,
        'avaliacoes': turma.avaliacoes_professores.select_related('professor'),
        'escala': ESCALA,
    })


@staff_member_required
def duplicidades(request, pk):
    turma = get_object_or_404(Turma.objects.select_related('semestre'), pk=pk)
    return render(request, 'avaliacao/coordenacao/duplicidades.html', {
        'turma': turma, 'grupos': relatorios.grupos_suspeitos(turma),
    })


@staff_member_required
@require_POST
def alternar_descarte(request, pk):
    resposta = get_object_or_404(RespostaAluno, pk=pk)
    resposta.descartada = not resposta.descartada
    resposta.save(update_fields=['descartada'])
    return redirect('avaliacao:duplicidades', pk=resposta.turma_id)


@staff_member_required
def exportar_excel(request, pk):
    semestre = get_object_or_404(Semestre, pk=pk)
    wb = Workbook()
    rotulo = dict(ESCALA)

    ws = wb.active
    ws.title = 'Professores'
    ws.append(['Professor', 'Disciplinas', 'Didática', 'Postura', 'Autoavaliação dos alunos'])
    for p in relatorios.consolidado_professores(semestre):
        ws.append([p['nome'], p['n_disciplinas'], p['didatica'], p['postura'], p['autoavaliacao']])

    ws = wb.create_sheet('Disciplinas')
    ws.append(['Turma', 'Disciplina', 'Professor', 'Grupo', 'Pergunta', 'Média', 'Respostas'])
    for turma in semestre.turmas.all():
        for d in turma.disciplinas.select_related('professor'):
            for g in relatorios.detalhe_disciplina(d):
                for i in g['itens']:
                    ws.append([turma.nome, d.nome, d.professor.nome, g['rotulo'], i['texto'], i['media'], i['total']])

    ws = wb.create_sheet('Respostas dos alunos')
    ws.append(['Resposta', 'Data', 'Aluno', 'Turma', 'Disciplina', 'Professor', 'Pergunta', 'Nota', 'Valor',
               'Descartada'])
    notas = Nota.objects.filter(resposta__turma__semestre=semestre).select_related(
        'resposta__turma', 'disciplina__professor', 'item'
    ).order_by('resposta_id', 'disciplina__ordem', 'item__ordem')
    for n in notas:
        ws.append([
            n.resposta_id, n.resposta.criada_em.replace(tzinfo=None), n.resposta.nome, n.resposta.turma.nome,
            n.disciplina.nome, n.disciplina.professor.nome, n.item.texto,
            rotulo[n.valor], n.valor, 'sim' if n.resposta.descartada else 'não',
        ])

    ws = wb.create_sheet('Avaliações das turmas')
    ws.append(['Turma', 'Professor', 'Classificação', 'Comentários', 'Destaques positivos',
               'Destaques negativos', 'Comentário sobre destaques', 'Atualizada em'])
    for a in AvaliacaoTurma.objects.filter(turma__semestre=semestre).select_related('turma', 'professor'):
        ws.append([
            a.turma.nome, a.professor.nome, a.get_classificacao_display(), a.comentarios,
            a.destaques_positivos, a.destaques_negativos, a.comentario_destaques,
            a.atualizada_em.replace(tzinfo=None),
        ])

    saida = BytesIO()
    wb.save(saida)
    resposta = HttpResponse(
        saida.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    resposta['Content-Disposition'] = f'attachment; filename="avaliacao-{semestre.nome}.xlsx"'
    return resposta
