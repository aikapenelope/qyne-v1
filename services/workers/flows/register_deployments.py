"""
QYNE v1 — Register all Prefect deployments.

Run inside the Prefect worker container:
  docker exec -e PREFECT_API_URL=http://prefect:4200/api \
    qyne-prefect-worker python /app/flows/register_deployments.py

This creates/updates deployments with schedules in the Prefect server.
The worker picks them up automatically from default-pool.
"""

from prefect.runner import serve


def register():
    from flows.property_pipeline import property_pipeline
    from flows.selector_health_check import selector_health_check
    from flows.website_crawler import website_crawler
    from flows.etl_documents import etl_documents
    from flows.database_backup import database_backup
    from flows.health_check import health_check
    from flows.email_digest import daily_digest
    from flows.report_generator import weekly_report
    from flows.data_cleanup import data_cleanup
    from flows.data_enricher import data_enricher
    from flows.data_sync import data_sync
    from flows.lead_scorer import lead_scorer
    from flows.sentiment_analyzer import sentiment_analyzer
    from flows.knowledge_indexer import knowledge_indexer
    from flows.export_csv import export_csv
    from flows.import_csv import import_csv
    from flows.dedup_merger import dedup_merger

    deployments = [
        # --- Property pipelines (per site, staggered) ---
        property_pipeline.to_deployment(
            name="property-rentahouse-daily",
            cron="0 4 * * *",
            parameters={"sites": ["rentahouse_ve"], "max_pages": 1, "download_images": False},
        ),
        property_pipeline.to_deployment(
            name="property-century21-daily",
            cron="0 5 * * *",
            parameters={"sites": ["century21_ve"], "max_pages": 1, "download_images": False},
        ),
        property_pipeline.to_deployment(
            name="property-all-weekly",
            cron="0 2 * * 6",  # Saturday 2am
            parameters={"sites": None, "max_pages": 5, "download_images": False},
        ),

        # --- Monitoring ---
        selector_health_check.to_deployment(
            name="selector-health-weekly",
            cron="0 3 * * 0",  # Sunday 3am
            parameters={"check_urls": True, "url_sample": 100},
        ),
        health_check.to_deployment(
            name="health-check-30min",
            cron="*/30 * * * *",
            parameters={},
        ),

        # --- On-demand flows (no schedule, trigger from chat) ---
        website_crawler.to_deployment(
            name="website-crawler-ondemand",
            parameters={"url": "", "max_pages": 20, "index_in_knowledge": False},
        ),
        etl_documents.to_deployment(
            name="etl-documents-on-demand",
            parameters={"file_paths": [], "collection": "documents"},
        ),
        knowledge_indexer.to_deployment(
            name="knowledge-indexer-ondemand",
            parameters={},
        ),
        export_csv.to_deployment(
            name="export-csv-ondemand",
            parameters={"collection": "contacts", "fields": "*", "bucket": "exports"},
        ),
        import_csv.to_deployment(
            name="import-csv-ondemand",
            parameters={"file_path": "", "collection": "contacts"},
        ),
        dedup_merger.to_deployment(
            name="dedup-merger-ondemand",
            parameters={},
        ),

        # --- Scheduled flows (activate when ready) ---
        database_backup.to_deployment(
            name="backup-daily-3am",
            cron="0 3 * * *",
            parameters={"databases": ["directus_db", "prefect_db"], "bucket": "backups"},
        ),
        daily_digest.to_deployment(
            name="daily-digest-8am",
            cron="0 8 * * *",
            parameters={},
        ),
        weekly_report.to_deployment(
            name="weekly-report-mon8am",
            cron="0 8 * * 1",
            parameters={},
        ),
        data_cleanup.to_deployment(
            name="data-cleanup-sun2am",
            cron="0 2 * * 0",
            parameters={},
        ),
        data_enricher.to_deployment(
            name="data-enricher-daily",
            cron="0 5 * * *",
            parameters={},
        ),
        data_sync.to_deployment(
            name="data-sync-hourly",
            cron="0 * * * *",
            parameters={"source_collection": "", "target_collection": "", "field_map": {}},
        ),
        lead_scorer.to_deployment(
            name="lead-scorer-daily6am",
            cron="0 6 * * *",
            parameters={},
        ),
        sentiment_analyzer.to_deployment(
            name="sentiment-daily",
            cron="0 7 * * *",
            parameters={},
        ),
    ]

    print(f"Registering {len(deployments)} deployments...")
    serve(*deployments)


if __name__ == "__main__":
    register()
