# Skills de QA mobile + desktop web con Herdr

Dos skills para planificar y ejecutar QA de una app mobile (simuladores iOS de Xcode y emuladores Android de Android Studio, con Maestro CLI + Maestro MCP) y de su versión web desktop (Playwright MCP). Un orquestador Claude reparte cada estrategia de test a un worker Claude independiente en su propio panel de Herdr, y cada worker maneja un único dispositivo.

Las dos son **solo manuales** (`disable-model-invocation: true`): Claude nunca las carga por su cuenta, solo corren cuando las llamás con `/writing-qa-test-plans` o `/executing-qa-test-plans`.

| Skill | Cuándo se usa |
|---|---|
| `writing-qa-test-plans/` | Para armar el plan de testeo. Recorre todas las estrategias del catálogo (smoke, aceptación, regresión, negativas, exploratorio, UI, accesibilidad, localización, interrupciones, red, instalación/upgrade, seguridad, performance, paridad entre plataformas, E2E entre sistemas) y deja cada una incluida, diferida o no aplicable, con su motivo. También define los carriles (un dispositivo por carril), las cuentas y los rangos de datos, el modelo de cada suite y las suites con escenarios concretos. |
| `executing-qa-test-plans/` | Para ejecutar ese plan: levantar los dispositivos, generar los paquetes, lanzar los workers en Herdr, aceptar cada suite, re-verificar los bugs con un worker independiente, consolidar el reporte y, si está aprobado, subir a ClickUp los bugs confirmados. También sirve para retomar una corrida. |

## Qué evalúa

Lo mismo que `qa-team-spacedev`, extendido a iOS, Android y API. Está en `executing-qa-test-plans/evaluation-standard.md`, que se agrega automáticamente al paquete de cada worker:

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
- Xcode con simuladores, y Android Studio con al menos un AVD (`emulator`, `adb`);
- Maestro CLI ≥ 2.11 y Java 17+. Los workers reciben el Maestro MCP (`maestro mcp`) por `--mcp-config`;
- bash. Los scripts funcionan con el bash 3.2 de macOS, y `render-results.py` con el Python del sistema (`/usr/bin/python3`, 3.9+);
- opcionales:
  - el Playwright MCP (`npx -y @playwright/mcp@latest`), si hay suites web;
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

6. Maestro CLI y Java:

   ```bash
   curl -fsSL "https://get.maestro.mobile.dev" | bash
   maestro --version                     # ≥ 2.11
   java -version                         # 17 o superior
   ```

   Para usar el Maestro MCP vos de forma interactiva:

   ```bash
   claude mcp add maestro --scope user -- maestro mcp
   ```

## Instalación

La guía completa, paso a paso, está en [`setup-herdr-qa.html`](setup-herdr-qa.html): Herdr, Claude Code, skills, Xcode, Android, Maestro, Playwright, vault y ClickUp opcionales, permisos y problemas comunes.

Para usarlas en todos los proyectos, enlazalas en tu carpeta personal de skills:

```bash
ln -s "$PWD/skills/writing-qa-test-plans" ~/.claude/skills/writing-qa-test-plans
ln -s "$PWD/skills/executing-qa-test-plans" ~/.claude/skills/executing-qa-test-plans
```

Para usarlas solo en un proyecto de QA, enlazalas en su `.claude/skills/`.

Los scripts `.sh` de `executing-qa-test-plans/scripts/` se ejecutan con `bash <script>` (funcionan con el bash 3.2 de macOS). `render-results.py` se ejecuta con `/usr/bin/python3` (el Python del sistema, 3.9+, solo librería estándar).

## Límites conocidos

- Maestro no soporta dispositivos iOS físicos: el testing iOS se hace en simuladores.
- El Maestro MCP usa puertos fijos por plataforma. Por eso corre como máximo un worker con MCP por plataforma a la vez, y los carriles extra de esa plataforma usan `maestro test` por CLI.
- El simulador de iOS no tiene throttling de red por línea de comandos.
- Las mediciones de performance en emulador son indicativas, no equivalen a las de un dispositivo real.
