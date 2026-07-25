# Governance and maintenance

The EATF Agent Evidence Package toolkit is maintained by Anton Sokolov at
Tyche Institute. The repository is an open research-software project rather
than a hosted service or standards body.

## Decisions

Routine fixes are decided through issue and pull-request discussion. Changes
to cryptographic meaning, canonical bytes, required entries, or verdict
semantics require:

- a written rationale and compatibility analysis;
- matching TypeScript and Python behavior;
- shared positive and negative vectors;
- updated schemas and format documentation; and
- a versioned release note.

The maintainer makes the final release decision and records material
trade-offs publicly. Sustained contributors may be invited as reviewers or
maintainers based on demonstrated work, not affiliation.

## Releases and compatibility

Releases use semantic versioning while the package names remain at major
version zero. Tags are immutable and archived releases receive persistent
identifiers. The current signer emits the current profile; verifier support
for explicitly labeled legacy packages is maintained only when its weaker
security meaning can be reported accurately.

Security fixes may receive an accelerated release. Ordinary feature requests
have no guaranteed service level. The project aims to acknowledge public
issues and private vulnerability reports within seven days, subject to
maintainer availability.

## Scope

Accepted work must support the public package toolkit: signing, inspection,
verification, schemas, vectors, examples, packaging, or reproducibility.
Hosted tenant management, policy administration, dashboards, and managed
trust services belong outside this repository.
