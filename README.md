# Skills de QA mobile + desktop web con Herdr

Dos skills para planificar y ejecutar QA de una app mobile (simuladores iOS de Xcode y emuladores Android de Android Studio) y de su versión web (Chrome). Un orquestador Claude reparte cada estrategia de test a un worker Claude independiente en su propio panel de Herdr, y cada worker maneja un único dispositivo con el driver de su carril:

| Plataforma | Driver por defecto | Instala algo | Alternativa (solo con tu OK) |
|---|---|---|---|
| Android | `adb` directo (tap 41 ms, captura 190 ms, árbol 0,5 s) | no | `maestro-mcp` para tipear unicode/emoji o correr flows Maestro existentes |
| iOS | `maestro-mcp` si Maestro ya está instalado (un carril por plataforma) | no, si ya está | `axe` (brew, sin Java, sin límite de carriles) o instalar Maestro |
| Web | `chrome`: el Chrome nativo de Claude Code (`--chrome`), tu propio perfil, un carril a la vez | no | `playwright-mcp` (npx) para carriles web en paralelo o el viewport mobile 375×667 |
| API | `curl` | no | – |

**Ninguna skill instala nada sin preguntarte.** Maestro, AXe, Playwright MCP o Java aparecen en el plan como decisión `to confirm`; si decís que no, los carriles que lo necesitaban quedan bloqueados y el resto corre igual.

Las dos son **solo manuales** (`disable-model-invocation: true`): Claude nunca las carga por su cuenta, solo corren cuando las llamás con `/writing-qa-test-plans` o `/executing-qa-test-plans`.

| Skill | Cuándo se usa |
|---|---|
| `writing-qa-test-plans/` | Para armar el plan de testeo. Recorre todas las estrategias del catálogo (smoke, aceptación, regresión, negativas, exploratorio, UI, accesibilidad, localización, interrupciones, red, instalación/upgrade, seguridad, performance, paridad entre plataformas, E2E entre sistemas) y deja cada una incluida, diferida o no aplicable, con su motivo. También define los carriles (un dispositivo por carril), las cuentas y los rangos de datos, el modelo de cada suite y las suites con escenarios concretos. |
| `executing-qa-test-plans/` | Para ejecutar ese plan: levantar los dispositivos, generar los paquetes, lanzar los workers en Herdr, aceptar cada suite (chequeo mecánico con `check-report.py` más las capturas de los FAIL), re-verificar los bugs con un worker independiente por carril, consolidar el reporte y, si está aprobado, subir a ClickUp los bugs confirmados. También sirve para retomar una corrida. |

Las dos skills arrancan con **dos preguntas, siempre, antes de cualquier chequeo**: qué plataformas se testean (iOS, Android, web, API o todas) y qué tipos de usuario tiene la app (admin, usuario final, otros roles). Los roles se buscan primero en el vault, en `context/navigation-map.md` y en `.env.example`; solo se pregunta lo que no aparece ahí.

## Qué evalúa

Lo mismo que `qa-team-spacedev`, extendido a iOS, Android y API. Está en `executing-qa-test-plans/evaluation-standard.md`. Cada worker recibe las secciones comunes (evidencia, severidad, puntaje, consola una vez por suite, acciones prohibidas, template del reporte) más las que su estrategia posee: error guessing en `negative-validation`, accesibilidad en `accessibility`, visual en `ui-visual`, textos en `text-quality`, etc. (tabla al inicio del archivo). Así un smoke hace un smoke, y los chequeos transversales los hace la suite de cada plataforma que los posee. Si una plataforma no tiene suite para un chequeo, `make-package.sh` lo mete en la suite portadora de esa plataforma como red de seguridad, y lo imprime al generar el paquete. Todo worker reporta igual lo que ve en el árbol o la captura que ya tiene (un botón sin label, una key de i18n, un typo, un crash), sin auditar.

Lo que el estándar define:

