Please work on this ticket:

TL-33 - Say which command was not recognized

When support staff mistype a command (`tl tranfer alice bob 10.50`), tl prints the usage text and exits 1, with no
hint of what went wrong.

Acceptance criteria:

1. `tl tranfer alice bob 10.50` prints `Unknown command: tranfer` on the first line, then the usage text, and exits 1.
2. `tl` with no command prints the usage text as today, with no "Unknown command" line, and exits 1.
3. Known commands behave exactly as before.
