from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from . import relatorios
from .models import AvaliacaoTurma, Disciplina, Item, Nota, Professor, RespostaAluno, Semestre, Turma


class Base(TestCase):
    def setUp(self):
        self.semestre = Semestre.objects.create(nome='2026.2')
        self.turma = Turma.objects.create(semestre=self.semestre, nome='1º ano')
        self.nielsen = Professor.objects.create(nome='Nielsen')
        self.romualdo = Professor.objects.create(nome='Romualdo')
        self.hebraico = Disciplina.objects.create(turma=self.turma, nome='Hebraico I', professor=self.nielsen)
        self.vocacao = Disciplina.objects.create(turma=self.turma, nome='Vocação', professor=self.romualdo)
        self.itens = list(Item.objects.all())

    def respostas_completas(self, valor=4):
        return {f'n_{d.pk}_{i.pk}': str(valor) for d in (self.hebraico, self.vocacao) for i in self.itens}

    def enviar_aluno(self, dados, ip='10.0.0.1', ua='Firefox'):
        return self.client.post(
            self.turma.get_absolute_url(), dados, REMOTE_ADDR=ip, HTTP_USER_AGENT=ua
        )


class FormularioAlunoTests(Base):
    def test_perguntas_iniciais_criadas(self):
        self.assertEqual(len(self.itens), 9)

    def test_envio_completo_grava_notas_anonimas(self):
        resp = self.enviar_aluno(self.respostas_completas())
        self.assertRedirects(resp, reverse('avaliacao:obrigado'))
        resposta = RespostaAluno.objects.get()
        self.assertEqual(resposta.notas.count(), 18)
        self.assertNotIn('10.0.0.1', resposta.ip_hash)
        self.assertEqual(resposta.ip_hash, relatorios.hash_curto('10.0.0.1'))

    def test_envio_incompleto_e_recusado_mantendo_marcacoes(self):
        dados = self.respostas_completas(3)
        dados.pop(f'n_{self.vocacao.pk}_{self.itens[0].pk}')
        resp = self.enviar_aluno(dados)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Faltou responder')
        self.assertContains(resp, 'checked', count=17)
        self.assertFalse(RespostaAluno.objects.exists())

    def test_valor_fora_da_escala_e_recusado(self):
        dados = self.respostas_completas()
        dados[f'n_{self.hebraico.pk}_{self.itens[0].pk}'] = '9'
        self.enviar_aluno(dados)
        self.assertFalse(RespostaAluno.objects.exists())

    def test_semestre_fechado(self):
        self.semestre.aberto = False
        self.semestre.save()
        resp = self.enviar_aluno(self.respostas_completas())
        self.assertContains(resp, 'Avaliação encerrada')
        self.assertFalse(RespostaAluno.objects.exists())

    def test_ip_atras_de_proxy(self):
        self.client.post(
            self.turma.get_absolute_url(), self.respostas_completas(),
            HTTP_X_FORWARDED_FOR='200.1.1.1, 10.0.0.9',
        )
        self.assertEqual(RespostaAluno.objects.get().ip_hash, relatorios.hash_curto('200.1.1.1'))


class FormularioProfessorTests(Base):
    def url(self, prof=None, turma=None):
        prof, turma = prof or self.nielsen, turma or self.turma
        return reverse('avaliacao:professor_turma', args=[prof.token, turma.pk])

    def test_lista_turmas_do_professor(self):
        resp = self.client.get(self.nielsen.get_absolute_url())
        self.assertContains(resp, '1º ano')
        self.assertContains(resp, 'pendente')

    def test_salva_e_depois_edita(self):
        self.client.post(self.url(), {'classificacao': 3, 'destaques_positivos': 'João'})
        self.client.post(self.url(), {'classificacao': 4, 'destaques_positivos': 'João e Maria'})
        avaliacao = AvaliacaoTurma.objects.get()
        self.assertEqual((avaliacao.professor, avaliacao.classificacao), (self.nielsen, 4))
        self.assertEqual(avaliacao.destaques_positivos, 'João e Maria')

    def test_classificacao_obrigatoria(self):
        resp = self.client.post(self.url(), {'comentarios': 'oi'})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(AvaliacaoTurma.objects.exists())

    def test_professor_nao_acessa_turma_alheia(self):
        outra = Turma.objects.create(semestre=self.semestre, nome='2º ano')
        Disciplina.objects.create(turma=outra, nome='Grego', professor=self.romualdo)
        self.assertEqual(self.client.get(self.url(turma=outra)).status_code, 404)


class CoordenacaoTests(Base):
    def setUp(self):
        super().setUp()
        self.coord = User.objects.create_user('coord', password='x', is_staff=True)

    def test_exige_login(self):
        resp = self.client.get(reverse('avaliacao:painel'))
        self.assertEqual(resp.status_code, 302)

    def test_relatorios_e_descarte(self):
        self.enviar_aluno(self.respostas_completas(4), ua='A')
        self.enviar_aluno(self.respostas_completas(2), ua='A')
        self.enviar_aluno(self.respostas_completas(4), ip='10.0.0.2')
        consolidado = {p['nome']: p for p in relatorios.consolidado_professores(self.semestre)}
        self.assertAlmostEqual(consolidado['Nielsen']['didatica'], 10 / 3)

        grupos = relatorios.grupos_suspeitos(self.turma)
        self.assertEqual(len(grupos), 1)
        self.assertTrue(all(r.mesmo_aparelho for r in grupos[0]['respostas']))

        self.client.force_login(self.coord)
        segunda = grupos[0]['respostas'][1]
        self.client.post(reverse('avaliacao:descartar', args=[segunda.pk]))
        consolidado = {p['nome']: p for p in relatorios.consolidado_professores(self.semestre)}
        self.assertEqual(consolidado['Nielsen']['didatica'], 4)

        for nome in ('painel',):
            self.assertEqual(self.client.get(reverse(f'avaliacao:{nome}')).status_code, 200)
        for nome in ('semestre', 'excel'):
            self.assertEqual(self.client.get(reverse(f'avaliacao:{nome}', args=[self.semestre.pk])).status_code, 200)
        for nome in ('turma', 'duplicidades'):
            self.assertEqual(self.client.get(reverse(f'avaliacao:{nome}', args=[self.turma.pk])).status_code, 200)
        self.assertEqual(Nota.objects.count(), 54)
