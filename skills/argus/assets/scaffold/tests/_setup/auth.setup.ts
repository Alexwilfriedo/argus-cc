import { test as setup, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { argus } from '../../argus.config';

setup('préparer la session de test', async ({ page }) => {
  const state = path.resolve(argus.auth.storageState);
  fs.mkdirSync(path.dirname(state), { recursive: true });

  if (!argus.auth.required) {
    await page.context().storageState({ path: state });
    return;
  }

  const { QA_USER, QA_PASS } = process.env;
  if (!QA_USER || !QA_PASS) {
    throw new Error("Session authentifiée demandée. Fournir QA_USER et QA_PASS ou choisir ARGUS_AUTH=off.");
  }
  await page.goto(new URL(argus.auth.loginPath, argus.baseURL).href);
  await page.getByLabel(/e-?mail|utilisateur|username/i).fill(QA_USER);
  await page.getByLabel(/mot de passe|password/i).fill(QA_PASS);
  await page.getByRole('button', { name: /se connecter|sign in|connexion/i }).click();

  // Adapter ce signal à l’identité affichée par l’application testée.
  await expect(page.getByRole('button', { name: /profil|account|déconnexion|logout/i })).toBeVisible();
  await page.context().storageState({ path: state });
});
