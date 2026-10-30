from django.db import migrations

PERGUNTAS = [
    ('didatica', 'Quanto ao planejamento e organização da aula'),
    ('didatica', 'Quanto à clareza e objetividade da aula'),
    ('didatica', 'Quanto à capacidade de promover conexão do aspecto teórico com a prática'),
    ('didatica', 'Quanto à promoção de esclarecimentos de dúvidas'),
    ('postura', 'Quanto ao cumprimento do horário previsto'),
    ('postura', 'Quanto à forma de tratamento com alunos'),
    ('postura', 'Quanto a domínio e segurança sobre disciplina que ministra'),
    ('autoavaliacao', 'Quanto à capacidade de manter-se atento à aula'),
    ('autoavaliacao', 'Quanto ao cumprimento das tarefas passadas pelo professor'),
]


def criar(apps, schema_editor):
    Item = apps.get_model('avaliacao', 'Item')
    for ordem, (grupo, texto) in enumerate(PERGUNTAS, start=1):
        Item.objects.create(grupo=grupo, texto=texto, ordem=ordem)


def remover(apps, schema_editor):
    apps.get_model('avaliacao', 'Item').objects.filter(texto__in=[t for _, t in PERGUNTAS]).delete()


class Migration(migrations.Migration):
    dependencies = [('avaliacao', '0001_initial')]
    operations = [migrations.RunPython(criar, remover)]