- **Evidencia:** sin captura no hay afirmación; cada escenario termina en PASS, FAIL o BLOCKED (BLOCKED nunca cuenta como defecto); los falsos positivos se corrigen por escrito y no se borran; se respetan los comportamientos conocidos que no son bugs.
- **Puntaje de calidad 0–100** en 6 dimensiones: funcional 30%, validaciones 20%, navegación 15%, visual 15%, accesibilidad 10%, consola y logs 10%. PASS desde 85, CONDITIONAL PASS de 60 a 84, FAIL por debajo de 60. Hay uno por suite y uno para toda la corrida.
- **Severidad** alta, media o baja, con criterios definidos, y acciones Must Fix / Should Fix / Nice to Have.
- **Casos de error típicos:** clases de equivalencia, valores límite, doble envío, back o refresh a mitad de flujo, emoji, inyección, textos largos, uploads, fechas y paginación.
- **Los 12 escenarios estándar de autenticación** (AUTH-01…12) en todo flujo de login, registro o recuperación de contraseña.
- **Accesibilidad** (web y mobile), **salud de consola y logs** (consola del browser, crashes y ANRs en mobile), **revisión visual y de UX**, y **calidad de textos**: typos, gramática, idioma mezclado, keys de i18n, placeholders.
- **Descubrimiento de la plataforma:** drift contra `navigation-map.md`, sin editarlo nunca.
- **Organizaciones y roles:** aislamiento de datos entre organizaciones; los permisos se prueban con cada rol.
- **API:** versión y cuenta como datos de entrada, credenciales que nunca se imprimen, autorización entre organizaciones, y los fallos que dependen de qué cuenta llama quedan retenidos hasta confirmar de quién es la key.
- **Fallas conocidas según el registro:** ticket abierto = conocida; cerrado "as designed" = comportamiento esperado; cerrado por otro motivo = posible regresión.
- **Regresión:** datos de prueba vencidos marcados aparte, aviso de flujos que no corren hace más de 30 días y oferta de sumar flujos al set de regresión.

## Cómo se mantiene corta la corrida

- **La verificación no frena el carril.** Una suite queda `accepted (pending verification)` apenas pasa el chequeo mecánico y el orquestador vio las capturas de los FAIL; el carril arranca la siguiente suite en ese momento. Un único verify worker por carril re-reproduce los bugs High y Medium acumulados cuando el carril termina su cola, cuando junta 8 hallazgos, o de inmediato si un smoke falla en un flujo crítico. CONFIRMED a la primera reproducción; los 3 intentos solo cuando la primera no reproduce.
- **La aceptación es mecánica donde puede serlo.** `scripts/check-report.py` valida el template del reporte, la aritmética del puntaje, la cobertura de escenarios contra el plan y la existencia de cada archivo de evidencia en milisegundos; el orquestador solo abre las imágenes de FAIL, y en paralelo con subagentes cuando varias suites terminan juntas.
- **Más carriles por default.** Dos carriles Android con `adb` desde 16 GB de RAM (segundo AVD o el mismo con `--read-only`, sin instalar nada), segundo carril iOS si AXe ya está instalado, y el carril de API siempre propio, arrancando en la primera ola.

## Cómo interactúan rápido con el dispositivo

El cuello de botella no es el emulador sino la cantidad de turnos del modelo y los bytes que vuelven en cada uno. `executing-qa-test-plans/driver-protocol.md` se agrega a cada paquete con las reglas y las latencias medidas (2026-10-15, M2 Pro 16 GB):

- mirar el árbol una vez por pantalla y actuar por texto/id/bounds, nunca adivinar coordenadas desde una captura;
- una sola llamada por paso del escenario (flow Maestro de varios comandos, `axe batch`, un Bash con varias líneas de `adb`, `browser_batch` en Chrome);
- verificar por texto (`assertVisible` ≈ 150 ms, `grep` sobre el dump) y guardar capturas directo a archivo; la imagen inline (160–250 KB) solo cuando el chequeo es visual;
- nunca `maestro test` ni `maestro hierarchy` por paso (9–22 s cada invocación); el CLI solo corre archivos de flows enteros;
- animaciones apagadas en Android (`uiautomator dump` baja de 2,1 s a 0,5 s).

## Fuentes opcionales

