# Interfaz local Django (Práctica 07)

**Se conserva la arquitectura aprobada en la Práctica 06: Django + SQLite + Bootstrap como diseño visual.** Esta primera implementación usa CSS local simple y deja los mockups Bootstrap como referencia para la integración posterior; NO afirma que las ocho interfaces finales estén desarrolladas.

## Arranque en Windows (PowerShell)

Desde `implementacion/`:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-web.txt
$env:DJANGO_SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(50))"
python web_local/manage.py migrate
python web_local/manage.py createsuperuser
python web_local/manage.py seed_demo
python web_local/manage.py runserver 127.0.0.1:8000
```

Abrir http://127.0.0.1:8000/login/. Acceder con el administrador creado; crear otro usuario sin `is_staff` desde `/admin/` para comprobar rol Investigador. El comando `seed_demo` crea dos registros del catálogo **etiquetados DEMO** para permitir registrar un experimento y pulsar «Ejecutar DEMO sintética» sin archivos reales. Para datos CSI reales, el administrador deberá reemplazar esos registros por datos auditados. **Eso no descarga CSI real.** Ejecutar `python web_local/manage.py test portal` para comprobar 5 casos de acceso (requiere Django instalado).

## Seguridad aplicada / límites
- 3 niveles: anónimo (solo login), investigador (operaciones propias), administrador (`is_staff` y permisos de Django admin).
- Django hash de contraseñas, POST+CSRF, sesión HttpOnly/SameSite, caducidad 30 min, cabeceras defensivas, host limitado a localhost, rate limiting básico por IP y usuario en caché local.
- Las rutas de datos son metadatos y no se exponen como enlaces a archivos del servidor. No está habilitada una subida HTTP de ficheros grandes o arbitrarios.
- La prueba sintética no lee datos CSI reales. El botón de demostración genera un pequeño dataset artificial y resultados etiquetados **SINTÉTICO**.
- No exponer este servidor de desarrollo a Internet. Para despliegue remoto, implementar HTTPS, endurecimiento de cookies, servidor WSGI y monitoreo.
- No se guarda una contraseña ni `SECRET_KEY` en el ZIP; generar una variable nueva para cada instancia. Los datasets completos deben permanecer fuera de Git.

**Limitación de verificación:** el entorno usado para confeccionar la entrega no pudo instalar Django (sin acceso al índice de paquetes). Las pruebas del núcleo Python sí pudieron ejecutarse. Ejecutar los tests web en Windows tras instalar los requisitos. La navegación Django se entrega como primera integración, no como producto de seguridad auditada en producción.
