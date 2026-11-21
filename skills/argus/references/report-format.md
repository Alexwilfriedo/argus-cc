# Résultats d’une exécution

| Sortie | Producteur | Ce que le lecteur peut y vérifier |
| --- | --- | --- |
| `test-results/results.json` | Reporter JSON Playwright du scaffold | Tests, projets, tentatives, statuts, erreurs globales et pièces jointes |
| `test-results/junit.xml` | Reporter JUnit Playwright | Cas destinés aux outils CI |
| `argus-report/report.html` | `npm run argus:report` | Bilan des cas présents dans le JSON et mesures CWV disponibles, par cas et projet |
| `junit.xml`, `exit-code.txt`, `target.txt` dans le dossier du run | `scripts/mobile.sh` et Maestro | Flows, résultat de la commande, appareil et application demandés |
| PDF de campagne | `scripts/report.py` | Couverture du plan déclaré, constats, blocages et justificatifs selon `references/pdf.md` |

Le code de sortie de la **commande de test** renseigne sur cette exécution. Les commandes HTML et PDF indiquent si l’export a abouti. Les tests ignorés, les échecs attendus et les interruptions sont à expliciter dans le bilan de couverture. Attribuer une sévérité produit demande un impact observé.

En exploration, consigner dans le manifeste l’action, la règle de référence, l’observation et le chemin de la preuve expurgée. Pour annoncer une évolution, comparer deux runs identifiés sur le même périmètre. Pour annoncer une mesure, relever sa valeur et son unité dans le résultat du run. Les fichiers effectivement produits se vérifient avant remise.
