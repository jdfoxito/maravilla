# VisorDG — Runbook de puesta en marcha en el servidor nuevo

**Servidor:** Windows 11 · IP 10.2.0.17 · Python 3.14 en `E:\py` · PostgreSQL 18 · nginx en `C:\nginx`
**Proyecto:** `E:\sri\soluciones\DG\VisorDG` · Wheels offline: `E:\sri\soluciones\DG\offline`

Todos los comandos se ejecutan en **CMD como administrador**, salvo los que dicen *PowerShell*.

---

## 0. Qué está pasando (resumen)

| # | Síntoma | Causa | Se arregla en |
|---|---|---|---|
| 1 | *refused* hacia `127.0.0.1:4443` en `error.log` | El bloque **443** de nginx manda a Flask, que no existe en este servidor | §2 |
| 2 | 404/500 al abrir el visor (aunque nginx responda) | `root` de nginx apunta a **D:**, el proyecto está en **E:** | §2 |
| 3 | Respuestas incoherentes tras editar nginx | **4 procesos nginx** escuchando el 9000 (instancias viejas) | §2 |
| 4 | `ERR_CONNECTION_TIMED_OUT` desde otra PC/red | Firewall de Windows, firewall/ACL de red o proxy del navegador | §5 |
| 5 | `pdm run ...` → `No module named 'asyncpg'` | PDM apunta a un `.venv` vacío (sin pip) o a `__pypackages__` vacío | §4 |
| 6 | `pdm run refrescar` o el refresco de las 23:00 fallan | `psql` no está en el PATH (lo usa `correr_sql`) | §3.3 |

> **Refused ≠ timeout.** *Refused* = el paquete llegó y no había nadie escuchando (configuración). *Timeout* = el paquete se perdió en el camino (firewall, red o proxy). Arreglar nginx **no** arregla el timeout.

---

## 1. Orden recomendado (checklist)

- [ ] Correr `diagnostico_visordg.cmd` y guardar el `.txt` (foto del "antes")
- [ ] §2 nginx: matar todos los procesos, corregir rutas y 443, `nginx -t`, arrancar uno solo
- [ ] §3 FastAPI arriba en 8000 + `psql` en el PATH + `settings.toml` sin rutas a D:
- [ ] §3.4 Revisar que el frontend no apunte a la IP del servidor viejo
- [ ] Pruebas locales: 8000, 9000 y 443 → todas **200**
- [ ] §5 Firewall de Windows abierto → probar desde una PC de la **misma** red
- [ ] §5.4 Si falla desde **otra** red → pedido a Infraestructura
- [ ] §4 PDM reparado (opcional: todo funciona también sin PDM)
- [ ] §7 Arranque automático de nginx y API
- [ ] §8 Seguridad pendiente

---

## 2. nginx

### 2.1 Dejar una sola instancia
```cmd
cd /d C:\nginx
taskkill /f /im nginx.exe
tasklist /fi "imagename eq nginx.exe"
```
`tasklist` debe responder "No hay tareas". Si alguno sobrevive, usa `taskkill /f /pid <PID>`.

### 2.2 Corregir la configuración
```cmd
copy conf\nginx.conf conf\nginx.conf.bak_%date:~-4%%date:~3,2%%date:~0,2%
if not exist C:\nginx\temp mkdir C:\nginx\temp
```
- Reemplazar `conf\nginx.conf` por el corregido, o como mínimo:
  - Cambiar todos los `D:/sri/...` por `E:/sri/...`.
  - En el bloque 443: quitar `upstream flask_backend` y sus `location`, y poner los mismos `location /`, `location ~* \.(css|js)$` y `location /api/` del bloque 9000.
- Comprobar que existen `C:\nginx\cert\cadena.crt` y `cadenaprivada.key` (si no, el 443 no arranca).
- Comprobar que existen `C:\nginx\html\gadyrErr.html` y `gadyrErr500.html`.

### 2.3 Validar y arrancar
```cmd
nginx.exe -t
start "" nginx.exe
netstat -ano | findstr LISTENING | findstr ":443 :9000 :8000"
```
- Si `-t` da error en `http2 on;`, tu versión de nginx es anterior a la 1.25. Borra esa línea y usa `listen 443 ssl http2;`.
- Para recargar después de editar: `nginx -s reload`. Si se vuelve a desordenar: `taskkill /f /im nginx.exe` + `start "" nginx.exe`.

