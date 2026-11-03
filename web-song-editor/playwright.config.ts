import { defineConfig } from '@playwright/test';
const remote = process.env.EDITOR_URL;
export default defineConfig({
  testDir: './tests/browser', workers: 1,
  use: { baseURL: remote ?? 'http://127.0.0.1:5187/SuperPresenter/' },
  webServer: remote ? undefined : {
    command: 'node node_modules/vite/bin/vite.js preview --base /SuperPresenter/ --host 127.0.0.1 --port 5187 --strictPort',
    url: 'http://127.0.0.1:5187/SuperPresenter/', reuseExistingServer: false, timeout: 60000,
  },
});
