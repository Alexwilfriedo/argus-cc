# Argus — plugin QA/QE pour Claude Code

**Argus** est un agent QA/QE invocable par `/argus` dans Claude Code. Il dialogue, puis :
- **installe un harness `@playwright/test` de non-régression** dans ton projet (régression visuelle,
  accessibilité axe/WCAG, Core Web Vitals, liens, console/réseau, sécurité DAST/SCA/headers/authz,
  rapports JSON/JUnit/HTML, CI GitHub Actions) ;
- ou mène un **audit live** d'une app web (mode EXPLORE), avec une couche **démo vidéo** optionnelle (DEMO).

Trois modes : **EXPLORE** (audit), **DEMO** (capture YouTube), **REGRESS** (suite déterministe, gating CI).

---

## Installation

### Option A — Plugin (recommandé)
Dans Claude Code :
```
/plugin marketplace add https://github.com/<ton-user>/argus
/plugin install argus@alexwilfriedo
```
> En local sans Git : `/plugin marketplace add /chemin/vers/argus`.

Puis, dans n'importe quel projet :
```
/argus
```

### Option B — Copie manuelle du skill
```bash
cp -R argus/skills/argus ~/.claude/skills/argus
```
Le skill `/argus` est alors disponible dans toutes tes sessions.

---

## Utilisation

1. Tape `/argus`. Il te demande l'objectif (installer le harness ou lancer un audit), l'URL,
   l'environnement, l'auth, etc.
2. Pour le harness : il copie le scaffold, tu édites **`argus.config.ts`** (URL, routes, breakpoints,
   navigateurs, seuils), puis :
   ```bash
   npm install
   npx playwright install --with-deps chromium
   npm run argus:test        # suite complète (smoke, visual, a11y, links, security, authz)
   npm run argus:report      # rapport HTML Argus
   ```

## Prérequis
- **Node ≥ 18**, npm. Playwright s'installe à l'usage (`npx playwright install`).
- Docker (optionnel) pour le DAST OWASP ZAP (`npm run argus:zap`).

## Garde-fous
Argus est **lecture seule par défaut en prod** ; écritures uniquement en staging/local avec données
jetables ; secrets via variables d'environnement. Détails : `skills/argus/references/methodology.md`.

## Mises à jour
Bumper `version` dans `.claude-plugin/plugin.json` **et** `.claude-plugin/marketplace.json`, puis
commit/push. Les utilisateurs font `/plugin marketplace update alexwilfriedo`.

## Contenu
```
.claude-plugin/{plugin.json, marketplace.json}
skills/argus/
  ├── SKILL.md                 # orchestrateur interactif
  ├── references/              # méthodologie, mode démo, format de rapport
  ├── scripts/install.sh       # copie idempotente du scaffold
  └── assets/scaffold/         # le harness @playwright/test réel
```

*Plugin perso · v1.0.0 · MIT*
