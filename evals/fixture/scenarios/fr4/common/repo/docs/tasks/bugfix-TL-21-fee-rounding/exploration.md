# Exploration log - bugfix-TL-21-fee-rounding

## {{ago:40}} - debug

- [LESSONS] A refactor that moves a formula into a table can drop a rounding term; the fee tests used whole-cent fees
  and could not see it
