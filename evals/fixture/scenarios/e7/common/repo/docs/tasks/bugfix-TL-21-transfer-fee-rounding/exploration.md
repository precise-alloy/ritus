# Exploration Log - bugfix-TL-21-transfer-fee-rounding

## {{ago:25}} - triage

- [NONE] TL-21: `tl transfer alice bob 10.50` charges a $0.10 fee; D-002 says 10.5 cents rounds half-up to 11 cents
- [NONE] The transfer fee comes from `computeFee(amountCents, 'transfer')` (src/transfer.js:9)
