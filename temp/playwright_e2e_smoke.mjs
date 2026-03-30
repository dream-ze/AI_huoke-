import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE_URL = 'http://127.0.0.1:5173';
const OUTPUT_DIR = path.resolve('d:/智获客/temp/e2e-artifacts');

async function ensureDir() {
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
}

async function screenshot(page, name) {
  await page.screenshot({ path: path.join(OUTPUT_DIR, name), fullPage: true });
}

async function createMaterialViaBrowserApi(page, title, content) {
  return await page.evaluate(async ({ title, content }) => {
    const token = localStorage.getItem('zhk_token');
    const resp = await fetch('/api/mvp/materials', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        platform: 'xiaohongshu',
        title,
        content,
        source_url: 'https://example.com/e2e-smoke',
        author: 'e2e-smoke',
      }),
    });
    const text = await resp.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }
    return { ok: resp.ok, status: resp.status, data };
  }, { title, content });
}

async function waitForText(page, text, timeout = 120000) {
  await page.waitForFunction(
    (needle) => document.body.innerText.includes(needle),
    text,
    { timeout }
  );
}

async function login(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
  await page.getByLabel('用户名').fill('testuser');
  await page.getByLabel('密码').fill('password123');
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForURL((url) => !url.pathname.endsWith('/login'), { timeout: 30000 });
}

async function testGenerate(page, summary) {
  await page.goto(`${BASE_URL}/mvp-workbench`, { waitUntil: 'networkidle' });
  await screenshot(page, '01-workbench-before-generate.png');

  const localModelButton = page.getByRole('button', { name: /本地模型/ });
  if (await localModelButton.count()) {
    await localModelButton.click();
  }

  await page.getByRole('button', { name: /开始生成/ }).click();

  const successLocator = page.getByText('✨ 生成结果');
  const errorLocator = page.getByText('⚠️ 生成失败');

  const outcome = await Promise.race([
    successLocator.waitFor({ state: 'visible', timeout: 180000 }).then(() => 'success'),
    errorLocator.waitFor({ state: 'visible', timeout: 180000 }).then(() => 'error'),
  ]);

  await screenshot(page, '02-workbench-after-generate.png');

  if (outcome === 'error') {
    const errorText = await errorLocator.locator('xpath=..').innerText();
    summary.generate = { success: false, message: errorText };
    return;
  }

  const finalTextLocator = page.locator('text=🏆 最终推荐版本').locator('xpath=following::*[contains(@style, "white-space")][1]');
  let finalText = '';
  if (await finalTextLocator.count()) {
    finalText = (await finalTextLocator.first().innerText()).slice(0, 300);
  } else {
    finalText = (await page.locator('body').innerText()).slice(0, 500);
  }

  summary.generate = { success: true, snippet: finalText };
}

async function ensureMaterials(page) {
  await page.goto(`${BASE_URL}/mvp-materials`, { waitUntil: 'networkidle' });
  if (await page.getByText('素材库为空').count()) {
    const now = Date.now();
    const created = [];
    for (let i = 0; i < 2; i += 1) {
      const res = await createMaterialViaBrowserApi(
        page,
        `E2E素材-${now}-${i + 1}`,
        `这是用于端到端验证的测试素材内容 ${i + 1}。主题围绕贷款知识科普，适合后续批量入知识库验证。`
      );
      created.push(res);
    }
    await page.reload({ waitUntil: 'networkidle' });
    return created;
  }
  return [];
}

async function testBatchBuildKnowledge(page, summary) {
  const created = await ensureMaterials(page);
  await screenshot(page, '03-materials-before-batch-build.png');

  const rowCheckboxes = page.locator('tbody input[type="checkbox"]');
  const checkboxCount = await rowCheckboxes.count();
  if (checkboxCount === 0) {
    summary.batchBuildKnowledge = {
      success: false,
      message: '素材页没有可选择的复选框，无法执行批量入知识库',
      created,
    };
    return;
  }

  await rowCheckboxes.nth(0).check();
  if (checkboxCount > 1) {
    await rowCheckboxes.nth(1).check();
  }

  await page.getByRole('button', { name: /批量入知识库/ }).click();
  await waitForText(page, '批量入知识库完成', 180000);
  await screenshot(page, '04-materials-after-batch-build.png');

  const messageText = await page.locator('.mat-message').innerText();
  summary.batchBuildKnowledge = {
    success: true,
    message: messageText,
    created,
  };
}

async function main() {
  await ensureDir();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  const summary = {
    baseUrl: BASE_URL,
    generate: null,
    batchBuildKnowledge: null,
  };

  try {
    await login(page);
    await screenshot(page, '00-after-login.png');
    await testGenerate(page, summary);
    await testBatchBuildKnowledge(page, summary);
  } finally {
    await browser.close();
  }

  const summaryPath = path.join(OUTPUT_DIR, 'summary.json');
  await fs.writeFile(summaryPath, JSON.stringify(summary, null, 2), 'utf8');
  console.log(JSON.stringify(summary, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});