- **Vault (Obsidian u otro MCP):** si está conectado y tiene notas del proyecto, el plan las cita y el orquestador copia los extractos en los paquetes. Si no hay vault, o el MCP no conecta, el plan dice `Vault: none (motivo)` y sigue igual. Los archivos del vault nunca se leen desde el disco.
- **ClickUp:** cumple dos roles independientes, y los dos son opcionales.
  - **Fuente:** los tickets aportan los criterios de aceptación. Se leen frescos en cada corrida.
  - **Destino:** ahí van los bugs confirmados. Solo se escribe ahí con la decisión aprobada, nunca durante la planificación.

  Si no indicás un ClickUp (ni en el plan ni cuando la skill pregunta, una sola vez), la corrida **no toca ClickUp en ningún momento**, aunque el MCP esté conectado, y el resultado es **solo la página HTML**. También se genera el HTML si ClickUp estaba previsto pero se desconectó o no se aprobó el destino. El cierre genera una página HTML con los resultados: `evidence/<app>/QA-RUN-RESULTS-<run-id>.html`. Tiene el resumen, el go / no-go, los resultados por suite, los bugs con su verificación y sus capturas, los falsos positivos y las brechas de cobertura. Se abre sin conexión. Para compartirla hay que mandar toda la carpeta `evidence/<app>/` (las capturas van enlazadas). Los bugs también quedan en el Bug Register de cada `qa-report.md`, listos para `/report-bugs-to-clickup`.
- **Sin vault ni ClickUp:** los requisitos salen de lo que describe el usuario, de `context/` y `maestro/flows/` (si existen) o de una suite exploratoria de descubrimiento.

## Requisitos

- Herdr, con la integración de Claude (`herdr integration install claude`), y el orquestador corriendo dentro de un panel (`HERDR_ENV=1`);
- Claude Code;
- los skills `herdr` y `herdr-agent-orchestration`;
- el plugin Superpowers (`verification-before-completion`);
- Xcode con simuladores, y Android Studio con al menos un AVD (`emulator`, `adb`). Con eso alcanza para los carriles Android (`adb`);
- para iOS, uno de los dos: Maestro CLI ≥ 2.11 con Java 17+ (los workers reciben el Maestro MCP por `--mcp-config`), o AXe (`brew install cameroncooke/axe/axe`). Ninguno se instala sin tu OK;
- para web, Google Chrome abierto con la extensión "Claude in Chrome" (≥ 1.0.36) conectada a tu organización de claude.ai y una sesión `/login` con plan directo de Anthropic. Los workers arrancan con `--chrome`;
- bash. Los scripts funcionan con el bash 3.2 de macOS, y `render-results.py` con el Python del sistema (`/usr/bin/python3`, 3.9+);
- opcionales:
  - el Playwright MCP fijado en `@playwright/mcp@0.0.83` (nunca `@latest`: los workers lo corren con Bash), solo si aprobás esa decisión: carriles web en paralelo, viewport mobile 375×667, headless o perfil aislado. Un Playwright MCP que ya tengas registrado en tu Claude (`claude mcp list`) no cuenta como instalado: los workers solo ven la config de la corrida con la versión fijada, y el preflight verifica que el plan no nombre otra;
  - un MCP de vault (Obsidian u otro), si el proyecto tiene vault;
  - el MCP de ClickUp, si los tickets son fuente de requisitos o si se suben ahí los bugs confirmados;
  - las skills de `qa-team-spacedev` (`qa-evidence-discipline`, `report-bugs-to-clickup`, `qa-report-test-execution`). Si están, se reutilizan; si no, el plan copia sus reglas.

### Setup

1. Herdr y Claude Code instalados. Verificá con `herdr --version` y `claude --version`.
2. Integración de Herdr con Claude Code:

   ```bash
   herdr integration install claude
   herdr integration status      # debe mostrar: claude: current
   ```

3. Skills de Herdr:

   ```bash
   npx skills add herdrdev/herdr --skill herdr -g
   npx skills add aerain/herdr-agent-orchestration -g -s herdr-agent-orchestration -a claude-code
   ```

4. Superpowers, dentro de Claude Code:

   ```
   /plugin install superpowers@claude-plugins-official
   ```

5. Simuladores y emuladores. Verificá que haya al menos un dispositivo por plataforma:

   ```bash
   xcrun simctl list devices available   # simuladores iOS (Xcode)
   emulator -list-avds                   # AVDs de Android Studio
   adb version
   ```

