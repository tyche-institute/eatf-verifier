# Pilot calibration record

The first run was a calibration pilot, not the confirmatory result.

- Cases: 21
- Full oracle matches in both implementations: 18/21
- Boolean TypeScript/Python mismatches: 0
- First-failure-code mismatches: 1

Three case designs needed correction:

1. Removing `overt_receipt.sig` was intercepted by the receipt's witness
   reference before the explicit signed-receipt gate. The confirmatory operator
   removes that witness reference, re-signs the receipt with the documented
   test key, and then removes the signature entry.
2. Emptying `timestamp.tsr` was intercepted by TypeScript's stricter non-empty
   witness-reference check. The confirmatory operator removes the optional
   timestamp witness, re-signs the receipt, and then empties the timestamp.
3. Assigning `None` to the optional ASN.1 certificate field did not remove it
   from the encoded timestamp. The generator now deletes the field.

The oracle operator names were updated before the confirmatory run. Expected
states were not changed: the changes make each constructed package reach the
predeclared state instead of an earlier guard.