### 2.4 Logs útiles (PowerShell)
```powershell
Get-Content C:\nginx\logs\visor_error.log -Tail 30 -Wait
Get-Content C:\nginx\logs\error.log -Tail 30
```

---

## 3. FastAPI / Python

### 3.1 Arrancar la API sin depender de PDM
```cmd
cd /d E:\sri\soluciones\DG\VisorDG\app\backend
E:\py\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```
(Si ya reparaste PDM según §4, usa `.venv\Scripts\python.exe` en vez de `E:\py\python.exe`.)

### 3.2 Pruebas locales
```cmd
curl.exe http://127.0.0.1:8000/api/v1/health
curl.exe -o nul -w "%{http_code}\n" http://127.0.0.1:9000/
curl.exe http://127.0.0.1:9000/api/v1/health
curl.exe -k https://127.0.0.1/api/v1/health
curl.exe -o nul -w "%{http_code}\n" http://10.2.0.17:9000/
```

| Resultado | Diagnóstico |
|---|---|
| Todas OK | Servidor listo; lo que quede es red (§5) |
| Solo falla `10.2.0.17` | IP distinta (`ipconfig`) o firewall local |
| 8000 OK, 9000 falla | nginx (rutas, instancia vieja) → `visor_error.log` |
| 8000 falla | API apagada o error al arrancar (ver consola de uvicorn) |
| 502 en `/api/` | nginx sí funciona; la API está caída |

### 3.3 `psql` en el PATH (lo necesitan `refrescar` y el demonio de las 23:00)
*PowerShell (admin):*
```powershell
$p = [Environment]::GetEnvironmentVariable('Path','Machine')
if ($p -notlike '*PostgreSQL\18\bin*') {
  [Environment]::SetEnvironmentVariable('Path', "$p;C:\Program Files\PostgreSQL\18\bin", 'Machine')
}
```
Después hay que cerrar y abrir la consola. Para comprobar: `where psql`.
> No uses `setx /M PATH` porque trunca el PATH a 1024 caracteres.

### 3.4 Configuración y frontend
```cmd
findstr /n /i "D:\\ D:/ softapps" E:\sri\soluciones\DG\VisorDG\config\settings.toml
findstr /s /n /i "10.21 4443 http://" E:\sri\soluciones\DG\VisorDG\app\frontend\dist\js\pro\*.js
```
- En `settings.toml`: las rutas de `[fuentes].local`, `[fuentes].fileserver` y `[database]` deben ser las de **este** servidor.
- En `config.js`: si el endpoint de la API está escrito con la IP vieja (10.21.178.245), el visor cargaría pero los datos darían timeout. Debe ser **relativo** (`/api/v1/...`).

### 3.5 Librerías instaladas
```cmd
E:\py\python.exe -c "import fastapi, uvicorn, asyncpg, pandas, jwt, pwdlib, openpyxl, xlrd; print('OK')"
```

---

## 4. Arreglar PDM (offline)

**Qué pasó:**
1. `pdm.exe` vino de otra máquina y apuntaba a `D:\softapps\py\python.exe` (*Fatal error in launcher*).
2. `pdm install` creó un `.venv` **sin pip** e intentó bajar paquetes de internet (bloqueado).
3. `pdm use E:\py\python.exe` con `use_venv false` activó `__pypackages__`, que está vacío.

**Solución:** crear un venv propio con pip, llenarlo con las wheels offline y apuntar PDM a él. **No volver a correr `pdm install` ni `pdm sync`**: el lockfile incluye `oracledb` y las dependencias de desarrollo, que no están en las wheels, y PDM intentará ir a internet.

### 4.1 Si `pdm` da "Fatal error in launcher"
Reinstalar PDM con el Python correcto (las wheels de PDM las descargaste en `offline\pdm`):
```cmd
E:\py\python.exe -m pip install --no-index --find-links=E:\sri\soluciones\DG\offline\pdm --force-reinstall pdm
```
Mientras tanto, siempre funciona: `E:\py\python.exe -m pdm <comando>`.

### 4.2 Reconstruir el entorno del proyecto
```cmd
cd /d E:\sri\soluciones\DG\VisorDG\app\backend
taskkill /f /im python.exe            :: solo si la API corre desde .venv
rmdir /s /q .venv
rmdir /s /q __pypackages__
del .pdm-python

E:\py\python.exe -m venv .venv
.venv\Scripts\python.exe -m pip --version
.venv\Scripts\python.exe -m pip install --no-index --find-links=E:\sri\soluciones\DG\offline -r requirimientos.txt
.venv\Scripts\python.exe -c "import fastapi, uvicorn, asyncpg, pandas, jwt, pwdlib; print('OK')"
```
> Revisa el nombre del archivo: en la máquina de descarga se llamó `requirimientos.txt` y en otros pasos `requirements.txt`. Usa el que realmente exista.
> `python -m venv` usa `ensurepip`, que funciona sin internet, así que este venv **sí** trae pip.

