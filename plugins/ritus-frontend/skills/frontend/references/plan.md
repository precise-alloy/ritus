# Planning UI Acceptance

A UI task is checkable when each Acceptance line names where to look, what state to put the UI in, and what evidence
proves the result. Do not create a separate UI spec file; put the checkable contract in the task's Acceptance.

## Each UI line names the coordinates

Use this shape in the task file:

```text
[ACn] At <route or component>, viewport <width>, state <state>: <expected visible/accessibility/design result> - check:
browser at <width>, <measurement or assertion>; axe scope <scope> when accessibility is in scope.
```

Coordinates are:

- **Route or component.** Use the app route when the feature is route-level; use the component and fixture/story/state
  when the task is component-only.
- **Viewport.** Take widths from `docs/FRONTEND.md` when present. Otherwise derive them from project breakpoints and
  supported widths.
- **State.** Name loading, empty, error, disabled, long content, success, selected, open/closed, authenticated, or
  unauthenticated states when they matter to the change.

If a viewport or state is not relevant, say why in the task's non-goals or constraints. Do not let "responsive" or
"works in all states" stand without coordinates.

## Accessibility is part of changed UI

For changed controls and content, Acceptance includes:

- visible labels for fields and controls;
- accessible names that match the visible purpose;
- keyboard operation and focus order for interactive states;
- axe with the audited scope stated;
- contrast against WCAG 2.2 AA for changed text, icons that convey meaning, focus indicators, and controls.

A placeholder-only field, icon-only button, or styled div that acts like a control needs an explicit check; a snapshot or
axe result alone may miss the human-readable label.

## Design system and Figma

Acceptance names an existing component only when its role matches: same purpose, semantics, and interaction. Otherwise
it requires the project's tokens for colour, spacing, radius, and type, and rejects raw values where a token exists. If
a design exists, put the node-scoped Figma URL in the task and record the design values that matter: spacing, size,
colour, typography, radius, assets, and component mapping. Do not make later workers call Figma again for values that
task generation already read.

## The check belongs in the line

Each line says how a verifier re-runs it: browser at width W, state setup, target, and what is measured or asserted.
Use measured evidence for layout, style, contrast, and state; use a command only when the task is about a build, lint,
or test gate.

Core task generation already requires value rules to have edge examples. Keep that rule for UI values too: a formatted
amount, capped count, truncation limit, or breakpoint switch gets an example at the edge where the rule decides.

## Before writing the task file

Check the UI task's Acceptance against this list. For an item that does not apply, put the reason in the non-goals;
silence is not a reason.

- The narrowest supported width and the widest common width.
- Both sides of every documented breakpoint, one pixel apart, when the change adds or alters layout, spacing, or
  visibility.
- A WCAG 2.2 AA contrast line for each changed text, control, meaningful icon, and focus indicator.
- Visible labels, accessible names, keyboard and focus, and axe with its scope, for changed controls.
- Tokens named; a component named only where its role matches.

## Example

Good UI Acceptance for a made-up notification settings panel:

- [AC1] At `/settings/notifications`, viewport 360, loading state: the panel keeps the save button visible below the
  loading rows with no horizontal overflow - check: browser at 360px, document scroll width equals viewport width and
  the button's accessible name is `Save notification settings`.
- [AC1] At `/settings/notifications`, viewports 639 and 640: delivery options change from one column to two columns at
  the project `md` breakpoint, using `Card` and the spacing token documented in `docs/FRONTEND.md` - check: browser at
  both widths, measure option card columns and gap.
- [AC1] At `/settings/notifications`, error state: the error summary is announced before the invalid fields, each field
  has a visible label, and focus moves to the first invalid field after submit - check: keyboard submit, accessibility
  snapshot, focus target.
- [AC1] At `/settings/notifications`, viewport 1280, success state: axe reports no violations for the settings form
  scope and changed text meets WCAG 2.2 AA contrast - check: axe on `main form`, contrast measured for changed text and
  focus ring.
