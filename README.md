# CursorCult Rulesets (`_rulesets`)

This repo registers **named rulesets**: curated lists of CursorCult rule packs you can apply as a group.

## What is a ruleset?

A ruleset is a text file at `rulesets/<NAME>.txt` containing newline-separated rule repo names:

```text
TDD
SpecsFirst
TruthOrSilence
```

Rulesets do **not** pin versions. The `cursorcult` CLI links each rule at its latest `vN` tag.

## Availability rule (important)

To be eligible for inclusion in any ruleset, a rule repo must have a **`v0` tag**.

This repo runs a periodic sync that removes any ruleset entries that no longer meet that requirement
(missing repo, missing `v0`, etc.).

## Governance

- **Submission**: Anyone can propose a new ruleset (or edits) via Pull Request.
- **Approval**: Merging requires approval from a CursorCult maintainer.
- **Maintenance**:
    - Rulesets are living documents.
    - Automation periodically removes entries that violate the Availability Rule (missing `v0` tag).
    - Rulesets may be deleted by maintainers if they become obsolete.

## Contributing

- Add or edit a ruleset file under `rulesets/`.
- Keep one rule per line; blank lines and `# comments` are allowed.
- CI validates that referenced rules exist in `https://github.com/CursorCult` and have a `v0` tag.

## Using a ruleset

With `cursorcult` installed:

```sh
pipx install cursorcult
cursorcult link --ruleset <NAME>
```

