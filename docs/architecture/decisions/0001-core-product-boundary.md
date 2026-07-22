# ADR 0001: Core Product Boundary

**Status:** Accepted

Asila core is an open-source, self-hostable knowledge platform. Its stable core includes organizations, memberships, API keys, provider configuration, text ingestion, indexing, retrieval, citations, REST, CLI, SDK-compatible APIs, and MCP search/retrieval.

Government workflows, WhatsApp, Twilio, broadcasts, geospatial targeting, citizen messaging, graph extraction, repository synchronization, and provider-specific connectors are extensions or follow-up capabilities. They must not add domain models or dependencies to the core platform.

The first-run experience is API/CLI-first. A dashboard is optional and is not a prerequisite for setup or use.
