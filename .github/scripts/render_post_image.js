// Render a post-image HTML file (1200x900) to a JPEG.
// Usage: node .github/scripts/render_post_image.js <name>
//   reads  .github/post-images/<name>.html
//   writes assets/posts/<name>.jpg
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
  const name = (process.argv[2] || '').trim();
  if (!/^[a-z0-9][a-z0-9-]*$/.test(name)) {
    console.error('Usage: render_post_image.js <name> (lowercase letters, numbers, hyphens)');
    process.exit(1);
  }
  const root = path.resolve(__dirname, '..', '..');
  const src = path.join(root, '.github', 'post-images', name + '.html');
  if (!fs.existsSync(src)) {
    console.error('No such file: ' + src);
    process.exit(1);
  }
  const outDir = path.join(root, 'assets', 'posts');
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 }, deviceScaleFactor: 1.5 });
  await page.goto('file://' + src);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
  const out = path.join(outDir, name + '.jpg');
  await page.screenshot({ path: out, type: 'jpeg', quality: 92 });
  await browser.close();
  console.log('wrote ' + path.relative(root, out));
})();
