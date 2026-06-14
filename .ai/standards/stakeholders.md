# Stakeholders

> Project-specific ownership and escalation guidance. Fill this file during setup or project adoption.

## Business / Customer Side

| Name                            | Contact                            | Role                 | Authority                                                                           |
|---------------------------------|------------------------------------|----------------------|-------------------------------------------------------------------------------------|
| `{{PRODUCT_OWNER_NAME}}`        | `{{PRODUCT_OWNER_CONTACT}}`        | Product Owner        | Can confirm requirements, acceptance criteria, priorities, and business assumptions |
| `{{BUSINESS_STAKEHOLDER_NAME}}` | `{{BUSINESS_STAKEHOLDER_CONTACT}}` | Business Stakeholder | Can confirm domain rules and business process details                               |

## External Systems / Integrations

| Name                         | Contact                         | System / Area                 | Authority                                                                                    |
|------------------------------|---------------------------------|-------------------------------|----------------------------------------------------------------------------------------------|
| `{{INTEGRATION_OWNER_NAME}}` | `{{INTEGRATION_OWNER_CONTACT}}` | `{{INTEGRATION_SYSTEM_NAME}}` | Can confirm fields, statuses, API behavior, credentials process, and integration constraints |

## Development Team

| Name                       | Contact                       | Role                  | Authority                                                                   |
|----------------------------|-------------------------------|-----------------------|-----------------------------------------------------------------------------|
| `{{TECH_LEAD_NAME}}`       | `{{TECH_LEAD_CONTACT}}`       | Tech Lead / Architect | Can confirm architecture, implementation strategy, and technical trade-offs |
| `{{PROJECT_MANAGER_NAME}}` | `{{PROJECT_MANAGER_CONTACT}}` | Project Manager       | Can confirm delivery priority, sequencing, and coordination questions       |
| `{{BACKEND_OWNER_NAME}}`   | `{{BACKEND_OWNER_CONTACT}}`   | Backend Owner         | Can confirm backend implementation details                                  |
| `{{FRONTEND_OWNER_NAME}}`  | `{{FRONTEND_OWNER_CONTACT}}`  | Frontend Owner        | Can confirm UI/frontend implementation details                              |
| `{{QA_OWNER_NAME}}`        | `{{QA_OWNER_CONTACT}}`        | QA Owner              | Can confirm QA scenarios, test data, and regression scope                   |

## Escalation Guide

- **Requirements / acceptance criteria unclear** -> escalate to `{{PRODUCT_OWNER_NAME}}`.
- **Domain rules unclear** -> ask `{{BUSINESS_STAKEHOLDER_NAME}}`.
- **External system fields, statuses, API behavior, or credentials** -> ask `{{INTEGRATION_OWNER_NAME}}`.
- **Architecture / implementation decisions** -> confirm with `{{TECH_LEAD_NAME}}`.
- **Delivery priority / sequencing** -> coordinate with `{{PROJECT_MANAGER_NAME}}`.
- **QA scenarios / test data** -> coordinate with `{{QA_OWNER_NAME}}`.

## Usage Rules

- Ask one clear question at a time.
- Distinguish blocking questions from nice-to-have clarifications.
- Record confirmed answers in the relevant review, task, or decision document.
