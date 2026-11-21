# Remettre le rapport de campagne

Créer un manifeste JSON pour une exécution. Nommer l’application, le build, l’environnement et le périmètre vérifié. Avant le run, figer les scénarios prévus pour chaque cible. Après le run, compléter les notes à partir des preuves et joindre le PDF au bilan. Les sources sont relatives au manifeste. Regrouper uniquement les résultats du même build et de la même campagne.

```json
{
  "title": "Réservation d’un créneau",
  "build": "1.4.0 · build de recette 32",
  "scope": "Validation des périodes sur simulateur, données synthétiques.",
  "targets": [{
    "label": "iOS · simulateur de recette",
    "maestro": "ios-period-01",
    "planned": ["Fin égale au début", "Correction après refus"],
    "notes": {
      "Fin égale au début": {
        "expected": "La période est refusée.",
        "actual": "La période est acceptée.",
        "severity": "major",
        "repro": "Choisir le même jour pour les deux dates puis valider.",
        "evidence": "ios-period-01/junit.xml, cas Fin égale au début",
        "action": "Appliquer la règle stricte lors de la validation."
      }
    }
  }]
}
```

Chaque cible a un libellé, une liste `planned` de noms uniques et une source :

- `maestro` prend le dossier d’un run de `mobile.sh`. Utiliser le champ `name` du flow.
- `playwright` prend le JSON du reporter, typiquement `test-results/results.json`. L’identifiant combine projet, titres de suites (dont le fichier) et titre de spec, séparés par « › ». Les projets distincts restent identifiables. Utiliser les intitulés du projet et les cas listés par Playwright pour préparer le plan.
- `observations` prend une liste de contrôles exploratoires, d’intégration ou manuels. Exemple : `{"name":"Reprise du brouillon","status":"pass","evidence":"preuve-07.png","actual":"Le texte saisi est restauré."}`. Statuts acceptés : `pass`, `fail`, `flaky`, `skip`, `blocked`. Pour un blocage, indiquer le motif dans `actual`. Pour un cas repris après échec, conserver les deux preuves et le statut instable si le résultat a changé sur le même build.
- Les détails `expected`, `actual`, `repro`, `evidence`, `severity` et `action` enrichissent une ligne. Le champ facultatif `screenshot` insère une capture PNG relue, située sous le dossier du manifeste. Expurger données et secrets avant l’export. Pour chaque défaut, indiquer l’impact, comment le retrouver et où lire la preuve. Un test rouge appelle un diagnostic avant attribution au produit.

```bash
python3 "$SKILL_DIR/scripts/report.py" campagne.json rapport.pdf
```

Python 3.8+ et Chrome ou Chromium locaux sont nécessaires. Définir `ARGUS_CHROME` si le navigateur se trouve hors des chemins usuels. Le PDF présente les résultats d’exécution, les constats et le nombre de scénarios prévus ayant un résultat. Un scénario supplémentaire apparaît dans le détail sans augmenter le nombre prévu. Un cas prévu mais absent reste non vérifié. Le code de sortie du générateur indique le succès de l’export. Conserver le code du moteur de test pour la CI. Ouvrir le PDF et vérifier sa lisibilité et son périmètre avant remise.
