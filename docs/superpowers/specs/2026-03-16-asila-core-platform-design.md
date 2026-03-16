# Asila Core Platform: Design Specification
**Date:** March 16, 2026
**Topic:** Core Architecture, Multi-Tenancy, and RAG Pipeline

## 1. Executive Summary
Asila is a "Verified Information Hub" designed for local and state governments to proactively communicate with citizens via WhatsApp. It replaces fragmented social media updates with a centralized, reliable system that reduces bureaucratic load. The platform offers a dual-channel experience: one-way targeted broadcasts for official notices and a two-way AI-powered chat for citizen inquiries.

**Core Principles:**
- **Reliable Tech:** Prioritize robust, low-maintenance technology over bleeding-edge complexity.
- **Data Sovereignty & Isolation:** Absolute separation of tenant data with zero vendor lock-in.
- **Trust & Verification:** "Pure RAG" where the AI only answers based on verified government documents, providing explicit citations.

## 2. Architecture: The "Modular Monolith" with Physical Isolation
To balance SaaS manageability with government-grade security, Asila employs a Modular Monolith backend paired with a "Database-per-Tenant" storage model. This fully replaces any previous concepts of logical isolation via Row Level Security (RLS) in favor of strict physical isolation.

### Components
1. **The Control Plane (FastAPI):**
   - A central API server handling routing, orchestration, and business logic.
   - **Central Meta-DB:** A master PostgreSQL database storing tenant metadata (e.g., Council Name, Subscription, DB Connection String).
2. **The Tenant Factory:**
   - Automated provisioning system. When a new council is onboarded, the system executes `CREATE DATABASE [tenant] TEMPLATE asila_schema_template;` to instantly spin up a perfectly structured, isolated database.
3. **The Tenant DBs (PostgreSQL + PostGIS + pgvector):**
   - Each council has a dedicated database containing their specific `Users`, `Notices`, `Embeddings` (vector data), `Queries`, and `Broadcasts`.
4. **Auth0 Integration:**
   - Single dashboard login (`dashboard.asila.gov`).
   - Uses **Auth0 Organizations** to map users to their respective tenants. The JWT token will contain an `org_id` which the Control Plane matches against the Central Meta-DB to dynamically route queries to the correct Tenant DB.
5. **Database Migrations:**
   - Migrations are managed centrally using Alembic. A custom migration script will iterate through all active tenant connection strings in the Central Meta-DB, applying schema changes sequentially to ensure all Tenant DBs stay in sync with the `asila_schema_template`.

## 3. The "Truth Engine": Hybrid RAG Pipeline
To handle verbose, complex government documents, Asila uses a comprehensive indexing and retrieval pipeline.

### Document Ingestion (The Enrichment Layer)
1. **Upload & Parse:** Raw PDFs/DOCX are processed to preserve hierarchical structure (headings, tables, bullet points).
2. **Semantic Section Chunking:** Documents are split based on logical sections (e.g., 300-700 tokens per logical rule).
3. **AI Bridge Enrichment (Gemini):**
   - *Synthetic Questions:* Generates 3-5 possible citizen questions for the chunk.
   - *Entity Extraction:* Extracts hard data (Dates, Wards, Fines).
   - *Structured Summary:* Creates a citizen-friendly summary of the chunk.
4. **Embedding:** The enriched chunks (and synthetic questions) are converted to vectors and stored in the Tenant DB via `pgvector`.

### Citizen Query (Hybrid Retrieval)
1. **Metadata Filtering:** Before searching text, the system filters by known entities (e.g., specific Ward or Department).
2. **Hybrid Search:** Combines vector similarity (`pgvector` cosine similarity) with lexical/keyword search (using PostgreSQL `tsvector` and `tsquery` full-text search) to ensure exact terms (e.g., permit numbers) are not missed.
3. **Reranking:** The top 10 results are re-evaluated to find the best 3-5 chunks.
4. **Grounded Generation:** The AI Bridge (Gemini) generates an answer strictly from the provided chunks. If the answer is missing, it explicitly states so.
5. **Citations:** Every response includes the source title and section (e.g., *"Based on the 2024 Water Plan, Section 2..."*).

## 4. WhatsApp Engine & Twilio Integration
A single WhatsApp Business number per council provides a seamless user experience.

### The Dual-Channel System
1. **Broadcast Channel (One-Way):** Council admins send targeted template messages (e.g., *"⚠️ Water Outage..."*) to specific groups.
2. **Chat Channel (Two-Way):** Citizens can reply to broadcasts or ask new questions, triggering the RAG engine.

### Smart Geo-Onboarding & Targeting
1. **Frictionless Signup:** When a citizen messages the bot, they are prompted to provide their location via:
   - **WhatsApp Location Pin:** Resolved against Ward boundaries using PostgreSQL `PostGIS`.
   - **Landmark Text:** Processed by the AI Bridge to guess the corresponding Ward.
2. **Geo-Guess Validation:** If the user provides Landmark Text, the AI responds with a confirmation (e.g., *"It looks like you're in Ward 4. Is that correct? (Yes/No)"*). The location is only saved upon user confirmation.
3. **Ward Definition:** Admins define Wards in the dashboard by drawing polygons on a Google Maps interface, avoiding the need for complex GIS uploads.
4. **Geo-Targeted Broadcasts:** Admins can select specific Wards for targeted messaging, reducing "spam" for unaffected citizens.

### Conversation Memory
- **Redis (Fast Context):** Stores the last 5-15 minutes of a conversation to resolve pronouns and contextual follow-ups (e.g., *"When will it be fixed?"*).
- **PostgreSQL (Audit Archive):** The full interaction is saved to the `queries` table for compliance and analytics.

## 5. Analytics & The Decision Hub
The dashboard provides actionable insights derived from the interaction archive:
1. **Topic Map:** AI-summarized themes of current citizen inquiries (e.g., "80% of Ward 4 is asking about water outages").
2. **Service Efficiency (ROI):** Tracks resolved interactions (where the citizen indicates satisfaction), calculating the number of manual support calls prevented.
3. **Broadcast Heatmap:** A visual representation of subscriber density and alert frequency across the council's jurisdiction.

## 6. Data Portability & Sovereignty
To eliminate vendor lock-in, Asila provides robust data export features directly tied to the isolated Tenant DBs:
1. **One-Click Export:** Full `.sql` or `.csv` dumps of all tenant data.
2. **Real-Time Webhooks:** Forwarding live interactions (Query + AI Answer) to internal council CRMs or issue trackers.
3. **Direct Read-Only DB Access:** Secure connection strings provided for internal IT teams to plug into Power BI/Tableau.

## 7. The AI Bridge Pattern
To maintain flexibility, all AI operations (embedding, synthesis, generation) interface through an abstract `IntelligenceService`. While currently powered by Google Gemini, this design allows the underlying LLM provider to be swapped (e.g., to a local model for strict compliance) without altering core business logic.
