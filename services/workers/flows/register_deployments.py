"""
QYNE v1 — Register all Prefect deployments.

Run inside the Prefect worker container:
  docker exec qyne-prefect-worker python /app/flows/register_deployments.py

This creates deployments with schedules in the Prefect server.
The worker picks them up automatically.
"""

import asyncio

from prefect.client.orchestration import get_client
from prefect.client.schemas.schedules import CronSchedule


async def register():
    async with get_client() as client:
        # Import flows
        from flows.scraper_latam import scraper_latam
        from flows.etl_documents import etl_documents
        from flows.database_backup import database_backup

        deployments = [
            {
                "flow": scraper_latam,
                "name": "scraper-latam-6h",
                "schedule": CronSchedule(cron="0 */6 * * *"),
                "parameters": {"urls": [], "collection": "scraped_data"},
            },
            {
                "flow": etl_documents,
                "name": "etl-documents-on-demand",
                "schedule": None,
                "parameters": {"file_paths": [], "collection": "documents"},
            },
            {
                "flow": database_backup,
                "name": "backup-daily-3am",
                "schedule": CronSchedule(cron="0 3 * * *"),
                "parameters": {"databases": ["directus_db", "prefect_db"], "bucket": "backups"},
            },
        ]

        for d in deployments:
            flow_id = d["flow"].to_deployment(
                name=d["name"],
                schedule=d["schedule"],
                parameters=d["parameters"],
            )
            print(f"  Registered: {d['name']}")

        # Use serve to register all at once
        print("\nRegistering deployments...")
        await scraper_latam.to_deployment(
            name="scraper-latam-6h",
            cron="0 */6 * * *",
            parameters={"urls": [], "collection": "scraped_data"},
        ).apply()

        await etl_documents.to_deployment(
            name="etl-documents-on-demand",
            parameters={"file_paths": [], "collection": "documents"},
        ).apply()

        await database_backup.to_deployment(
            name="backup-daily-3am",
            cron="0 3 * * *",
            parameters={"databases": ["directus_db", "prefect_db"], "bucket": "backups"},
        ).apply()

        print("All deployments registered!")


if __name__ == "__main__":
    asyncio.run(register())
