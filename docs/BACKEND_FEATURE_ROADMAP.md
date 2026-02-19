# BidBoard Backend Feature Roadmap

## Goal
Make BidBoard production-grade for high-scale multi-organization recruitment with stronger reliability, automation, and decision support.

## Phase 1 (Immediate, Highest Impact)

### 1. Event and Workflow Engine
- Build first-class `events` + `event_attendance` tables (not just lunches).
- Add event types: `lunch`, `rush_event`, `meeting`, `follow_up`.
- Add RSVP + attendance status (`planned`, `attended`, `no_show`).
- Expose a unified calendar API with filtering by role, member, PNM, and event type.
- Why: gives one source of truth for all recruiting activity and fixes calendar fragmentation.

### 2. Assignment Orchestration and Capacity Controls
- Add assignment states: `unassigned`, `assigned`, `in_progress`, `completed`, `needs_help`.
- Add assignment load balancing based on officer capacity and active PNM count.
- Add overdue assignment alerts and escalation rules to head rush officers.
- Why: prevents silent assignment failures and uneven workload.

### 3. Notification Center (Server-Side)
- Add `notifications` table + delivery channel abstraction.
- Trigger events for: pending approvals, assignment changes, meeting prep windows, no recent touchpoints.
- Add digest endpoints (`daily`, `weekly`) and read/unread state.
- Why: keeps officers active without requiring manual dashboard checks.

### 4. Data Reliability Hardening
- Move from ad-hoc schema evolution to versioned migrations (Alembic or equivalent).
- Add startup validation for all tenant schemas and indexes.
- Add scheduled backup verification job (test restore into temp DB).
- Why: prevents drift and ensures recoverability.

## Phase 2 (Decision Quality + Scale)

### 5. Recruitment Funnel Pipeline
- Add stage tracking table: `sourced -> engaged -> evaluated -> discussed -> bid -> accepted/declined`.
- Track stage transitions with actor, timestamp, and reason code.
- Add stage conversion analytics endpoint.
- Why: gives objective funnel visibility and bottleneck detection.

### 6. Rating Intelligence and Bias Guardrails
- Add per-rater normalization metrics (score inflation/deflation index).
- Add confidence score based on number of interactions and rating variance.
- Add outlier alerts (large delta updates, rating conflicts).
- Why: improves fairness and decision quality in chapter meetings.

### 7. Advanced Audit Ledger
- Create append-only `audit_ledger` table for critical actions:
  - user approvals/disapprovals
  - rating changes
  - assignment changes
  - archive/reset operations
- Add tamper-evident hash chain per tenant (optional but recommended).
- Why: stronger accountability and trust for high-stakes decisions.

### 8. API Performance and Tenant Isolation
- Add request-level tenant context middleware hard checks.
- Add indexes for hot paths (`ratings`, `pnms`, `events`, `assignments`).
- Add response caching for read-heavy dashboards (`analytics overview`, `leaderboard`).
- Why: faster UI and safer multi-tenant behavior.

## Phase 3 (Enterprise + Growth)

### 9. SSO, MFA, and Security Policy Controls
- Add optional SSO (Google/Microsoft OIDC) per organization.
- Add required MFA policy for head/admin roles.
- Add organization-level session policy (idle timeout, max session age).
- Why: improves security posture for larger orgs and universities.

### 10. Integration Framework
- Add integration service abstraction + credentials vault table.
- First connectors:
  - Google Calendar (service account + org-scoped sync)
  - Slack/Discord webhook notifications
  - Twilio SMS reminders
- Why: lets BidBoard orchestrate communication, not just store data.

### 11. Predictive Insights Layer
- Add feature store table from interactions, attendance, trend velocity, and comments.
- Add model endpoint to predict fit probability and risk flags.
- Show explainability fields in meeting packet (`top factors`).
- Why: gives head rush teams better prioritization signals.

### 12. Seasonal Archives and Cross-Season Analytics
- Store immutable season snapshots with lineage metadata.
- Add cross-season benchmarks: conversion rates, engagement intensity, acceptance quality.
- Why: enables long-term learning and playbook optimization.

## Technical Foundations to Add Alongside Phases

### Testing and Quality
- Contract tests for all role-restricted endpoints.
- Multi-tenant isolation test suite (negative tests required).
- Seed fixtures for realistic chapter sizes (50, 150, 300 PNM seasons).

### Observability
- Structured logs with request ids and tenant ids.
- Metrics: p95 latency, error rate by endpoint, DB query time, queue lag.
- Alerting on auth failures, backup failures, and migration errors.

### Job System
- Add background queue for notifications, digest generation, backup verification, and sync tasks.
- Include idempotency keys for external integration jobs.

## Suggested Build Order (Practical)
1. Event/workflow engine + assignment orchestration
2. Notification center + reliability hardening
3. Funnel + rating intelligence + audit ledger
4. SSO/MFA + integration framework
5. Predictive insights + cross-season analytics

## Stretch Ideas
- Offline-first mobile sync with conflict resolution.
- Voice-note ingestion and auto-summary for PNM notes.
- Smart assignment recommender using shared interest + conversation outcomes.
- Scenario simulator for meeting decisions ("if we bid top 20, projected acceptance range").
