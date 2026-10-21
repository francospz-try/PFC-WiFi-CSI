"""ConfiguraciÃ³n local. La clave privada SOLO va por variable de entorno."""
from pathlib import Path
import os
BASE_DIR=Path(__file__).resolve().parent.parent
PROJECT_DIR=BASE_DIR.parent
SECRET_KEY=os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('Configura DJANGO_SECRET_KEY antes de iniciar Django. Ver README.')
DEBUG=os.environ.get('DJANGO_DEBUG','0')=='1'
ALLOWED_HOSTS=['localhost','127.0.0.1','testserver']
INSTALLED_APPS=['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','portal']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.debug','django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE='es'
TIME_ZONE='America/Lima'
USE_I18N=True
USE_TZ=True
STATIC_URL='static/'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
LOGIN_URL='login'
LOGIN_REDIRECT_URL='dashboard'
LOGOUT_REDIRECT_URL='login'
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE='Lax'
SESSION_COOKIE_AGE=1800
SESSION_SAVE_EVERY_REQUEST=True
SESSION_EXPIRE_AT_BROWSER_CLOSE=True
CSRF_COOKIE_SAMESITE='Lax'
SESSION_COOKIE_SECURE=os.environ.get('DJANGO_HTTPS','0')=='1'
CSRF_COOKIE_SECURE=SESSION_COOKIE_SECURE
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_REFERRER_POLICY='same-origin'
X_FRAME_OPTIONS='DENY'
DATA_DIR=(PROJECT_DIR/'datos_locales').resolve()
OUTPUT_DIR=(PROJECT_DIR/'outputs'/'web').resolve()
DATA_DIR.mkdir(parents=True,exist_ok=True)
OUTPUT_DIR.mkdir(parents=True,exist_ok=True)

STATICFILES_DIRS = [BASE_DIR / "static"]
