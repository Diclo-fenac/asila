"""Ingestion retry fencing, stale recovery, lease ownership, and deletion lifecycle.

Revision ID: 0007_ingestion_retry_and_fencing
Revises: 0006_isolated_extraction
Create Date: 2026-10-19
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0007_ingestion_retry_and_fencing"
down_revision: str = "0006_isolated_extraction"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add lease ownership and fencing columns
    op.add_column(
        "ingestion_jobs",
        sa.Column("lease_id", sa.String(128), nullable=True),
        schema="app",
    )
    op.add_column(
        "ingestion_jobs",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        schema="app",
    )
    op.add_column(
        "ingestion_jobs",
        sa.Column("worker_id", sa.String(128), nullable=True),
        schema="app",
    )

    # 2. Queue performance index for polling and stale-lease recovery
    op.create_index(
        "ix_ingestion_jobs_queue_lease",
        "ingestion_jobs",
        ["status", "available_at", "attempts", "lease_expires_at"],
        schema="app",
    )

    # 3. Reconcile RLS on app.ingestion_jobs
    # Allow dispatcher role/context to see queued and stale jobs across tenants
    op.execute(
        "DROP POLICY IF EXISTS ingestion_jobs_organization_isolation ON app.ingestion_jobs"
    )
    op.execute(
        """
        CREATE POLICY ingestion_jobs_organization_isolation ON app.ingestion_jobs
        USING (
            organization_id = current_setting('app.organization_id', true)
            OR current_setting('app.job_dispatcher', true) = 'true'
        )
        WITH CHECK (
            organization_id = current_setting('app.organization_id', true)
            OR current_setting('app.job_dispatcher', true) = 'true'
        )
        """
    )

    # 4. Narrowly granted transactional claim routine with fixed search_path
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.claim_next_ingestion_job(
            p_worker_id text,
            p_lease_seconds integer DEFAULT 300
        )
        RETURNS TABLE (
            id text,
            organization_id text,
            document_id text,
            operation text,
            payload_json json,
            attempts integer,
            lease_id text,
            lease_expires_at timestamptz
        )
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = app, pg_catalog, pg_temp
        AS $$
        DECLARE
            v_job_id text;
            v_new_lease text;
            v_expires timestamptz;
        BEGIN
            -- Activate dispatcher flag within this security definer function
            PERFORM set_config('app.job_dispatcher', 'true', true);

            -- Automatically terminate exhausted jobs
            UPDATE app.ingestion_jobs
            SET status = 'failed',
                last_error = 'MAX_ATTEMPTS_EXCEEDED',
                completed_at = clock_timestamp(),
                updated_at = clock_timestamp()
            WHERE attempts >= 5 AND status IN ('queued', 'processing')
              AND (lease_expires_at IS NULL OR lease_expires_at < clock_timestamp());

            -- Select next eligible job with SKIP LOCKED
            -- 1. status = 'queued' AND (available_at IS NULL OR available_at <= now()) AND attempts < 5
            -- 2. status = 'processing' AND lease_expires_at < now() AND attempts < 5 (stale recovery)
            SELECT j.id INTO v_job_id
            FROM app.ingestion_jobs j
            WHERE (
                (j.status = 'queued' AND (j.available_at IS NULL OR j.available_at <= clock_timestamp()))
                OR
                (j.status = 'processing' AND j.lease_expires_at IS NOT NULL AND j.lease_expires_at < clock_timestamp())
            )
            AND j.attempts < 5
            ORDER BY j.created_at ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1;

            IF v_job_id IS NULL THEN
                RETURN;
            END IF;

            v_new_lease := 'lease_' || md5(random()::text || clock_timestamp()::text || v_job_id);
            v_expires := clock_timestamp() + (p_lease_seconds || ' seconds')::interval;

            RETURN QUERY
            UPDATE app.ingestion_jobs
            SET status = 'processing',
                attempts = ingestion_jobs.attempts + 1,
                started_at = clock_timestamp(),
                updated_at = clock_timestamp(),
                worker_id = p_worker_id,
                lease_id = v_new_lease,
                lease_expires_at = v_expires
            WHERE ingestion_jobs.id = v_job_id
            RETURNING
                ingestion_jobs.id::text,
                ingestion_jobs.organization_id::text,
                ingestion_jobs.document_id::text,
                ingestion_jobs.operation::text,
                ingestion_jobs.payload_json,
                ingestion_jobs.attempts,
                ingestion_jobs.lease_id::text,
                ingestion_jobs.lease_expires_at;
        END;
        $$;
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION app.claim_next_ingestion_job(text, integer) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION app.claim_next_ingestion_job(text, integer) TO asila_app"
    )


def downgrade():
    op.execute(
        "DROP FUNCTION IF EXISTS app.claim_next_ingestion_job(text, integer)"
    )
    op.drop_index("ix_ingestion_jobs_queue_lease", table_name="ingestion_jobs", schema="app")
    op.execute(
        "DROP POLICY IF EXISTS ingestion_jobs_organization_isolation ON app.ingestion_jobs"
    )
    op.execute(
        """
        CREATE POLICY ingestion_jobs_organization_isolation ON app.ingestion_jobs
        USING (organization_id = current_setting('app.organization_id', true))
        WITH CHECK (organization_id = current_setting('app.organization_id', true))
        """
    )
    op.drop_column("ingestion_jobs", "worker_id", schema="app")
    op.drop_column("ingestion_jobs", "lease_expires_at", schema="app")
    op.drop_column("ingestion_jobs", "lease_id", schema="app")
