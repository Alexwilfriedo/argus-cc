import { test, expect } from '@playwright/test';
import { argus } from '../argus.config';

/**
 * argus :: authz — contrôle d'accès (broken access control / IDOR).
 *
 * 1) Un visiteur ANONYME ne doit pas atteindre les routes protégées
 *    (argus.config.protectedRoutes). Actif dès qu'au moins une route est déclarée.
 * 2) Isolation inter-rôles (IDOR) — exemple à compléter avec une assertion métier
 *    (argus.config.roles, chacun avec son storageState).
 *
 * Non destructif : on NAVIGUE et on observe le verdict d'accès, sans rien muter.
 */

test.describe("argus :: authz (contrôle d'accès)", () => {
  test('un visiteur anonyme ne peut PAS accéder aux routes protégées', async ({ browser }) => {
    test.skip(
      argus.protectedRoutes.length === 0,
      'Aucune route protégée déclarée (argus.config.protectedRoutes).',
    );

    // Contexte VIERGE sans storageState → vrai anonyme (ignore l'auth du projet).
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    const leaks: string[] = [];

    try {
      for (const route of argus.protectedRoutes) {
        const url = new URL(route, argus.baseURL).toString();
        const res = await page.goto(url, { waitUntil: 'load' });
        const status = res?.status() ?? 0;
        expect(status, 'Réponse HTTP absente').toBeGreaterThan(0);
        expect(status, 'Service indisponible').toBeLessThan(500);
        const finalUrl = page.url();
        const login = new URL(argus.auth.loginPath, argus.baseURL);
        const destination = new URL(finalUrl);
        const redirectedToAuth = destination.origin === login.origin && destination.pathname === login.pathname && url !== finalUrl && status >= 200 && status < 400;
        const blockedStatus = status === 401 || status === 403;
        // Accès correctement refusé si 401/403 OU redirigé vers une page d'auth.
        if (!blockedStatus && !redirectedToAuth) {
          leaks.push(`${route} → HTTP ${status} (URL finale: ${finalUrl})`);
        }
      }
    } finally {
      await ctx.close();
    }

    expect(
      leaks,
      leaks.length ? `Routes protégées atteignables en anonyme :\n${leaks.join('\n')}` : '',
    ).toEqual([]);
  });

  test.fixme('isolation inter-rôles — assertion métier à fournir dans le projet', () => {});
});
