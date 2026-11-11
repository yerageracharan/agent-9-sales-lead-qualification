import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import { extname, resolve, sep } from "node:path";

const siteRoot = resolve("site");
const artifactDir = resolve("artifacts/design-review");
await mkdir(artifactDir,{recursive:true});
const port = 4173;
const mime = {
  ".html":"text/html; charset=utf-8",
  ".css":"text/css; charset=utf-8",
  ".js":"text/javascript; charset=utf-8",
  ".svg":"image/svg+xml"
};

const server = createServer(async (req,res) => {
  try {
    let pathname = decodeURIComponent(new URL(req.url||"/","http://localhost").pathname);
    if (pathname==="/" || pathname.endsWith("/")) pathname += "index.html";
    const file = resolve(siteRoot,"."+pathname);
    if (!file.startsWith(siteRoot+sep)) throw new Error("Path outside site root");
    const body = await readFile(file);
    res.writeHead(200,{"content-type":mime[extname(file)]||"application/octet-stream"});
    res.end(body);
  } catch {
    res.writeHead(404);
    res.end("Not found");
  }
});

await new Promise(resolveListen=>server.listen(port,"127.0.0.1",resolveListen));
const browser = await chromium.launch({headless:true});
const slugs = ["optimized-mechanical","barrons-air","rojas-sons","ordines-hvac","3h-ac"];
const failures = [];
const record = (condition,message)=>{if(!condition)failures.push(message)};

try {
  for (const slug of slugs) {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    const browserErrors = [];
    page.on("pageerror",error=>browserErrors.push(error.message));
    await page.goto(`http://127.0.0.1:${port}/previews/${slug}/`,{waitUntil:"networkidle"});
    record((await page.locator("h1").innerText()).trim().length>0,`${slug}: page headline missing`);
    record(await page.locator("[data-scene]").count()===5,`${slug}: narrative scene count is not five`);
    record(await page.locator("[data-visual]").count()===5,`${slug}: visual scene count is not five`);
    const linkAudit = await page.locator("a[href],link[href],script[src]").evaluateAll(nodes =>
      nodes.map(node => node.getAttribute("href") || node.getAttribute("src")).filter(Boolean)
    );
    record(linkAudit.every(url => url.startsWith("https://yerageracharan.github.io/agent-9-sales-lead-qualification/") || url.startsWith("#")), `${slug}: internal link or asset uses a non-canonical origin`);
    record(!linkAudit.some(url => /hide.?out/i.test(url)), `${slug}: legacy hideout domain found in a link`);
    const redirectGuard = await page.locator("head script").allTextContents();
    record(redirectGuard.some(script => script.includes('canonicalHost = "yerageracharan.github.io"') && script.includes("window.location.replace")), `${slug}: canonical-host redirect guard missing`);

    await page.locator("[data-start]").click();
    record(await page.locator(".story.enhanced").count()===1,`${slug}: hero launch did not activate the walkthrough`);
    for(let i=0;i<4;i++) await page.locator("[data-next]").click();
    record((await page.locator("[data-count]").innerText())==="5 of 5",`${slug}: next control did not reach final scene`);
    record(await page.locator("[data-scene].is-active").count()===1,`${slug}: exactly one narrative scene should be active`);
    record(await page.locator("[data-visual].is-active").count()===1,`${slug}: exactly one visual scene should be active`);

    await page.locator("[data-back]").click();
    record((await page.locator("[data-count]").innerText())==="4 of 5",`${slug}: back control failed`);
    await page.locator("[data-replay]").click();
    record((await page.locator("[data-count]").innerText())==="1 of 5",`${slug}: replay control failed`);

    await page.locator("[data-story]").focus();
    await page.keyboard.press("ArrowRight");
    record((await page.locator("[data-count]").innerText())==="2 of 5",`${slug}: keyboard navigation failed`);

    await page.setViewportSize({width:375,height:812});
    const dimensions = await page.evaluate(()=>({
      documentWidth:document.documentElement.scrollWidth,
      viewportWidth:document.documentElement.clientWidth
    }));
    record(dimensions.documentWidth<=dimensions.viewportWidth,`${slug}: horizontal overflow at 375px (${dimensions.documentWidth} > ${dimensions.viewportWidth})`);
    await page.screenshot({path:resolve(artifactDir,`${slug}-mobile.png`),fullPage:true});
    record(browserErrors.length===0,`${slug}: browser errors: ${browserErrors.join(" | ")}`);
    await page.close();
  }

  const landing=await browser.newPage({viewport:{width:375,height:812}});
  await landing.goto(`http://127.0.0.1:${port}/`,{waitUntil:"networkidle"});
  const landingWidth=await landing.evaluate(()=>({doc:document.documentElement.scrollWidth,view:document.documentElement.clientWidth}));
  record(landingWidth.doc<=landingWidth.view,`landing page: horizontal overflow at 375px (${landingWidth.doc} > ${landingWidth.view})`);
  await landing.screenshot({path:resolve(artifactDir,"landing-mobile.png"),fullPage:true});
  await landing.close();

  const noScriptContext=await browser.newContext({javaScriptEnabled:false,viewport:{width:1280,height:900}});
  const noScriptPage=await noScriptContext.newPage();
  await noScriptPage.goto(`http://127.0.0.1:${port}/previews/3h-ac/`,{waitUntil:"networkidle"});
  record(await noScriptPage.locator("[data-scene]:visible").count()===5,"3h-ac: story content must remain visible without JavaScript");
  await noScriptContext.close();
} finally {
  await browser.close();
  await new Promise(resolveClose=>server.close(resolveClose));
}

if(failures.length){
  console.error("Browser quality checks failed:\n"+failures.map(item=>" - "+item).join("\n"));
  process.exit(1);
}
console.log("Browser quality checks passed: five story flows, launch, back, next, replay, keyboard, no-JS fallback and mobile widths.");