### 4.3 Apuntar PDM al venv y quitarle internet
```cmd
pdm config python.use_venv true
pdm config check_update false
pdm use -f .venv\Scripts\python.exe
pdm info
pdm run python -c "import asyncpg; print('pdm OK')"
```
`pdm info` debe mostrar el intérprete de `...\backend\.venv\Scripts\python.exe`.

### 4.4 Comandos de uso diario (ya con PDM)
```cmd
pdm run start
pdm run cargar todo --origen local
pdm run cargar solo ventas --origen local
pdm run refrescar
pdm run verificar --origen local
```
Si PDM vuelve a fallar, cada script equivale a esto:
`.venv\Scripts\python.exe cargas.py <comando>` · `.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000`

### 4.5 Para la próxima instalación offline
En la máquina **con** internet:
```cmd
python3.14 -m pip download --only-binary=:all: -r requirements.txt -d offline
python3.14 -m pip download pdm -d offline\pdm
```
Ten en cuenta que `oracledb` y el grupo `dev` (pylint, pytest, httpx) solo hacen falta si los vas a usar. Si quieres que `pdm sync` funcione offline algún día, descarga también esos paquetes.

---

## 5. Red, firewall y proxy (el timeout)

### 5.1 En el servidor: reglas de entrada
```cmd
netsh advfirewall firewall add rule name="VisorDG 9000" dir=in action=allow protocol=TCP localport=9000 profile=any
netsh advfirewall firewall add rule name="VisorDG 443"  dir=in action=allow protocol=TCP localport=443  profile=any
netsh advfirewall show allprofiles state
```
*PowerShell (admin):*
```powershell
Get-NetConnectionProfile
# Quitar bloqueos que Windows crea si se cerró el aviso "Permitir acceso" de nginx
Get-NetFirewallApplicationFilter | ? Program -match 'nginx' | Get-NetFirewallRule | ? Action -eq Block | Remove-NetFirewallRule
# Ver reglas que tocan 443/9000
Get-NetFirewallPortFilter | ? { $_.LocalPort -in '443','9000' } | Get-NetFirewallRule | ft DisplayName,Enabled,Action,Profile
```
- Si la red aparece como **Public**, puedes cambiarla a privada con `Set-NetConnectionProfile -InterfaceAlias "<nombre>" -NetworkCategory Private`. Si el equipo está en dominio, eso lo controla la GPO.
- Prueba rápida, **solo para diagnosticar**: apagar el firewall unos minutos con `netsh advfirewall set allprofiles state off` y probar desde fuera. **Volver a encenderlo** con `... state on`. Si con el firewall apagado funciona, el bloqueo es de Windows; si no, es de la red.

