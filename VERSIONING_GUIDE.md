# IoTDevSim - Guía de Control de Versiones

> 📚 **Versión:** 1.0.0  
> 🎯 **Objetivo:** Establecer buenas prácticas para el versionado semántico, releases automatizadas y flujo de trabajo Git.

---

## 📋 Tabla de Contenidos

1. [Estrategia de Versionado](#estrategia-de-versionado)
2. [Convenciones de Commits](#convenciones-de-commits)
3. [Flujo de Ramas (Git Flow)](#flujo-de-ramas)
4. [Versionado Semántico](#versionado-semántico)
5. [Proceso de Release](#proceso-de-release)
6. [Scripts de Automatización](#scripts-de-automatización)
7. [Changelog](#changelog)
8. [Cheatsheet](#cheatsheet)

---

## 🎯 Estrategia de Versionado

### Modelo: Git Flow Simplificado

```
main (producción) ─────────────────────────────────────
    │
    └── develop (integración) ─────────────────────────
         │
         ├── feature/kafka-fix ────────┐
         ├── feature/auth-ui ──────────┤→ Pull Request → develop
         └── feature/new-endpoint ─────┘
    │
    └── release/v2.1.0 ────────────────→ Merge → main + Tag
```

### Ramas Principales

| Rama | Propósito | Protección |
|------|-----------|------------|
| `main` | Código en producción | ✅ Protegida - solo via PR |
| `develop` | Integración continua | ✅ Protegida - solo via PR |
| `feature/*` | Nuevas funcionalidades | ❌ No protegida |
| `release/v*.*.*` | Preparación de release | ❌ No protegida |
| `hotfix/*` | Correcciones urgentes | ❌ No protegida |

---

## 📝 Convenciones de Commits

### Formato: Conventional Commits

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Tipos de Commit

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `feat` | Nueva funcionalidad | `feat(auth): add JWT token refresh` |
| `fix` | Corrección de bug | `fix(kafka): resolve acks type coercion` |
| `docs` | Documentación | `docs(readme): update API examples` |
| `style` | Formato, sin cambios de código | `style(lint): fix ESLint warnings` |
| `refactor` | Refactorización | `refactor(pool): simplify connection caching` |
| `perf` | Mejora de rendimiento | `perf(query): optimize dataset loading` |
| `test` | Tests | `test(api): add device endpoint tests` |
| `chore` | Tareas de mantenimiento | `chore(deps): upgrade dependencies` |
| `ci` | CI/CD | `ci(docker): optimize build stages` |
| `build` | Build system | `build(vite): update production config` |

### Scopes Comunes

- `api` - Backend API
- `frontend` - Frontend React
- `transmission` - Transmission service
- `auth` - Autenticación
- `db` - Base de datos
- `docker` - Configuración Docker
- `docs` - Documentación

### Ejemplos

```bash
# Nueva funcionalidad
feat(transmission): add Kafka protocol support

# Corrección con referencia a issue
fix(connection): resolve pool memory leak

Fixes #123

# Breaking change
feat(api)!: change device status enum values

BREAKING CHANGE: DeviceStatus values changed from strings to integers

# Con scope múltiple
feat(auth,api): implement OAuth2 flow with PKCE
```

---

## 🌿 Flujo de Ramas

### 1. Desarrollo de Feature

```bash
# 1. Actualizar develop
git checkout develop
git pull origin develop

# 2. Crear feature branch
git checkout -b feature/nombre-descriptivo

# 3. Desarrollar con commits convencionales
git add .
git commit -m "feat(scope): description"

# 4. Push y crear Pull Request
git push -u origin feature/nombre-descriptivo
# → Crear PR en GitHub hacia develop
```

### 2. Preparar Release

```bash
# 1. Crear rama de release
git checkout develop
git pull origin develop
git checkout -b release/v2.1.0

# 2. Actualizar versión y changelog
# Editar version en package.json, pyproject.toml, etc.

# 3. Commit de versión
git add .
git commit -m "chore(release): bump version to 2.1.0"

# 4. Merge a main y develop
git checkout main
git merge release/v2.1.0
git tag -a v2.1.0 -m "Release v2.1.0 - Kafka Support"
git push origin main --tags

git checkout develop
git merge release/v2.1.0
git push origin develop
```

### 3. Hotfix (emergencia)

```bash
# 1. Crear desde main
git checkout main
git pull origin main
git checkout -b hotfix/critical-fix

# 2. Aplicar fix
git commit -m "fix(scope): critical bug fix"

# 3. Merge a main y develop
git checkout main
git merge hotfix/critical-fix
git tag -a v2.1.1 -m "Hotfix v2.1.1"
git push origin main --tags

git checkout develop
git merge hotfix/critical-fix
git push origin develop
```

---

## 🏷️ Versionado Semántico

### Especificación: SemVer 2.0.0

```
MAJOR.MINOR.PATCH[-prerelease][+build]

Ejemplos:
  2.1.0         - Release estable
  2.1.0-beta.1  - Prerelease beta
  2.1.0+build.123 - Con metadato de build
```

### Reglas de Incremento

| Incremento | Cuándo | Ejemplo |
|------------|--------|---------|
| **MAJOR** | Breaking changes incompatibles | API v1 → v2, cambios de contrato |
| **MINOR** | Nuevas funcionalidades backwards-compatible | Nuevo endpoint, nueva feature |
| **PATCH** | Correcciones de bugs backwards-compatible | Fix de bug, refactor interno |

### Flujo de Versiones

```
2.0.0 → 2.1.0-alpha.1 → 2.1.0-alpha.2 → 2.1.0-beta.1 → 2.1.0-rc.1 → 2.1.0 → 2.1.1
```

---

## 🚀 Proceso de Release

### Checklist Pre-Release

- [ ] Todas las features mergeadas a develop
- [ ] Tests pasando (`pytest`, `npm test`)
- [ ] Linting sin errores (`ruff`, `eslint`)
- [ ] Docker build exitoso
- [ ] Changelog actualizado
- [ ] Version bump en:
  - [ ] `package.json` (frontend)
  - [ ] `pyproject.toml` / `setup.py` (backend)
  - [ ] `docker-compose.yml` tags
  - [ ] `VERSION` file

### Crear Release

#### Opción A: Script Automatizado (Recomendado)

```bash
./scripts/git-release.sh 2.1.0
```

#### Opción B: Manual

```bash
# 1. Preparar
git checkout develop
git pull origin develop

# 2. Crear rama release
git checkout -b release/v2.1.0

# 3. Actualizar versiones
# - frontend/package.json
# - api-service/pyproject.toml
# - transmission-service/pyproject.toml
# - VERSION file

# 4. Generar changelog
git log --pretty=format:"- %s" v2.0.0..HEAD > CHANGELOG.md

# 5. Commit
git add .
git commit -m "chore(release): prepare v2.1.0"

# 6. Merge a main
git checkout main
git merge --no-ff release/v2.1.0

# 7. Tag
git tag -a v2.1.0 -m "Release v2.1.0

Features:
- Kafka protocol support
- Enhanced authentication UI
- Dataset bulk operations

Fixes:
- Connection pool memory leak
- Row index synchronization

Full changelog: CHANGELOG.md"

# 8. Push
git push origin main --tags

# 9. Merge a develop
git checkout develop
git merge --no-ff release/v2.1.0
git push origin develop

# 10. Crear GitHub Release
gh release create v2.1.0 \
  --title "IoT-DevSim v2.1.0" \
  --notes-file CHANGELOG.md \
  --draft
```

---

## 🤖 Scripts de Automatización

### 1. `scripts/git-push.sh` - Push Seguro

Valida antes de hacer push:
- No commits en main/develop directamente
- Tests pasando
- Linting sin errores
- Mensaje de commit válido

```bash
./scripts/git-push.sh
```

### 2. `scripts/git-release.sh` - Crear Release

Automatiza todo el proceso de release:
- Bump de versión
- Generación de changelog
- Creación de tag
- Push a GitHub
- Creación de GitHub Release

```bash
./scripts/git-release.sh <version> [options]

Opciones:
  -d, --dry-run    Simular sin ejecutar
  -f, --force      Saltar confirmaciones
  -h, --help       Mostrar ayuda

Ejemplos:
  ./scripts/git-release.sh 2.1.0
  ./scripts/git-release.sh 2.1.0-beta.1
  ./scripts/git-release.sh 2.2.0 --dry-run
```

### 3. `scripts/bump-version.sh` - Actualizar Versión

Actualiza la versión en todos los archivos:

```bash
./scripts/bump-version.sh 2.1.0
```

---

## 📝 Changelog

### Formato: Keep a Changelog

```markdown
# Changelog

Todas las modificaciones notables de este proyecto se documentarán en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nueva funcionalidad X
- Soporte para protocolo Y

### Changed
- Mejora de rendimiento en Z

### Fixed
- Corrección de bug en W

## [2.1.0] - 2026-02-13

### Added
- feat(kafka): implement Kafka protocol handler
- feat(auth): add OAuth2 PKCE flow
- feat(api): bulk operations for connections

### Fixed
- fix(transmission): resolve acks type coercion
- fix(pool): memory leak in connection caching

### Security
- security(seed): replace hardcoded passwords with env vars

## [2.0.0] - 2026-01-15
...

[Unreleased]: https://github.com/usuario/iot-devsim/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/usuario/iot-devsim/compare/v2.0.0...v2.1.0
```

---

## 📚 Cheatsheet

### Comandos Rápidos

```bash
# Iniciar feature
git checkout develop && git pull && git checkout -b feature/nombre

# Commits convencionales
git commit -m "feat(scope): description"
git commit -m "fix(kafka): resolve connection timeout" -m "Closes #123"

# Ver historial formateado
git log --oneline --graph --decorate

# Comparar con último tag
git log $(git describe --tags --abbrev=0)..HEAD --oneline

# Ver cambios no pusheados
git log @{u}..

# Deshacer último commit (mantener cambios)
git reset --soft HEAD~1

# Deshacer último commit (perder cambios)
git reset --hard HEAD~1

# Amend al último commit
git commit --amend --no-edit

# Stash temporal
git stash push -m "descripción"
git stash pop

# Ver stashes
git stash list
```

### Flujo Completo Feature → Production

```bash
# 1. Crear feature
feat iniciar kafka-support

# 2. Desarrollar y commitear
git add . && git commit -m "feat(kafka): add producer handler"

# 3. Push
git push origin feature/kafka-support

# 4. Crear PR en GitHub (Web/UI)
# → Merge a develop

# 5. Preparar release
./scripts/git-release.sh 2.1.0

# 6. Deploy
./scripts/deploy.sh production
```

---

## 🔗 Recursos

- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)
- [GitHub Flow](https://docs.github.com/en/get-started/quickstart/github-flow)

---

## 🆘 Soporte

¿Problemas con el versionado?

1. Consulta el [cheatsheet](#cheatsheet)
2. Revisa la documentación de los [scripts](./scripts/)
3. Crea un issue en GitHub con tag `question`

---

**Última actualización:** 2026-02-13  
**Mantenido por:** IoT-DevSim Team
