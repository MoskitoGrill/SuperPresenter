import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

test('one name field saves default or overwrites a named arrangement without duplicates', async ({ page }) => {
  await page.goto('./');
  await expect(page.getByText('Pokročilá úprava skupin a opakování', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Správa pořadí', { exact: true })).toHaveCount(0);
  const name = page.getByLabel('Název opakování', { exact: true });
  await expect(name).toHaveValue('');
  await page.getByLabel('Název písně', { exact: true }).fill('Pojmenování pořadí');
  await page.getByLabel('Sloka 1', { exact: true }).fill('Sloka');
  await page.locator('.available-parts').getByRole('button', { name: 'Sloka 1', exact: true }).click();
  async function xml() {
    await page.getByText('Stáhnout', { exact: true }).click();
    const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'XML', exact: true }).click()]);
    await download.saveAs('test-output/named-order.xml');
    return readFileSync('test-output/named-order.xml', 'utf8');
  }
  const initial = await xml();
  expect(initial).toContain('<repetition name="default" main="1">v1</repetition>');
  await page.getByRole('button', { name: 'Refrén', exact: true }).click();
  await page.getByLabel('Refrén 1', { exact: true }).fill('Refrén');
  await page.locator('.available-parts').getByRole('button', { name: 'Refrén 1', exact: true }).click();
  await name.fill('kapela 1');
  page.once('dialog', d => d.accept()); await page.reload();
  await expect(name).toHaveValue('kapela 1');
  await expect(page.locator('#preview pre')).toHaveText(['Sloka', 'Refrén']);
  const named = await xml();
  expect(named).toContain('<repetition name="default">v1</repetition>');
  expect(named).toContain('<repetition name="kapela 1" main="1">v1 r1</repetition>');
  await page.locator('.available-parts').getByRole('button', { name: 'Refrén 1', exact: true }).click();
  await name.fill('kapela 1');
  const updated = await xml();
  expect(updated.match(/name="kapela 1"/g)).toHaveLength(1);
  expect(updated).toContain('>v1 r1 r1</repetition>');
  // An already existing target gets replaced, while other named orders survive.
  await name.fill('');
  const fallback = await xml();
  expect(fallback.match(/name="default"/g)).toHaveLength(1);
  expect(fallback).toContain('<repetition name="default" main="1">v1 r1 r1</repetition>');
  expect(fallback).toContain('<repetition name="kapela 1">v1 r1 r1</repetition>');
  await page.getByLabel('Otevřít XML', { exact: true }).setInputFiles('test-output/named-order.xml');
  await expect(name).toHaveValue('');
  await expect(page.locator('#preview pre')).toHaveText(['Sloka', 'Refrén', 'Refrén']);
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({ path: 'test-output/named-order.png', fullPage: true });
});
