import json
import os
from typing import Any, Dict, List
from urllib.parse import unquote_plus

import boto3


s3_client = boto3.client("s3")
bedrock_agent_client = boto3.client("bedrock-agent")


def _read_s3_object(bucket: str, key: str) -> str:
    response = s3_client.get_object(
        Bucket=bucket,
        Key=key,
    )

    return response["Body"].read().decode("utf-8")


def _parse_vtt(vtt_text: str) -> List[Dict[str, str]]:
    lines = [
        line.strip()
        for line in vtt_text.splitlines()
        if line.strip()
    ]

    entries: List[Dict[str, str]] = []
    current: Dict[str, str] = {}

    for line in lines:
        if line.startswith("WEBVTT"):
            continue

        if "-->" in line:
            if current:
                entries.append(current)

            current = {
                "timestamp": line
            }
            continue

        if line.startswith("<v "):
            speaker = (
                line[3:]
                .split(">", 1)[0]
                .strip()
            )

            text = (
                line.split(">", 1)[1].strip()
                if ">" in line
                else ""
            )

            current["speaker"] = speaker
            current["content"] = text
            continue

        if current:
            previous = current.get(
                "content",
                "",
            )

            current["content"] = (
                f"{previous} {line}".strip()
            )

    if current:
        entries.append(current)

    return entries


def _build_clean_transcript(
    entries: List[Dict[str, str]],
) -> str:

    output = []

    for entry in entries:
        timestamp = entry.get(
            "timestamp",
            "",
        )

        speaker = entry.get(
            "speaker",
            "Unknown Speaker",
        )

        content = entry.get(
            "content",
            "",
        )

        output.append(
            f"Timestamp: {timestamp}\n"
            f"Speaker: {speaker}\n"
            f"{content}\n"
        )

    return "\n".join(output)


def _save_processed_transcript(
    bucket: str,
    raw_key: str,
    content: str,
) -> str:

    filename = (
        raw_key
        .split("/")[-1]
        .rsplit(".", 1)[0]
    )

    processed_key = (
        f"transcripts/processed/"
        f"{filename}.txt"
    )

    s3_client.put_object(
        Bucket=bucket,
        Key=processed_key,
        Body=content.encode("utf-8"),
        ContentType="text/plain",
    )

    return processed_key


def _start_ingestion_job() -> Dict[str, Any]:
    knowledge_base_id = os.getenv(
        "BEDROCK_KB_ID"
    )

    data_source_id = os.getenv(
        "BEDROCK_DATA_SOURCE_ID"
    )

    if not knowledge_base_id:
        raise ValueError(
            "BEDROCK_KB_ID is not configured"
        )

    if not data_source_id:
        raise ValueError(
            "BEDROCK_DATA_SOURCE_ID "
            "is not configured"
        )

    return bedrock_agent_client.start_ingestion_job(
        knowledgeBaseId=knowledge_base_id,
        dataSourceId=data_source_id,
        description=(
            "Triggered by processed "
            "Zoom transcript"
        ),
    )


def lambda_handler(
    event: Dict[str, Any],
    context: Any,
) -> Dict[str, Any]:

    """
    Convert raw Zoom VTT transcripts into clean text
    documents and trigger Bedrock Knowledge Base sync.
    """

    try:
        records = event.get(
            "Records",
            [],
        )

        if not records:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error":
                        "No S3 records found"
                    }
                ),
            }

        processed_objects = []

        for record in records:
            bucket_name = (
                record["s3"]
                ["bucket"]
                ["name"]
            )

            object_key = unquote_plus(
                record["s3"]
                ["object"]
                ["key"]
            )

            if not object_key.startswith(
                "transcripts/raw/"
            ):
                continue

            if not object_key.endswith(
                ".vtt"
            ):
                continue

            raw_transcript = (
                _read_s3_object(
                    bucket_name,
                    object_key,
                )
            )

            entries = _parse_vtt(
                raw_transcript
            )

            if not entries:
                raise ValueError(
                    "No transcript entries "
                    f"found in {object_key}"
                )

            clean_transcript = (
                _build_clean_transcript(
                    entries
                )
            )

            processed_key = (
                _save_processed_transcript(
                    bucket_name,
                    object_key,
                    clean_transcript,
                )
            )

            processed_objects.append(
                {
                    "raw_key":
                    object_key,

                    "processed_key":
                    processed_key,

                    "entries":
                    len(entries),
                }
            )

        if not processed_objects:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message":
                        "No eligible VTT "
                        "transcripts found"
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
                    "message":
                    "Transcript converted "
                    "and Bedrock ingestion started",

                    "processed_objects":
                    processed_objects,

                    "ingestion_job_id":
                    ingestion_job.get(
                        "ingestionJobId"
                    ),

                    "ingestion_status":
                    ingestion_job.get(
                        "status"
                    ),
                }
            ),
        }

    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "type":
                    type(exc).__name__,
                }
            )
        )

        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error":
                    "Transcript processing failed"
                }
            ),
        }
