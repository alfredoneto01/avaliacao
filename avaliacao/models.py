import uuid

from django.db import models
from django.urls import reverse

ESCALA = [
    (1, 'Ruim'),
    (2, 'Regular'),
    (3, 'Bom'),
    (4, 'Excelente'),
]

ESCALA_TURMA = [
    (4, 'Excelente'),
    (3, 'Boa'),
    (2, 'Regular'),
    (1, 'Ruim'),
]


class Semestre(models.Model):
    nome = models.CharField(max_length=20, unique=True, help_text='Ex.: 2026.2')
    aberto = models.BooleanField(
        default=True, help_text='Só é possível responder enquanto o semestre estiver aberto.'
    )

    class Meta:
        ordering = ['-nome']

    def __str__(self):
        return self.nome


class Professor(models.Model):
    nome = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ['nome']
        verbose_name_plural = 'professores'

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        return reverse('avaliacao:professor', args=[self.token])


class Turma(models.Model):
    semestre = models.ForeignKey(Semestre, on_delete=models.PROTECT, related_name='turmas')
    nome = models.CharField(max_length=60, help_text='Ex.: 1º ano')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ['semestre', 'nome']
        constraints = [
            models.UniqueConstraint(fields=['semestre', 'nome'], name='turma_unica_por_semestre')
        ]

    def __str__(self):
        return f'{self.nome} – {self.semestre}'

    def get_absolute_url(self):
        return reverse('avaliacao:aluno', args=[self.token])


class Disciplina(models.Model):
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name='disciplinas')
    nome = models.CharField(max_length=120)
    professor = models.ForeignKey(Professor, on_delete=models.PROTECT, related_name='disciplinas')
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['turma', 'ordem', 'nome']

    def __str__(self):
        return f'{self.nome} – {self.professor}'


class Item(models.Model):
    """Pergunta do formulário do aluno, repetida para cada disciplina."""

    class Grupo(models.TextChoices):
        DIDATICA = 'didatica', 'Aspectos didáticos do desempenho do professor'
        POSTURA = 'postura', 'Aspectos relativos à postura do docente'
        AUTOAVALIACAO = 'autoavaliacao', 'Aspectos relativos à participação do aluno - autoavaliação'

    grupo = models.CharField(max_length=20, choices=Grupo.choices)
    texto = models.CharField(max_length=200)
    ordem = models.PositiveSmallIntegerField(default=0)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['ordem']
        verbose_name = 'pergunta do aluno'
        verbose_name_plural = 'perguntas do aluno'

    def __str__(self):
        return self.texto


class RespostaAluno(models.Model):
    """Um envio do formulário do aluno, anônimo a menos que ele informe o nome.

    Não guarda IP nem navegador em texto: apenas hashes, suficientes para
    detectar envios repetidos sem permitir identificar o aluno.
    """

    turma = models.ForeignKey(Turma, on_delete=models.PROTECT, related_name='respostas')
    nome = models.CharField('Nome do aluno', max_length=120, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    ip_hash = models.CharField(max_length=16, db_index=True)
    navegador_hash = models.CharField(max_length=16)
    descartada = models.BooleanField(
        default=False, help_text='Respostas descartadas não entram nos relatórios.'
    )

    class Meta:
        ordering = ['-criada_em']
        verbose_name = 'resposta de aluno'
        verbose_name_plural = 'respostas de alunos'

    def __str__(self):
        return f'Resposta #{self.pk} – {self.turma}'


class Nota(models.Model):
    resposta = models.ForeignKey(RespostaAluno, on_delete=models.CASCADE, related_name='notas')
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT, related_name='notas')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='notas')
    valor = models.PositiveSmallIntegerField(choices=ESCALA)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['resposta', 'disciplina', 'item'], name='nota_unica_por_resposta'
            )
        ]


class AvaliacaoTurma(models.Model):
    """Avaliação (identificada) que o professor faz de uma turma."""

    turma = models.ForeignKey(Turma, on_delete=models.PROTECT, related_name='avaliacoes_professores')
    professor = models.ForeignKey(Professor, on_delete=models.PROTECT, related_name='avaliacoes')
    classificacao = models.PositiveSmallIntegerField(
        'Em linhas gerais, você classifica a turma como', choices=ESCALA_TURMA
    )
    comentarios = models.TextField('Comentários', blank=True)
    destaques_positivos = models.TextField('Alunos destaques positivos (citar nomes)', blank=True)
    destaques_negativos = models.TextField('Alunos destaques negativos (citar nomes)', blank=True)
    comentario_destaques = models.TextField('Comentário (sobre os alunos destaques)', blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['turma', 'professor']
        verbose_name = 'avaliação de turma'
        verbose_name_plural = 'avaliações de turmas'
        constraints = [
            models.UniqueConstraint(fields=['turma', 'professor'], name='uma_avaliacao_por_professor')
        ]

    def __str__(self):
        return f'{self.professor} → {self.turma}'
