# Scripts de Automatización - IoTDevSim

Colección de scripts para automatizar el flujo de trabajo Git, versionado y releases.

## 📋 Scripts Disponibles

### 1. `git-release.sh` - Crear Releases

Automatiza todo el proceso de creación de releases siguiendo SemVer y Conventional Commits.

```bash
./scripts/git-release.sh <version> [options]
```

**Flujo automatizado:**
1. Valida formato de versión (SemVer)
2. Actualiza versiones en todos los archivos
3. Genera changelog desde último tag
4. Crea rama release/vX.Y.Z
5. Commitea cambios de versión
6. Merge a main y develop
7. Crea tag anotado
8. Push a origin
9. Crea GitHub Release (si gh CLI disponible)

**Ejemplos:**
```bash
./scripts/git-release.sh 2.1.0              # Release normal
./scripts/git-release.sh 2.1.0-beta.1       # Pre-release
./scripts/git-release.sh 2.2.0 --dry-run   # Simulación
./scripts/git-release.sh 2.1.1 --force      # Sin confirmaciones
```

### 2. `git-push.sh` - Push Seguro

Valida cambios antes de hacer push, protegiendo ramas importantes.

```bash
./scripts/git-push.sh [options]
```

**Validaciones:**
- ✅ No push directo a main/develop
- ✅ Mensaje de commit válido (Conventional Commits)
- ✅ Sin commits WIP/TODO/DRAFT
- ✅ Sin archivos grandes (>10MB)
- ✅ Sin archivos con nombres sospechosos

**Ejemplos:**
```bash
./scripts/git-push.sh              # Push normal con validaciones
./scripts/git-push.sh --force    # Saltar validaciones (cuidado!)
```

### 3. `bump-version.sh` - Actualizar Versión

Actualiza la versión en todos los archivos del proyecto.

```bash
./scripts/bump-version.sh <version>
```

**Archivos actualizados:**
- `VERSION` - Archivo de versión principal
- `frontend/package.json` - Versión del frontend
- `api-service/pyproject.toml` - Versión del API
- `transmission-service/pyproject.toml` - Versión del transmission

**Ejemplo:**
```bash
./scripts/bump-version.sh 2.1.0
```

---

## 🚀 Flujo de Trabajo Recomendado

### Desarrollo de Feature

```bash
# 1. Crear feature branch desde develop
git checkout develop
git pull origin develop
git checkout -b feature/nueva-funcionalidad

# 2. Desarrollar con commits convencionales
git add .
git commit -m "feat(auth): add OAuth2 support"

# 3. Push seguro (valida protecciones)
./scripts/git-push.sh

# 4. Crear Pull Request en GitHub hacia develop
# → Code review → Merge
```

### Crear Release

```bash
# 1. Preparar release
./scripts/git-release.sh 2.1.0

# 2. Verificar en GitHub
# → Revisar release creada
# → Verificar tags

# 3. Deploy
./scripts/deploy.sh staging
./scripts/deploy.sh production
```

### Hotfix Urgente

```bash
# 1. Crear hotfix desde main
git checkout main
git pull origin main
git checkout -b hotfix/correccion-critica

# 2. Aplicar fix
git commit -m "fix(api): resolve security vulnerability"

# 3. Usar release script con patch
./scripts/git-release.sh 2.1.1
```

---

## 📚 Referencias

- [VERSIONING_GUIDE.md](../VERSIONING_GUIDE.md) - Guía completa de versionado
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)

---

## 🔧 Requisitos

- **Git** >= 2.25
- **GitHub CLI** (opcional, para crear releases automáticamente)
  ```bash
  # Instalar gh CLI
  # macOS: brew install gh
  # Windows: winget install GitHub.cli
  # Linux: https://github.com/cli/cli/blob/trunk/docs/install_linux.md
  
  # Autenticar
  gh auth login
  ```
- **jq** (opcional, para manipular package.json)
  ```bash
  # macOS: brew install jq
  # Windows: winget install jqlang.jq
  ```

---

## ⚠️ Notas Importantes

1. **Ramas protegidas:** main y develop están protegidas. Usa Pull Requests.
2. **Commits:** Usa Conventional Commits para changelog automático.
3. **Versiones:** Sigue SemVer (MAJOR.MINOR.PATCH).
4. **Tests:** Ejecuta tests antes de crear release.

---

**Mantenido por:** IoT-DevSim Team  
**Última actualización:** 2026-02-13