6. Driver iOS, solo si hay carriles iOS (Android corre con `adb` sin nada más). Una de las dos opciones; la skill te lo pregunta y no instala por su cuenta:

   ```bash
   # Maestro CLI + Java: versión fijada, y sin pasar el script por un pipe (leelo antes de correrlo)
   curl -fsSL "https://get.maestro.mobile.dev" -o /tmp/maestro-install.sh
   MAESTRO_VERSION=2.11.0 bash /tmp/maestro-install.sh
   maestro --version                     # 2.11.0
   java -version                         # 17 o superior
   # o AXe (binario único, sin Java)
   brew install cameroncooke/axe/axe
   axe list-simulators
   ```

   Para usar el Maestro MCP vos de forma interactiva:

   ```bash
   claude mcp add maestro --scope user -- maestro mcp
   ```

7. Web con el Chrome nativo de Claude Code: instalá la extensión "Claude in Chrome" desde la Chrome Web Store, iniciá sesión en la misma organización de claude.ai que tu `claude` (`/login`), dejá Chrome abierto y permití en la extensión los dominios que vas a testear. Verificá con `claude --chrome` y `/chrome` en una sesión tuya. Playwright MCP no hace falta salvo que lo apruebes en el plan. **Ojo:** este carril actúa dentro de tu Chrome real, con tus sesiones iniciadas. Usalo solo contra sitios propios de staging o dev, idealmente desde un perfil de Chrome dedicado donde no haya nada más abierto y la extensión solo permita los dominios de QA. Para cualquier otro sitio, usá el carril de Playwright (perfil aislado).

## Instalación

La guía completa, paso a paso, está en [`setup-herdr-qa.html`](setup-herdr-qa.html): Herdr, Claude Code, skills, Xcode, Android, Maestro, Playwright, vault y ClickUp opcionales, permisos y problemas comunes.

Para usarlas en todos los proyectos, enlazalas en tu carpeta personal de skills:

```bash
ln -s "$PWD/skills/writing-qa-test-plans" ~/.claude/skills/writing-qa-test-plans
ln -s "$PWD/skills/executing-qa-test-plans" ~/.claude/skills/executing-qa-test-plans
```

Para usarlas solo en un proyecto de QA, enlazalas en su `.claude/skills/`.

Los scripts `.sh` de `executing-qa-test-plans/scripts/` se ejecutan con `bash <script>` (funcionan con el bash 3.2 de macOS). `render-results.py` y `check-report.py` se ejecutan con `/usr/bin/python3` (el Python del sistema, 3.9+, solo librería estándar; `check-report.py` importa el parser de `render-results.py`, así que van juntos).

## Seguridad

- **Contenido no confiable:** el texto de tickets, extractos del vault, pantallas de la app o del sitio, respuestas de API y logs es dato, nunca instrucción (`evaluation-standard.md` § 0, y una línea en cada paquete). Un intento de inyección se reporta como hallazgo, no se obedece.
- **Credenciales:** además de la regla escrita, los workers arrancan con `--disallowedTools` (`devices-and-tools.md` § Secret deny rules): bloquea leer `.env*` y volcar el entorno aun en modo `auto`. Es una defensa adicional, no un sandbox.
- **Versiones fijas:** Maestro 2.11.0 y `@playwright/mcp@0.0.83`. Para subirlas hay que leer las notas de la versión nueva y cambiar los lugares que la nombran.
- **Carril `chrome`:** es el de mayor exposición porque usa tu perfil real (ver el paso 7 del setup).

## Límites conocidos

- Maestro y AXe no soportan dispositivos iOS físicos: el testing iOS se hace en simuladores.
- El Maestro MCP usa puertos fijos por plataforma. Por eso corre como máximo un worker con MCP por plataforma a la vez; los carriles Android extra usan `adb`, y los iOS extra usan AXe (con tu OK) o `maestro test` solo sobre flows existentes.
- El Chrome nativo comparte un solo grupo de pestañas entre todas las sesiones de Claude Code y usa tu perfil: un carril web a la vez, y lo que el worker abra lo ves vos. No emula viewports mobile.
- `adb shell input text` no tipea acentos ni emoji: esos escenarios van a un carril `maestro-mcp` o quedan `N/A (driver)`.
- El simulador de iOS no tiene throttling de red por línea de comandos.
- Las mediciones de performance en emulador son indicativas, no equivalen a las de un dispositivo real.
