# Flip PropUp

Web privada para detectar propiedades subvaluadas (fix-and-flip) en Córdoba: busca en los portales, guarda cada aviso con su historial de precios, permite seguir los que interesan y manda un resumen diario por email.

**Etapa 1 (esta versión):** Clasificados La Voz, búsquedas guardadas, seguimientos, notas, historial de precios, alertas por email y acceso con Google para usuarios habilitados.

## Cómo está armado

| Carpeta | Qué hay | Dónde corre |
| --- | --- | --- |
| `web/` | La web (Next.js): Buscar, Mis seguimientos, Búsquedas guardadas, ficha de cada aviso | Vercel |
| `scraper/` | El robot (Python + Playwright) que busca en La Voz y manda el email | GitHub Actions, todos los días a las 8:00 |
| `database/schema.sql` | Tablas y reglas de seguridad | Supabase |
| `.github/workflows/robot-diario.yml` | El horario del robot | GitHub |

## Puesta en marcha (una sola vez)

Hacé los pasos en orden. Ninguna clave se escribe en el código: todas van en la configuración de cada servicio.

### 1. Subir el código a GitHub

En Git Bash:

```bash
cd ~/Documents
git clone https://github.com/AhumadaCeleste/flippropup.git
cd flippropup
# copiá acá adentro el contenido del zip (las carpetas web, scraper, database, .github y este README)
git add .
git commit -m "Etapa 1: robot La Voz, base de datos y web"
git push
```

La primera vez, Git Bash puede abrir una ventana para que inicies sesión en GitHub.

### 2. Base de datos (Supabase)

1. En tu proyecto de Supabase entrá a **SQL Editor › New query**.
2. Pegá todo el contenido de `database/schema.sql` y tocá **Run**. Crea las tablas, carga los dos emails habilitados y activa la seguridad.
3. En **Project Settings › API** vas a necesitar tres datos: **Project URL**, la clave **anon public** y la clave **service_role**. La service_role es secreta: solo va en GitHub.

Para sumar a alguien más: **Table Editor › usuarios_habilitados › Insert row** con su email.

### 3. Ingreso con Google

1. En [Google Cloud Console](https://console.cloud.google.com) creá un proyecto llamado `Flip PropUp`.
2. **APIs y servicios › Pantalla de consentimiento de OAuth**: tipo **Externo**; nombre Flip PropUp; en **Usuarios de prueba** agregá los dos emails.
3. **Credenciales › Crear credenciales › ID de cliente de OAuth** › tipo **Aplicación web**. En **URI de redireccionamiento autorizados** poné:
   `https://TU-PROYECTO.supabase.co/auth/v1/callback` (tu Project URL + `/auth/v1/callback`).
4. Copiá el **ID de cliente** y el **Secreto**.
5. En Supabase: **Authentication › Sign In / Providers › Google** › activalo y pegá esos dos datos.

### 4. Publicar la web (Vercel)

1. En Vercel: **Add New › Project** › elegí el repositorio `flippropup`.
2. En **Root Directory** elegí `web`.
3. En **Environment Variables** cargá:
   - `NEXT_PUBLIC_SUPABASE_URL` = Project URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = clave anon public
4. Tocá **Deploy**. Vas a obtener una dirección como `https://flippropup.vercel.app`.
5. De vuelta en Supabase: **Authentication › URL Configuration** › **Site URL** = esa dirección, y en **Redirect URLs** agregá `https://flippropup.vercel.app/**`.

### 5. Robot y email diario (GitHub Actions)

1. En la cuenta **flippropup@gmail.com**: activá la verificación en dos pasos y creá una **contraseña de aplicación** en [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (16 letras).
2. En GitHub, en el repositorio: **Settings › Secrets and variables › Actions › New repository secret**. Cargá estos cinco:

| Nombre | Valor |
| --- | --- |
| `SUPABASE_URL` | Project URL de Supabase |
| `SUPABASE_SERVICE_KEY` | clave service_role de Supabase |
| `GMAIL_USUARIO` | `flippropup@gmail.com` |
| `GMAIL_CLAVE_APP` | la contraseña de aplicación (sin espacios) |
| `SITIO_URL` | la dirección de Vercel, por ejemplo `https://flippropup.vercel.app` |

3. Probalo: **Actions › Robot diario › Run workflow**. Tarda entre 2 y 5 minutos. Si sale en verde, en la web ya vas a ver los barrios en los desplegables.

### 6. Botón "Actualizar ahora" (opcional)

Permite correr el robot desde la web sin esperar a la mañana.

1. En GitHub: **tu foto › Settings › Developer settings › Personal access tokens › Fine-grained tokens › Generate new token**.
2. Solo para el repositorio `flippropup`, con el permiso **Actions: Read and write**.
3. En Vercel, sumá las variables `GITHUB_TOKEN` (el token) y `GITHUB_REPO` = `AhumadaCeleste/flippropup`, y volvé a publicar (**Deployments › Redeploy**).

## Uso diario

1. Entrá con Google.
2. En **Buscar** armá los filtros y tocá **Guardar búsqueda**. El robot la corre enseguida (si configuraste el paso 6) y después todos los días a las 8:00.
3. Tocá **☆ Seguir** en las que te interesan. En **Mis seguimientos** les ponés estado, precio objetivo y notas.
4. Cada mañana llega a los emails habilitados un resumen con avisos nuevos, bajas y subas de precio, avisos dados de baja y los que llegaron a tu precio objetivo. La primera corrida de cada búsqueda no manda "nuevos", para no llenarte el email.

## Si algo falla

- **El robot salió en rojo en Actions:** abrí la corrida y mirá el último paso; también queda registrado en la tabla `ejecuciones` de Supabase. Si La Voz cambió su sitio, pasame el error y lo ajustamos.
- **No llega el email:** revisá `GMAIL_CLAVE_APP` y la carpeta de spam. Si ese día no hubo novedades, no se envía nada.
- **"No tenés acceso" al entrar:** el email no está en `usuarios_habilitados`.

## Probar la web en tu computadora (opcional)

Necesitás [Node.js](https://nodejs.org) 20 o más nuevo.

```bash
cd web
cp .env.example .env.local   # y completá los valores
npm install
npm run dev                  # abre http://localhost:3000
```

Para que el login funcione en tu computadora, sumá `http://localhost:3000/**` en las Redirect URLs de Supabase.

## Próximas etapas

- Etapa 3: Argenprop y Zonaprop (por emails de alerta y agregar por link), detección de duplicados entre portales.
- Etapa 4: precio por m² contra el promedio del barrio, puntaje de oportunidad, calculadora de compra + refacción + venta y mapa.
