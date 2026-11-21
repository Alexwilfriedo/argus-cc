# Audit natif avec Maestro

Identifier Android (applicationId de la variante installée), iOS (bundle identifier de la configuration), ou les deux. React Native et Flutter se testent via le binaire natif. Pour une WebView, choisir le moteur selon l’action à observer et vérifier au moins la transition entre vues quand elle fait partie du parcours.

1. Lire les instructions de build et les flows existants. Identifier les services utilisés par le binaire, les comptes synthétiques et les permissions nécessaires. Vérifier `maestro --version`. Démarrer l’émulateur Android ou le simulateur iOS local prévu, installer la version de test et noter son identifiant de build. Lister les appareils avec `adb devices` ou `xcrun simctl list devices booted`.
2. Lancer l’app puis inspecter `maestro --device "$DEVICE_ID" hierarchy`. Choisir un identifiant accessible stable de l’écran attendu après ouverture. Protéger les captures, hiérarchies et journaux comme les traces Playwright. Placer les résultats dans un dossier ignoré par Git.
3. Depuis le projet cible, appeler le script **dans le dossier du skill**. Chaque commande reçoit un nouveau dossier de sortie. Le premier exemple exerce le flow fourni. Le second lance les flows du projet.

```bash
READY_ID="$HOME_SCREEN_ID" bash "$SKILL_DIR/scripts/mobile.sh" \
  "$DEVICE_ID" "$APP_ID" argus-report/ios-smoke-01
bash "$SKILL_DIR/scripts/mobile.sh" \
  "$DEVICE_ID" "$APP_ID" argus-report/ios-period-01 .maestro/period
```

4. Pour chaque scénario de la matrice, créer ou adapter un flow YAML dans les conventions du projet. Partir d’un état synthétique reproductible. Nommer le flow selon sa règle métier, ajouter une assertion sur le résultat et une relecture après navigation si la persistance est en jeu. Pour un refus, contrôler aussi l’absence d’effet de bord. Vérifier les identifiants dans la hiérarchie de chaque plateforme. Les attentes Maestro synchronisées sur un élément visible remplacent les pauses arbitraires. Exécuter chaque cible séparément et conserver son code de sortie.
5. Le dossier contient `junit.xml`, la version de Maestro, la cible, le code de sortie et les artefacts Maestro disponibles. En cas de problème de build, appareil ou driver, conserver le diagnostic et rendre la cible non vérifiée. Pour une reprise, conserver aussi le premier run. Générer le PDF avec `references/pdf.md`.

[Référence CLI Maestro](https://docs.maestro.dev/maestro-cli/maestro-cli-commands-and-options) · [Rapports et artefacts](https://docs.maestro.dev/maestro-flows/workspace-management/test-reports-and-artifacts)
