# Fieldwork design system

## Project and audience
Fieldwork is a set of independent, guided future-state workflow demonstrations for US HVAC contractors and their office managers. A visitor should recognise a moment from their working day and see a plausible, calmer way for that work to move. The primary action is to explore a scenario and start a conversation, not to operate a pretend CRM.

## Visual direction
**Editorial field-service engineering.** The visual world comes from work orders, dispatch boards, maintenance schedules, estimate jackets and property service records. The page should feel like an intelligently designed operating manual, not a generic SaaS landing page.

The memorable element is the work artefact itself: each company gets a bespoke request board, estimate jacket, property service record, booking review or annual maintenance timeline. The artefact carries the story; decoration does not.

## Tokens
- Paper: `#E7ECE8`
- Sheet: `#F8FAF6`
- Ink: `#1B3038`
- Steel: `#52666D`
- Rule: `#B9C5C0`
- Deep field: `#18323D`
- Secondary field: `#274752`
- Signal orange: `#E8A13A`
- Signal ink: `#5A3911`
- Completed work: `#477467`

Typography pairs IBM Plex Serif for editorial display with IBM Plex Sans for reading and interface text (Georgia and system sans fallbacks). Do not use condensed display faces for long headlines. Avoid negative tracking on headings; keep letter spacing at normal and use line-height around 1.02–1.12. Data values use tabular numerals where needed. Small labels stay in sentence case and the body face.

## Layout rules
- Use asymmetrical editorial composition; left-align headings and copy.
- Hero shows a real workflow artefact immediately, not a row of generic metrics.
- Story scenes pair a short narrative with a bespoke operational visual.
- Each company's art differs according to its workflow: dispatch lanes, estimate jacket, property service record, appointment ledger, annual service calendar.
- Use full-width working surfaces, ruled rows and rectangular controls. Avoid repeated floating cards.
- Keep the page content within a centred 1180px measure, with fluid outer gutters.
- Motion only responds to the visitor's scene navigation. Respect reduced motion.

## Explicit anti-patterns
Do not introduce:
- Purple/blue gradients, radial gradient washes or decorative gradients.
- Generic white card stacks, nested cards, floating rounded dashboards or fake browser/OS windows.
- Eyebrow headers, tracked all-caps labels, small-caps labels, decorative micro-labels, or tightly tracked/condensed headline typography.
- Repetitive centered hero blocks, repeated 3-card metrics, generic feature grids or fake testimonials.
- Pill buttons, decorative status dots, emoji icons, arrows appended to link labels or middle-dot meta strings.
- Monospace labels as decoration, italic emphasis inside headings, or one highlighted word in a headline.
- Fake lead forms, fake email capture, invented performance metrics or fabricated customer proof.
- Claims that a workflow is connected, automated, integrated or in use by the named company.

## Content and truth
- The named company is the intended audience, not the owner of the concept.
- Sample names, dates, records and appointment windows are illustrative.
- Company-specific operational claims must be grounded in its public website or confirmed directly by the business.
- Do not state savings, revenue lift, conversion improvement or other ROI without measured evidence.
- Say what a person does and what the system makes visible. Keep pricing, dispatch and final customer communication under human control unless a real implementation proves otherwise.

## Quality floor
- Keyboard-visible focus on every interactive element.
- Five content scenes and five matching visual scenes per walkthrough.
- Back, Next, direct scene selection and replay must work.
- Responsive layout must have no horizontal overflow at 375px.
- Reduced-motion preference must suppress nonessential animation.
- Content should remain readable with JavaScript disabled.
- Run `node scripts/design-guard.mjs` and the Playwright smoke test before publishing.

## Page-specific compositions
The system is shared, but the composition must follow the artefact rather than repeat one page template:
- Optimized Mechanical: dispatch lanes and a shared queue.
- Barron's: estimate jacket first; the document leads the composition.
- Rojas & Sons: wide property service record with the request context in view.
- Ordine's: appointment review with more horizontal space for the schedule.
- 3H AC: full-width annual calendar; the agreement timeline leads the page.

Do not homogenise these into identical hero/feature/card sections.
