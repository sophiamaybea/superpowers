---
name: superpowers-web-design
description: High-fidelity website reconstruction, creative frontend design, visual QA and iterative repair.
---
# Web design and website reconstruction

## Establish the reference
- Ask for the source URL or screenshots when absent. Record viewport dimensions, page routes, visible states, typography, spacing, colours, imagery, motion, and interactions. Do not claim to have inspected a site without a successful fetch/browser session.
- Respect copyright, licences, authentication and access restrictions. Rebuild from authorised references; never copy private assets or bypass paywalls.
- Define a measurable acceptance checklist for desktop, tablet, mobile, keyboard, reduced motion, loading and failure states.

## Choose the implementation
- Inspect the existing project and avoid unnecessary framework migration.
- Research official docs, GitHub repositories, open-source component libraries, animation examples, accessibility guidance and relevant community debugging discussions.
- Compare alternatives by reference fidelity, licensing, maintenance, bundle cost, accessibility, and reproducible demos. Do not equate popularity with suitability.
- For creative builds consider CSS, SVG, GSAP, WebGL/Three.js/R3F, canvas and shader techniques only when the reference warrants them. Prefer simpler, more performant methods when equivalent.

## Build and verify
- Implement real layouts and behaviour; avoid static screenshots as substitutes for functional pages.
- Run build, typecheck and automated tests where tools exist. Use browser screenshots at matching viewports and states, compare side by side, and prioritise major visual differences (composition, typography, spacing, colour, imagery, motion).
- Verify interactions, navigation, focus order, semantic HTML, contrast, responsive overflow, loading states and reduced motion.
- When verification fails: record exact failure, search targeted repos/issues/docs/community sources, select a different credible technique, implement a bounded fix, and rerun tests. Never report visual parity without comparisons.
- Stop when acceptance criteria pass or budget is reached; document remaining discrepancies and evidence.

## Deliverables
- Source code and reproducible run instructions, implementation decisions, research citations, test results, screenshot comparison findings, and unresolved gaps.
