import { test, expect } from '@playwright/test';

test('static assets under repository path and editing without network', async ({ page, context }) => {
  const requests: string[] = [];
  page.on('request', request => requests.push(request.url()));
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('./');
  await expect(page.getByLabel('Název písně', { exact: true })).toBeVisible();
  const root = new URL(page.url());
  expect(root.pathname.endsWith('/')).toBe(true);
  expect(requests.every(url => url.startsWith(root.href))).toBe(true);
  expect(requests.some(url => /\/assets\/.*\.js/.test(url))).toBe(true);
  await context.setOffline(true);
  await page.getByLabel('Název písně', { exact: true }).fill('Offline zkouška');
  await page.getByLabel('Sloka 1', { exact: true }).fill('Text bez sítě');
  await page.locator('.available-parts').getByRole('button', { name: 'Sloka 1', exact: true }).click();
  await expect(page.locator('#preview pre')).toHaveText(['Text bez sítě']);
  await page.getByText('Stáhnout', { exact: true }).click();
  const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'XML', exact: true }).click()]);
  expect(download.suggestedFilename()).toBe('Offline zkouška.xml');
  await context.setOffline(false);
  page.once('dialog', d => d.accept());
  await page.reload();
  await expect(page.getByLabel('Název písně', { exact: true })).toHaveValue('Offline zkouška');
  expect(errors).toEqual([]);
});
