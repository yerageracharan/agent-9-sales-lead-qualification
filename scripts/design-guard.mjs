import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const pages = [
  "site/previews/optimized-mechanical/index.html",
  "site/previews/barrons-air/index.html",
  "site/previews/rojas-sons/index.html",
  "site/previews/ordines-hvac/index.html",
  "site/previews/3h-ac/index.html"
];
const css = readFileSync(join(root,"site/assets/site.css"),"utf8");
const js = readFileSync(join(root,"site/assets/site.js"),"utf8");
const errors = [];
const checks = [];

function check(ok, message) {
  checks.push({ok,message});
  if (!ok) errors.push(message);
}

const banned = [
  [/linear-gradient\s*\(/i,"gradient decoration"],
  [/radial-gradient\s*\(/i,"radial gradient decoration"],
  [/box-shadow\s*:/i,"generic shadows"],
  [/transition\s*:\s*all/i,"transition: all"],
  [/text-transform\s*:\s*uppercase/i,"uppercase label styling"],
  [/\.eyebrow\b/i,"eyebrow headers"],
  [/border-radius\s*:\s*(?:[5-9]\d|\d{3,})px/i,"large rounded card/pill geometry"],
  [/letter-spacing\s*:\s*\.0[1-9]\w*/i,"tracked label typography"]
];
for (const [pattern,label] of banned) check(!pattern.test(css), `CSS contains forbidden pattern: ${label}`);
check(/html,body\s*\{[^}]*overflow-x\s*:\s*clip/s.test(css),"html and body must clip horizontal overflow");
check(/:focus-visible\s*\{/.test(css),"visible focus style is required");
check(/prefers-reduced-motion\s*:\s*reduce/.test(css),"reduced-motion support is required");
check(/animation-duration:\s*\.01ms/.test(css),"reduced-motion fallback must suppress scene motion");
check(!/data-demo-form|data-load-sample|local-only interaction/i.test(pages.map(p=>readFileSync(join(root,p),"utf8")).join("\n")),"old CRUD demo forms must be removed");
check(js.includes('ArrowRight') && js.includes('ArrowLeft'),"keyboard scene navigation is required");

for (const path of pages) {
  const html = readFileSync(join(root,path),"utf8");
  const contentScenes = (html.match(/data-scene\b/g)||[]).length;
  const visualScenes = (html.match(/data-visual\b/g)||[]).length;
  check(contentScenes===5, `${path}: expected 5 narrative scenes, found ${contentScenes}`);
  check(visualScenes===5, `${path}: expected 5 corresponding visual scenes, found ${visualScenes}`);
  check(/data-start/.test(html) && /data-next/.test(html) && /data-back/.test(html) && /data-replay/.test(html), `${path}: missing walkthrough controls`);
  check(/Independent concept by Charan Yeragera/.test(html), `${path}: missing independent-concept disclosure`);
  check(/<h1>/.test(html), `${path}: missing page headline`);
  check(/site\.js/.test(html), `${path}: missing shared scene controller`);
}
const cssFiles = readdirSync(join(root,"site/assets"));
check(cssFiles.includes("site.css"),"shared stylesheet must exist");
if (errors.length) {
  console.error("Design guard failed:");
  for (const e of errors) console.error(" - "+e);
  process.exit(1);
}
console.log(`Design guard passed: ${checks.length} checks across five bespoke walkthroughs.`);
