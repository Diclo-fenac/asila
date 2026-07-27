# Security Policy

## Supported Versions

Currently, only the latest release of Asila is supported with security updates. 

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within Asila, please DO NOT open a public issue. 
Instead, report it confidentially via email to `security@asila.dev` (or the appropriate organization email).

Please include:
- A description of the vulnerability.
- Steps to reproduce the issue.
- Potential impact (e.g., cross-tenant leakage, auth bypass).

We will attempt to respond to your report within 48 hours and work with you to patch the vulnerability before public disclosure.

## Threat Model

Asila relies heavily on **PostgreSQL Row-Level Security (RLS)** for tenant isolation. Any vulnerability that allows a user to bypass RLS or execute arbitrary SQL is considered a **P0 / Critical** issue. 
Local document parsing (Docling) and embedding generation (Ollama) run in isolated containers to prevent host-level compromise, but vulnerabilities leading to RCE in these components should also be reported immediately.
