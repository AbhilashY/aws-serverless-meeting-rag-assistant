import json
import os
from typing import Any, Dict

import boto3


bedrock_agent_client = boto3.client("bedrock-agent")


def _start_ingestion_job() -> Dict[str, Any]:
    knowledge_base_id = os.getenv("BEDROCK_KB_ID")
    data_source_id = os.getenv("BEDROCK_DATA_SOURCE_ID")

    if not knowledge_base_id:
        raise ValueError("BEDROCK_KB_ID is not configured")

    if not data_source_id:
        raise ValueError("BEDROCK_DATA_SOURCE_ID is not configured")

    response = bedrock_agent_client.start_ingestion_job(
        knowledgeBaseId=knowledge_base_id,
        dataSourceId=data_source_id,
        description="Triggered by new Zoom transcript uploaded to S3",
    )

    return response


def lambda_handler(
    event: Dict[str, Any],
    context: Any,
) -> Dict[str, Any]:
    """
    React to new Zoom transcript uploads in S3 and trigger
    Amazon Bedrock Knowledge Base ingestion.
    """

    try:
        records = event.get("Records", [])

        if not records:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "No S3 records found"
                    }
                ),
            }

        processed_objects = []

        for record in records:
            bucket_name = (
                record["s3"]["bucket"]["name"]
            )

            object_key = (
                record["s3"]["object"]["key"]
            )

            if not object_key.endswith(".vtt"):
                continue

            if not object_key.startswith(
                "transcripts/raw/"
            ):
                continue

            processed_objects.append(
                {
                    "bucket": bucket_name,
                    "key": object_key,
                }
            )

        if not processed_objects:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": (
                            "No eligible VTT transcript "
                            "objects found"
                        )
                    }
                ),
            }

        ingestion_response = (
            _start_ingestion_job()
        )

        ingestion_job = (
            ingestion_response.get(
                "ingestionJob",
                {},
            )
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": (
                        "Bedrock Knowledge Base "
                        "ingestion started"
                    ),
                    "objects": processed_objects,
                    "ingestion_job_id": (
                        ingestion_job.get(
                            "ingestionJobId"
                        )
                    ),
                    "status": (
                        ingestion_job.get(
                            "status"
                        )
                    ),
                }
            ),
        }

    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "type": type(exc).__name__,
                }
            )
        )

        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": (
                        "Failed to start "
                        "Bedrock ingestion job"
                    )
                }
            ),
        }
