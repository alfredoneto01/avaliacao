# Publicar no PythonAnywhere

Em todos os comandos, troque `SEUUSUARIO` pelo seu nome de usuário do PythonAnywhere.

## 1. Baixar o código e instalar

No PythonAnywhere, abra **Consoles → Bash** e cole:

```bash
git clone https://github.com/alfredoneto01/avaliacao.git
cd avaliacao
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

> Se aparecer `python3.13: command not found`, use `python3.12` no lugar.

## 2. Criar o arquivo de configuração (.env)

Ainda no console:

```bash
cat > .env <<EOF
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=SEUUSUARIO.pythonanywhere.com
DJANGO_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
EOF
```

> **Nunca apague nem troque a `DJANGO_SECRET_KEY` depois que as avaliações começarem.**
> Ela é usada para comparar os IPs nas duplicidades e para o login.

## 3. Criar o banco e o usuário da coordenação

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py createsuperuser
```

O último comando pede nome de usuário, e-mail (pode deixar em branco) e senha.

## 4. Criar o site

1. Vá na aba **Web** → **Add a new web app** → **Next**.
2. Escolha **Manual configuration** (não escolha "Django") → mesma versão do Python do passo 1 → **Next**.
3. Na página do site, preencha:
   - **Virtualenv:** `/home/SEUUSUARIO/avaliacao/.venv`
   - **Static files:** URL `/static/` → Directory `/home/SEUUSUARIO/avaliacao/staticfiles`
4. Ainda na página, ative **Force HTTPS**.
5. Clique no link do **WSGI configuration file**, **apague todo o conteúdo** e cole:

   ```python
   import os
   import sys

   sys.path.insert(0, '/home/SEUUSUARIO/avaliacao')
   os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

   Clique em **Save**.
6. Volte na aba **Web** e clique no botão verde **Reload**.

Pronto: acesse `https://SEUUSUARIO.pythonanywhere.com/` e entre com o usuário criado no passo 3.

## Atualizar depois de mudanças no código

No console Bash:

```bash
cd ~/avaliacao
git pull
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
```

Depois clique em **Reload** na aba **Web**.

## Backup

O banco inteiro é o arquivo `/home/SEUUSUARIO/avaliacao/db.sqlite3`.
Para baixar uma cópia: aba **Files** → pasta `avaliacao` → clique em `db.sqlite3` para baixar.
Faça isso ao fim de cada período de avaliação.

## Plano gratuito

A cada 3 meses o PythonAnywhere envia um e-mail pedindo para estender o site.
Basta entrar na aba **Web** e clicar em **Run until 3 months from today**.
