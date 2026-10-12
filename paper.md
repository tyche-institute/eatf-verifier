---
title: 'EATF: independently verifiable evidence packages for recorded AI-agent actions'
tags:
  - research software
  - AI agents
  - digital signatures
  - remote attestation
  - reproducibility
authors:
  - name: Anton Sokolov
    orcid: 0000-0003-2452-7096
    affiliation: 1
affiliations:
  - name: Tyche Institute, Tallinn, Estonia
    index: 1
bibliography: paper.bib
date: 2 August 2026
---

# Summary

EATF is an open toolkit for creating, inspecting, and independently verifying
Agent Evidence Packages (AEPs). An AEP is a portable ZIP envelope that binds a
recorded automated action to canonical bytes, cryptographic digests,
signatures, an optional receipt, and an RFC 3161 timestamp [@rfc3161]. The
toolkit provides an offline signer and inspector, independent TypeScript and
Python verifiers, JSON Schemas, command-line interfaces, executable examples,
and positive and single-fault negative conformance vectors.

The two verifier implementations share the package contract and test vectors
but no verification code. This makes implementation disagreement observable
instead of allowing one implementation to define correctness by itself. The
same property supports research that studies failure ordering, canonicalization
boundaries, downgrade resistance, and the limits of what signed evidence can
establish.

# Statement of need

Automated systems increasingly create records that must cross organizational
and technical boundaries. A producer, deployer, auditor, standards participant,
and independent researcher may need to inspect the same record at different
times and without access to the producer's service. A dashboard or database
entry hosted by the producer does not by itself provide a portable verification
contract, and a valid signature does not establish that an action was
authorized, correctly executed, or legally compliant.

Existing standards provide important but distinct building blocks. COSE
specifies protected messages [@rfc9052]; RATS defines an architecture for
attestation evidence and appraisal [@rfc9334]; JSON Canonicalization Scheme
defines a deterministic representation for JSON data [@rfc8785]; and ML-DSA
provides a standardized post-quantum digital-signature scheme [@fips204]. EATF
does not replace these standards. It supplies a small, executable research
object for investigating how action records, receipts, timestamps, trust
anchors, and verifier decisions interact in one offline package.

EATF is intended for research in accountable automation, digital identity,
security protocol composition, and long-lived evidence. It is not a trust
service, certificate authority, policy engine, or legal-compliance
determination.

# Software design

The toolkit separates four roles that are often conflated:

1. `eatf-sign` creates a package and binds the action payload and metadata to a
   canonical representation;
2. `eatf-inspect` exposes package structure without claiming validity;
3. `eatf-verify` applies the TypeScript verification contract; and
4. `eatf-verify-py` independently applies the corresponding Python contract.

Both verifiers check required entries, canonicalization, digest binding,
optional signer-key pinning, classical signatures, optional ML-DSA-65
signatures, receipt cross-bindings, and RFC 3161 message-imprint and CMS
signatures. Each verdict reports explicit limits. For example, successful
verification without a caller-supplied signer key proves control of the
embedded private key but not the real-world identity or authority of its
holder.

The repository includes deterministic conformance and experiment harnesses.
The shared corpus contains accepted packages and packages with one deliberate
fault each. Continuous integration builds and tests the TypeScript and Python
packages, executes both conformance suites, checks packaging, and runs the
reviewer workflow on multiple operating systems. Versioned source snapshots
and test vectors are archived on Zenodo [@eatfarchive].

# Research use

EATF has been used to prepare and replay public interoperability exercises
combining protected action records, transparency-style receipts, and remote
attestation appraisal. Its independent-verifier and negative-vector structure
also supports controlled studies of first-failure behavior and verifier
disagreement. These workflows keep the software paper separate from papers
that report scientific or legal findings obtained with the toolkit.

The public repository provides installation instructions, runnable examples,
format documentation, contribution and governance policies, a security-report
route, tagged releases, and an issue tracker. Exact versions can be cited with
the Zenodo DOI and preserved with Software Heritage identifiers.

# Acknowledgements

The author thanks the open-source and standards communities responsible for the
underlying cryptographic libraries and specifications, and participants who
provided interoperability and reproducibility feedback.

# AI usage disclosure

Generative-AI coding assistants were used during software development for code
generation and refactoring suggestions, test scaffolding, documentation, and
drafting this manuscript. The author made the problem-framing and architectural
decisions and reviewed, edited, and validated the resulting code, tests, data,
and prose. Before formal submission, the author will add the exact retained
tool/model/version inventory from the project's development records; this
draft must not be submitted to JOSS with that inventory unresolved.

# References
