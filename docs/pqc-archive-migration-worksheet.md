# PQC archive-migration worksheet

Use one copy per record class. The worksheet identifies evidence that may need
to remain verifiable after its original signer, certificate path, software
stack, or approved algorithm set has changed. It is an engineering inventory,
not legal advice, a compliance determination, or a trust-service profile.

## A. Record and horizon

| Field | Record-class answer |
|---|---|
| **1. Record class and accountable owner** | What is retained, who owns the decision, and can the record be recreated or reissued without changing its evidentiary meaning? |
| **2. Retention trigger and verification horizon** | What starts the retention period, what source sets it, and until what date could an independent party need to verify the record? Distinguish retention from the shorter or longer period during which cryptographic proof is expected. |
| **3. Signer and trust basis** | Which key signed the record? How is the signer bound to that key? Which certificate, explicit key pin, registry entry, or other trust decision must a future verifier reproduce? |
| **4. Timestamp and validation evidence** | Is there a trusted time assertion? What bytes does it cover? Which certificate path, policy, revocation data, and validation time assumptions would be needed later? |
| **5. Signature algorithm, encoding, and acceptance policy** | Record the algorithm and parameters, wire encoding or OID, hybrid composition rule, and the relying party's policy for classical-only transition evidence. Avoid a single value such as “PQC supported.” |
| **6. Preserved verification capability** | Name the independent verifier, version, runtime, dependencies, schemas, positive vector, negative controls, expected first-failure codes, and the location of an offline replay bundle. |
| **7. Renewal, revalidation, and disposition action** | Choose and date the action: bounded classical acceptance; hybrid signing for new records; preservation plus evidence renewal; migration to a new container; or documented expiry and disposal. Name the trigger and owner. |

## B. Decision sequence

1. **Can the record be recreated later without changing what it proves?** If
   yes, document the controlled reissue path. If no, treat it as archive
   evidence.
2. **Does the expected verification horizon outlive any signing algorithm,
   key, certificate, timestamp path, dependency, or policy assumption?** If
   yes or unknown, record a migration action rather than a generic support
   claim.
3. **For new records, is classical-only evidence still permitted?** State the
   end condition. If PQC is required, make that a relying-party verification
   policy and test a legitimately generated classical-only package.
4. **Can an independent implementation verify a positive package?** Preserve
   at least one positive cross-implementation vector before relying on the
   format.
5. **Do negative controls reach the intended decision points?** Include
   signature tamper, incomplete hybrid pair, structural stripping, payload
   change, and any encoding or trust-basis boundary that matters.
6. **Can the evidence be replayed offline on a clean machine?** Preserve the
   package, hashes, expected outputs, verifier source or binaries, dependency
   lock files, and a short operator procedure.

## C. Recorded outcome

| Decision | Entry |
|---|---|
| Current acceptance policy | `classical allowed until: ____` / `hybrid if present` / `PQC required` |
| Next migration or renewal event | Trigger/date: ____  Owner: ____ |
| Preserved replay bundle | Location/version/DOI: ____ |
| Last independent replay | Date: ____  Implementations: ____  Result: ____ |
| Residual limitation accepted by | Name/role: ____  Date: ____ |

**Review rule:** revisit the worksheet when the record class, retention source,
algorithm policy, trust basis, verifier dependency, or archive process changes.