### 5.2 Desde la PC cliente (PowerShell)
```powershell
ping 10.2.0.17
Test-NetConnection 10.2.0.17 -Port 9000
Test-NetConnection 10.2.0.17 -Port 443
tracert -d 10.2.0.17
curl.exe --noproxy "*" -o NUL -w "%{http_code}`n" http://10.2.0.17:9000/
```

| Resultado | Causa | Acción |
|---|---|---|
| `curl --noproxy` OK, navegador falla | Proxy institucional | Agregar `10.*` en las excepciones del proxy (Configuración → Red → Proxy) o pedirlo a soporte/GPO |
| Ping OK, `TcpTestSucceeded: False` | Firewall bloquea el puerto | §5.1; si persiste, firewall de red |
| Ping falla y `tracert` se corta | Sin ruta o ACL entre redes | Infraestructura (§5.4) |
| Funciona en la misma red, no en otra | ACL o firewall entre VLANs | Infraestructura (§5.4) |

> El ping puede estar bloqueado por política. Que no responda no prueba nada por sí solo; lo que manda es `Test-NetConnection -Port`.

### 5.3 Ver si llegan paquetes al servidor
Si el cliente da timeout y en `visor_access.log` **no aparece** su IP, el tráfico no está llegando a nginx: es firewall o red, no la aplicación.
```powershell
Get-Content C:\nginx\logs\visor_access.log -Tail 20 -Wait
```

### 5.4 Pedido a Infraestructura (texto sugerido)
> Solicito habilitar tráfico **TCP entrante hacia 10.2.0.17, puertos 443 y 9000**, desde las redes/VLAN `<IP o segmento de los equipos y TV de la DG>`. Servicio: VisorDG — Visor Gerencial de la Dirección General (nginx + FastAPI). Además, excluir `10.2.0.17` del proxy web institucional para los equipos de la DG.

---

## 6. Base de datos (verificación tras la exportación)
```cmd
cd /d "C:\Program Files\PostgreSQL\18\bin"
psql -U postgres -d detalles -c "SELECT schemaname, relname, n_live_tup FROM pg_stat_user_tables WHERE schemaname IN ('visordg','seg') ORDER BY 1,2;"
psql -U postgres -d detalles -c "SELECT fuente, fecha_corte FROM visordg.v_fecha_corte;"
psql -U postgres -d detalles -c "SELECT username, activo FROM seg.usuarios;"
```
- Compara los conteos con el servidor viejo (la misma consulta en ambos).
- `n_live_tup` es aproximado. Para cifras exactas: `pdm run verificar --origen local` (compara archivo contra base, mes a mes) y `pdm run auditar`.
- Si alguna cifra no cuadra: `pdm run cargar todo --origen local`, porque cada carga reemplaza los datos y no duplica.

---

## 7. Arranque automático al reiniciar el servidor

### 7.1 Scripts de arranque
`E:\sri\soluciones\DG\VisorDG\iniciar_api.cmd`
```cmd
@echo off
cd /d E:\sri\soluciones\DG\VisorDG\app\backend
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 >> E:\sri\soluciones\DG\VisorDG\api.log 2>&1
```
`C:\nginx\iniciar_nginx.cmd`
```cmd
@echo off
cd /d C:\nginx
taskkill /f /im nginx.exe >nul 2>&1
start "" nginx.exe
```

### 7.2 Tareas programadas
```cmd
schtasks /create /tn "VisorDG\nginx" /tr "C:\nginx\iniciar_nginx.cmd" /sc onstart /ru SYSTEM /rl highest /f
schtasks /create /tn "VisorDG\API"   /tr "E:\sri\soluciones\DG\VisorDG\iniciar_api.cmd" /sc onstart /ru "DOMINIO\usuario_servicio" /rp * /rl highest /f
schtasks /run /tn "VisorDG\API"
```
- La API debe correr con un **usuario de dominio** que tenga permisos sobre el fileserver. Con `SYSTEM`, el origen `fileserver` (ruta UNC) suele fallar, y con eso fallaría la recarga Shift+Alt+R.
- En la configuración de la tarea, desmarca "Detener si se ejecuta más de 3 días".

### 7.3 Que el servidor no se duerma
```cmd
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
```

---

## 8. Seguridad pendiente (del LEEME §9)
- [ ] Rotar la clave de `postgres` y actualizarla en `settings.toml`.
- [ ] Generar un `jwt_secret` nuevo con `E:\py\python.exe -c "import secrets; print(secrets.token_hex(32))"`.
- [ ] Confirmar que `admin` ya no usa la clave inicial.
- [ ] Limitar los permisos NTFS de `config\settings.toml` al usuario del servicio y a los administradores.
- [ ] Con todo funcionando por 443, considerar cerrar el 9000 hacia afuera (dejarlo solo local).

---

## 9. Tabla rápida de síntomas

| Veo… | Primero reviso… |
|---|---|
| `ERR_CONNECTION_TIMED_OUT` | §5 (firewall, proxy, red) |
| `ERR_CONNECTION_REFUSED` | ¿nginx corre? `netstat` del puerto (§2.3) |
| 502 Bad Gateway | API caída en 8000 (§3.1) |
| 404 o página en blanco | `root` de nginx a E: (§2.2) |
| Visor carga sin datos | `config.js` con IP vieja (§3.4); `/api/v1/tv-data` en el navegador |
| No se actualiza solo tras recargar | WebSocket: `visor_error.log` y la cabecera `Upgrade` en `location /api/` |
| Error de certificado en https | Normal con certificado interno; instalar la CA del SRI en los TV |
| `No module named ...` | §4 (entorno de PDM) o usar `E:\py\python.exe` |
| `psql no está en el PATH` | §3.3 |
| `no existe la relación ...` | La base no se migró completa: §6 o DDL del LEEME §3 caso 4 |
