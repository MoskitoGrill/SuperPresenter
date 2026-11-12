import { test, expect } from '@playwright/test';

for (const width of [1440, 390, 320]) {
  test(`visual stress ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('./');
    const custom = 'Dlouhý_název_vlastní_části_bez_mezer_'.repeat(5);
    const text = Array.from({ length: 60 }, (_, i) => `${i + 1}. Dlouhá píseň — Příliš žluťoučký kůň úpěl ďábelské ódy.`).join('\n');
    const xml = `<slide name="Dlouhá zkušební píseň"><variant name="čeština"><section name="v1">${text}</section><section name="r1">Společný refrén</section><section name="b1">Bridge</section><section name="${custom}">Vlastní text</section></variant><repetition name="default">v1 r1 b1 ${custom}</repetition></slide>`;
    page.on('dialog', d => d.accept());
    await page.getByLabel('Otevřít XML', { exact: true }).setInputFiles({ name: 'long.xml', mimeType: 'application/xml', buffer: Buffer.from(xml) });
    await page.locator('#result > summary').click();
    await expect(page.locator('#preview pre')).toHaveCount(4);
    await page.getByLabel('Sloka 1', { exact: true }).focus();
    expect(await page.getByLabel('Sloka 1', { exact: true }).evaluate(e => getComputedStyle(e).outlineStyle)).toBe('solid');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const clipped = await page.locator('button').evaluateAll(elements => elements.filter(e => {
      const r = e.getBoundingClientRect(); return e.checkVisibility() && r.width > 0 && (r.left < -1 || r.right > innerWidth + 1 || e.scrollWidth > e.clientWidth + 1);
    }).map(e => e.textContent));
    expect(clipped).toEqual([]);
    await page.evaluate(() => scrollTo(0, 0));
    await page.screenshot({ path: `test-output/visual-stress-${width}.png`, fullPage: true });
    const invalid = xml.replace(`v1 r1 b1 ${custom}</repetition>`, 'missing</repetition>');
    await page.getByLabel('Otevřít XML', { exact: true }).setInputFiles({ name: 'invalid.xml', mimeType: 'application/xml', buffer: Buffer.from(invalid) });
    await expect(page.locator('#sequence > .diagnostic')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.locator('#sequence > .diagnostic').scrollIntoViewIfNeeded();
    await page.screenshot({ path: `test-output/visual-error-${width}.png` });
  });
}
