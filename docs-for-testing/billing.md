# Billing & Subscription Logic

## Invoices
Invoices are generated monthly.
**Invariant:** Once an invoice status is set to `PAID`, it **cannot** be modified.

## Subscription Tiers
1.  **Free:** Max 5 projects.
2.  **Pro:** Unlimited projects.
3.  **Enterprise:** Access to Audit Logs and SSO.

## Configuration
*   `ALLOW_OFFLINE_PAYMENTS`: If set to `true`, users can pay via check.
