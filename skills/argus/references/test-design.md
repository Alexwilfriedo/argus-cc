# Concevoir la campagne à partir de l’application

Relever les parcours dans les écrans, stories, contrats, règles métier et suites du projet. Pour chaque décision importante, consigner la source, l’acteur, l’état initial, l’action, la règle et l’effet observable. Confronter les sources. Si l’interface autorise l’égalité et que le contrat demande une inégalité stricte, consigner la divergence avec les deux références. Une attente incertaine reste à arbitrer.

## Déduire les scénarios

| Situation rencontrée | Cas qui distinguent deux comportements | Preuve à recueillir |
| --- | --- | --- |
| Champs interdépendants | Cas valide, égalité, première valeur interdite de chaque côté, changement de l’un après validation de l’autre | Message associé au bon champ, valeur conservée, nouvelle soumission possible |
| Cycle de vie | Transition autorisée et refusée depuis le même état, annulation, reprise, inversion de deux opérations | État relu après retour ou relance, historique si prévu |
| Rôle ou propriété | Même opération métier avec chaque rôle de test prévu, session expirée ou déconnexion | Résultat attendu par le contrat, données de session absentes après déconnexion |
| Écriture asynchrone | Double appui, interruption après soumission, nouvelle tentative après réponse tardive | Nombre d’objets créés, état final et référence de l’opération |
| Données et calculs | Vide, minimum, maximum, précision, arrondi, locale, relation total/détail | Valeur de référence calculée indépendamment, vérifiée après relecture |
| Mobile | Première ouverture, permission refusée puis accordée, arrière-plan, redémarrage, clavier, réseau perdu puis revenu | Contenu accessible, brouillon ou file restaurée selon contrat, absence de doublon |
| Accès et lisibilité | Navigation au clavier ou lecteur d’écran, ordre de focus, taille de texte, erreur de saisie | Champ annoncé, focus récupéré, action encore accessible |

Pour une période à la journée régie par `début < fin`, fixer le début au 11 juin. Essayer le 12, le 11 et le 10 juin comme fins. Après chaque refus, vérifier le motif et, si l’action devait persister, le nombre d’enregistrements. Corriger la fin au 12 puis soumettre à nouveau. Vérifier aussi l’édition du début d’une période déjà valide. Utiliser la précision et le fuseau du domaine. Les changements de mois, années bissextiles et changements d’heure ont un intérêt quand la représentation peut modifier le résultat.

Isoler d’abord une violation à la fois. Puis combiner les facteurs qui interagissent, par exemple expiration de session pendant une reprise hors connexion. En cas de double violation, vérifier la priorité des messages si elle est spécifiée. Utiliser une table de décision pour les conditions combinées, un graphe pour les transitions, des classes d’équivalence pour un grand domaine d’entrées. Réserver les permutations exhaustives aux domaines bornés où elles sont peu coûteuses.

## Exécution et traçabilité

Avant le premier run, inscrire les couples scénario × cible dans le manifeste de campagne (voir `references/pdf.md`). Prioriser les conséquences irréversibles, les changements récents, les parcours fréquents puis les branches peu couvertes. Choisir le niveau qui observe la règle au meilleur coût : tests de domaine pour les combinaisons, intégration pour la persistance et les transactions, E2E pour les parcours et retours visibles. Réutiliser les tests existants. Sur les sujets de sécurité, examiner le code, les configurations et les assertions de droits avec des identités synthétiques.

Préparer des états initiaux indépendants et une sortie attendue déterminée avant exécution. Consigner version, environnement, horloge, fuseau et graine si pertinents. Après un échec, conserver la première preuve et identifier le composant en cause. Si seule la préparation a échoué, consigner le blocage du parcours. Pour une régression, vérifier que le test échoue sur le défaut et passe après correction lorsque les deux versions locales sont disponibles. Remettre les résultats de chaque cible, les cas omis avec leur motif et les références de preuve expurgées.

## Agent de recette propre au projet

Quand l’utilisateur demande un agent réutilisable, produire sa définition dans le format déjà utilisé par le projet pour Claude Code ou Codex. Lui transmettre le périmètre applicatif, les sources des règles, les rôles synthétiques, les commandes de préparation et de test, le dossier des preuves et la procédure de génération du PDF. Relier les scénarios aux fichiers de tests exécutables. L’essayer sur un parcours accepté et un refus avant remise. Une référence au build et à la matrice permet de régénérer les résultats après une évolution.
