import json
import os
from typing import Any, Dict, List

import boto3


bedrock_agent_runtime = boto3.client("bedrock-agent-runtime")
bedrock_runtime = boto3.client("bedrock-runtime")


def _retrieve_context(
    knowledge_base_id: str,
    query: str,
) -> List[Dict[str, Any]]:

    response = bedrock_agent_runtime.retrieve(
        knowledgeBaseId=knowledge_base_id,
        retrievalQuery={
            "text": query
        },
        retrievalConfiguration={
            "managedSearchConfiguration": {
                "numberOfResults": 5
            }
        }
    )

    return response.get(
        "retrievalResults",
        []
    )


def _build_context(
    retrieval_results: List[Dict[str, Any]],
) -> str:

    chunks = []

    for index, result in enumerate(
        retrieval_results,
        start=1,
    ):
        content = result.get(
            "content",
            {}
        )

        text = content.get(
            "text",
            ""
        )

        if text:
            chunks.append(
                f"[Source {index}]\n{text}"
            )

    return "\n\n".join(chunks)


def _build_sources(
    retrieval_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    sources = []

    for result in retrieval_results:
        location = result.get(
            "location",
            {}
        )

        s3_location = location.get(
            "s3Location",
            {}
        )

        sources.append(
            {
                "uri": s3_location.get(
                    "uri"
                ),
                "score": result.get(
                    "score"
                ),
            }
        )

    return sources


def _generate_answer(
    query: str,
    context: str,
) -> str:

    model_id = os.getenv(
        "BEDROCK_MODEL_ID",
        "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    )

    prompt = f"""
You are a meeting transcript assistant.

Answer the user's question using ONLY the transcript
context provided below.

If the answer cannot be determined from the context,
say:

"I could not find that information in the meeting transcript."

Do not invent information.

Transcript context:
{context}

User question:
{query}
"""

    response = bedrock_runtime.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt
                    }
                ],
            }
        ],
        inferenceConfig={
            "maxTokens": 512,
            "temperature": 0.1,
        },
    )

    return (
        response["output"]
        ["message"]
        ["content"][0]
        ["text"]
    )


def lambda_handler(
    event: Dict[str, Any],
    context: Any,
) -> Dict[str, Any]:

    try:
        body = event.get(
            "body",
            {}
        )

        if isinstance(
            body,
            str,
        ):
            body = json.loads(
                body
            )

        user_query = (
            body.get("query")
            or body.get("user_query")
        )

        if not user_query:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type":
                    "application/json"
                },
                "body": json.dumps(
                    {
                        "error":
                        "query is required"
                    }
                ),
            }

        knowledge_base_id = os.getenv(
            "BEDROCK_KB_ID"
        )

        if not knowledge_base_id:
            raise ValueError(
                "BEDROCK_KB_ID is not configured"
            )

        retrieval_results = (
            _retrieve_context(
                knowledge_base_id,
                user_query,
            )
        )

        if not retrieval_results:
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type":
                    "application/json"
                },
                "body": json.dumps(
                    {
                        "query":
                        user_query,

                        "answer":
                        "I could not find that "
                        "information in the "
                        "meeting transcript.",

                        "sources": [],
                    }
                ),
            }

        context_text = (
            _build_context(
                retrieval_results
            )
        )

        answer = _generate_answer(
            user_query,
            context_text,
        )

        sources = _build_sources(
            retrieval_results
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type":
                "application/json"
            },
            "body": json.dumps(
                {
                    "query":
                    user_query,

                    "answer":
                    answer,

                    "sources":
                    sources,
                }
            ),
        }

    except Exception as exc:
        print(
            json.dumps(
                {
                    "error":
                    str(exc),

                    "type":
                    type(exc).__name__,
                }
            )
        )

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type":
                "application/json"
            },
            "body": json.dumps(
                {
                    "error":
                    "Unable to retrieve an "
                    "answer from the "
                    "knowledge base"
                }
            ),
        }
