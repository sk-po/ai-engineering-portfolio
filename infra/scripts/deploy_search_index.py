"""Create or update an Azure AI Search index from a versioned JSON schema."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Sequence


API_VERSION = "2025-09-01"
SEARCH_SCOPE = "https://search.azure.com/.default"
DEFAULT_SCHEMA_FILE = (
    Path(__file__).resolve().parents[1] / "search" / "security-docs-v1.json"
)
SERVICE_NAME_PATTERN = re.compile(
    r"^(?=.{2,60}$)[a-z0-9](?:[a-z0-9]|-(?!-))*[a-z0-9]$"
)
INDEX_NAME_PATTERN = re.compile(
    r"^(?=.{2,128}$)[a-z0-9](?:[a-z0-9]|-(?!-))*[a-z0-9]$"
)
FIELD_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def load_schema(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as schema_file:
            schema = json.load(schema_file)
    except FileNotFoundError as error:
        raise ValueError(f"Schema file not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Schema file is not valid JSON: {path}:{error.lineno}:{error.colno}"
        ) from error

    if not isinstance(schema, dict):
        raise ValueError("The schema root must be a JSON object.")
    return schema


def validate_schema(schema: dict[str, Any]) -> None:
    index_name = schema.get("name")
    if not isinstance(index_name, str) or not INDEX_NAME_PATTERN.fullmatch(index_name):
        raise ValueError("Schema 'name' must be a valid lowercase Azure AI Search name.")

    fields = schema.get("fields")
    if not isinstance(fields, list) or not fields:
        raise ValueError("Schema 'fields' must be a non-empty array.")

    field_names: list[str] = []
    key_fields: list[str] = []
    vector_fields: list[dict[str, Any]] = []
    for field in fields:
        if not isinstance(field, dict) or not isinstance(field.get("name"), str):
            raise ValueError("Every field must be an object with a string 'name'.")
        field_name = field["name"]
        if not FIELD_NAME_PATTERN.fullmatch(field_name):
            raise ValueError(f"Invalid field name: {field_name}")
        if field_name in field_names:
            raise ValueError(f"Duplicate field name: {field_name}")
        field_names.append(field_name)

        if field.get("key") is True:
            key_fields.append(field_name)
        if field.get("type", "").startswith("Collection(Edm.") and "dimensions" in field:
            vector_fields.append(field)

    if len(key_fields) != 1:
        raise ValueError("Schema must define exactly one key field.")

    vector_search = schema.get("vectorSearch")
    if not isinstance(vector_search, dict):
        raise ValueError("Schema must define 'vectorSearch'.")

    algorithms = vector_search.get("algorithms")
    profiles = vector_search.get("profiles")
    if not isinstance(algorithms, list) or not algorithms:
        raise ValueError("vectorSearch must define at least one algorithm.")
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("vectorSearch must define at least one profile.")

    algorithm_names = {
        algorithm.get("name") for algorithm in algorithms if isinstance(algorithm, dict)
    }
    profile_algorithms: dict[str, str] = {}
    for profile in profiles:
        if not isinstance(profile, dict):
            raise ValueError("Every vector search profile must be an object.")
        profile_name = profile.get("name")
        algorithm_name = profile.get("algorithm")
        if not isinstance(profile_name, str) or not isinstance(algorithm_name, str):
            raise ValueError("Every vector profile must name itself and its algorithm.")
        if algorithm_name not in algorithm_names:
            raise ValueError(
                f"Vector profile '{profile_name}' references an unknown algorithm."
            )
        profile_algorithms[profile_name] = algorithm_name

    for field in vector_fields:
        dimensions = field.get("dimensions")
        profile_name = field.get("vectorSearchProfile")
        if not isinstance(dimensions, int) or dimensions < 1:
            raise ValueError(
                f"Vector field '{field['name']}' must have positive integer dimensions."
            )
        if profile_name not in profile_algorithms:
            raise ValueError(
                f"Vector field '{field['name']}' references an unknown profile."
            )


def build_index_url(service_name: str, index_name: str, api_version: str) -> str:
    if not SERVICE_NAME_PATTERN.fullmatch(service_name):
        raise ValueError(
            "Search service name must contain only lowercase letters, numbers, and hyphens."
        )
    if not INDEX_NAME_PATTERN.fullmatch(index_name):
        raise ValueError("Index name is invalid.")

    encoded_index_name = urllib.parse.quote(index_name, safe="-")
    encoded_api_version = urllib.parse.quote(api_version, safe="-")
    return (
        f"https://{service_name}.search.windows.net/"
        f"indexes('{encoded_index_name}')?api-version={encoded_api_version}"
    )


def acquire_access_token(subscription: str | None) -> str:
    azure_cli = shutil.which("az")
    if azure_cli is None:
        raise RuntimeError("Azure CLI was not found. Install it and run 'az login'.")

    command = [
        azure_cli,
        "account",
        "get-access-token",
        "--scope",
        SEARCH_SCOPE,
        "--query",
        "accessToken",
        "--output",
        "tsv",
        "--only-show-errors",
    ]
    if subscription:
        command.extend(["--subscription", subscription])

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "unknown Azure CLI error").strip()
        raise RuntimeError(f"Could not acquire an Azure AI Search token: {detail}") from error

    token = result.stdout.strip()
    if not token:
        raise RuntimeError("Azure CLI returned an empty Azure AI Search token.")
    return token


def put_index(
    url: str,
    schema: dict[str, Any],
    access_token: str,
    timeout_seconds: float,
) -> tuple[int, dict[str, Any]]:
    body = json.dumps(schema, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=body,
        method="PUT",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
            "x-ms-client-request-id": str(uuid.uuid4()),
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
            payload = json.loads(response_body) if response_body else {}
            return response.status, payload
    except urllib.error.HTTPError as error:
        response_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Azure AI Search returned HTTP {error.code}: {response_body}"
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not connect to Azure AI Search: {error.reason}") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create or update an Azure AI Search index from a versioned JSON schema. "
            "The command doesn't generate embeddings or upload documents."
        )
    )
    parser.add_argument(
        "--service-name",
        default=os.getenv("AZURE_SEARCH_SERVICE_NAME"),
        help=(
            "Azure AI Search service name. Defaults to AZURE_SEARCH_SERVICE_NAME."
        ),
    )
    parser.add_argument(
        "--schema-file",
        type=Path,
        default=DEFAULT_SCHEMA_FILE,
        help=f"Index schema JSON file. Default: {DEFAULT_SCHEMA_FILE}",
    )
    parser.add_argument(
        "--subscription",
        help="Optional Azure subscription ID or name used to acquire the access token.",
    )
    parser.add_argument(
        "--api-version",
        default=API_VERSION,
        help=f"Azure AI Search data-plane API version. Default: {API_VERSION}",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=60.0,
        help="HTTP timeout in seconds. Default: 60",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the schema and print the target without calling Azure.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.service_name:
        parser.error(
            "--service-name is required when AZURE_SEARCH_SERVICE_NAME is not set."
        )
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be greater than zero.")

    try:
        schema = load_schema(args.schema_file)
        validate_schema(schema)
        target_url = build_index_url(
            service_name=args.service_name,
            index_name=schema["name"],
            api_version=args.api_version,
        )
    except ValueError as error:
        parser.error(str(error))

    vector_fields = [
        field for field in schema["fields"] if "dimensions" in field
    ]
    print(
        f"Validated index schema '{schema['name']}': "
        f"{len(schema['fields'])} fields, {len(vector_fields)} vector field(s)."
    )
    print(f"Target: {target_url}")
    if args.dry_run:
        print("Dry run completed. Azure was not changed.")
        return 0

    try:
        access_token = acquire_access_token(args.subscription)
        status, response = put_index(
            url=target_url,
            schema=schema,
            access_token=access_token,
            timeout_seconds=args.timeout_seconds,
        )
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    deployed_name = response.get("name", schema["name"])
    print(f"Index '{deployed_name}' was created or updated (HTTP {status}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
