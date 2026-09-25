# Mortgage servicing industry pack

Regulated flow: greeter → verification → payment / loan_info + human escalation.

Attach loan-servicing MCP and set `CUSTOMER_LOS_API_KEY`. Payment flow FSM enforces
collect → confirm → `make_payment`.
