# Source Strategy

This skill treats `papers.cool` as the discovery layer, not the final ground truth.

## Reliability order

1. `papers.cool` venue and paper pages
2. Official external proceedings page exposed on the paper card
3. Official PDF url exposed on the paper card
4. Local PDF extraction when the PDF is available

## Working rules

- Prefer the official external link over a `papers.cool` summary when citing venue metadata.
- Treat `Kimi` explanations on `papers.cool` as optional reading, not as a default source for facts.
- If there is no official link or PDF, say that the record does not yet expose external materials for verification.
- If PDF extraction is unavailable, keep briefs abstract-based and label them clearly.
