# Claude Code project instructions

Before changing website design or front-end code, read `PRODUCT.md` and `DESIGN.md`. These files are the source of truth for audience, intent, visual direction and anti-patterns.

## Mandatory process
1. Inspect the relevant page and its actual copy before editing.
2. Make a short plan: the one job of the page, its strongest real workflow artefact, the layout composition and the tokens being used.
3. Keep the composition specific to the company workflow. Do not reuse a generic SaaS landing-page template across the five stories.
4. Build one scene at a time. The operational artefact must be the visual focus.
5. Critique the rendered page at desktop and mobile sizes. Do not approve based on source code alone.
6. Run `node scripts/design-guard.mjs`.
7. Run the browser check in CI: `node tests/site-smoke.mjs` after installing Playwright and Chromium.
8. Run `npx impeccable detect site/` when the Impeccable CLI is available. Resolve real findings; do not silence a rule to preserve an accidental style.

## Typography constraints
- Use the wider Arial/Helvetica display stack defined in `DESIGN.md`, not Impact or Arial Narrow.
- Do not use negative letter-spacing on headings or wordmarks. Keep display tracking at normal and line-height open enough for multi-line reading.
- Review headline kerning and word spacing at 1440px and 375px before approval.

## Non-negotiable visual constraints
- No purple/blue gradients, radial washes, generic floating cards, nested cards or fake browser chrome.
- No tracked all-caps labels, eyebrow headers, fake testimonials, decorative micro-labels or generic metrics.
- No pill controls, generic shadow stacks, decorative status dots or arrows appended to link text.
- Avoid repeated hero-card / three-metric / three-feature patterns.
- Do not add an image or illustration unless it explains the workflow. Prefer real artefacts and precise operational diagrams over stock imagery.
- Do not invent numbers, customer outcomes, quotes, company systems or integrations.

## Content constraints
Use direct language. Explain what the person does and what the proposed workflow makes visible. Keep the scenario explicitly illustrative and the company clearly independent of the concept.
