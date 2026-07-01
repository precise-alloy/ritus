# Stakeholders

> Project-specific ownership and escalation guidance. Fill during setup or project adoption.
> Referenced by `ticket-review` (clarifying questions) and `pr-review` (ownership + escalation).

## Business / Customer Side

| Name | Contact | Role | Authority |
|------|---------|------|-----------|
| | | Product Owner | Confirms requirements, acceptance criteria, priorities, business assumptions |
| | | Business Stakeholder | Confirms domain rules and business process details |

## External Systems / Integrations

| Name | Contact | System / Area | Authority |
|------|---------|---------------|-----------|
| | | | Confirms fields, statuses, API behavior, credentials, integration constraints |

## Development Team

| Name | Contact | Role | Authority |
|------|---------|------|-----------|
| | | Tech Lead / Architect | Confirms architecture, implementation strategy, technical trade-offs |
| | | Project Manager | Confirms delivery priority, sequencing, coordination |
| | | Backend Owner | Confirms backend implementation details |
| | | Frontend Owner | Confirms UI/frontend implementation details |
| | | QA Owner | Confirms QA scenarios, test data, regression scope |

## Escalation Guide

- **Requirements / acceptance criteria unclear** → escalate to Product Owner
- **Domain rules unclear** → ask Business Stakeholder
- **External system fields, statuses, API behavior** → ask Integration Owner
- **Architecture / implementation decisions** → confirm with Tech Lead
- **Delivery priority / sequencing** → coordinate with Project Manager
- **QA scenarios / test data** → coordinate with QA Owner
