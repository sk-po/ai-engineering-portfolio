from __future__ import annotations

import copy
import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch


INFRA_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = INFRA_DIR / "scripts" / "deploy_search_index.py"
SCHEMA_PATH = INFRA_DIR / "search" / "security-docs-v1.json"

spec = importlib.util.spec_from_file_location("deploy_search_index", SCRIPT_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT_PATH}")
deploy_search_index = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy_search_index)


class DeploySearchIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = deploy_search_index.load_schema(SCHEMA_PATH)

    def test_security_schema_matches_the_decided_vector_configuration(self) -> None:
        deploy_search_index.validate_schema(self.schema)

        self.assertEqual("security-docs-v1", self.schema["name"])
        self.assertEqual(38, len(self.schema["fields"]))

        fields = {field["name"]: field for field in self.schema["fields"]}
        self.assertEqual(
            "chunk_id",
            next(field["name"] for field in self.schema["fields"] if field["key"]),
        )
        self.assertEqual(1536, fields["content_vector"]["dimensions"])
        self.assertEqual(
            "vector-profile-default",
            fields["content_vector"]["vectorSearchProfile"],
        )

        algorithm = self.schema["vectorSearch"]["algorithms"][0]
        self.assertEqual("hnsw", algorithm["kind"])
        self.assertEqual("cosine", algorithm["hnswParameters"]["metric"])
        self.assertEqual(4, algorithm["hnswParameters"]["m"])
        self.assertEqual(400, algorithm["hnswParameters"]["efConstruction"])
        self.assertEqual(500, algorithm["hnswParameters"]["efSearch"])

    def test_validation_rejects_an_invalid_field_name(self) -> None:
        invalid_schema = copy.deepcopy(self.schema)
        invalid_schema["fields"][0]["name"] = "invalid/name"

        with self.assertRaisesRegex(ValueError, "Invalid field name"):
            deploy_search_index.validate_schema(invalid_schema)

    def test_validation_rejects_an_unknown_vector_profile(self) -> None:
        invalid_schema = copy.deepcopy(self.schema)
        vector_field = next(
            field for field in invalid_schema["fields"] if "dimensions" in field
        )
        vector_field["vectorSearchProfile"] = "missing-profile"

        with self.assertRaisesRegex(ValueError, "unknown profile"):
            deploy_search_index.validate_schema(invalid_schema)

    def test_build_index_url_uses_the_stable_data_plane_api(self) -> None:
        url = deploy_search_index.build_index_url(
            "search-asvs-rag-dev-example",
            "security-docs-v1",
            "2025-09-01",
        )

        self.assertEqual(
            "https://search-asvs-rag-dev-example.search.windows.net/"
            "indexes('security-docs-v1')?api-version=2025-09-01",
            url,
        )

    def test_dry_run_does_not_require_an_azure_token(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = deploy_search_index.main(
                [
                    "--service-name",
                    "search-asvs-rag-dev-example",
                    "--schema-file",
                    str(SCHEMA_PATH),
                    "--dry-run",
                ]
            )

        self.assertEqual(0, exit_code)
        self.assertIn("Dry run completed", output.getvalue())

    @patch.object(deploy_search_index.urllib.request, "urlopen")
    def test_put_index_uses_bearer_authentication(self, urlopen: MagicMock) -> None:
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'{"name":"security-docs-v1"}'
        urlopen.return_value.__enter__.return_value = response

        status, payload = deploy_search_index.put_index(
            url="https://example.search.windows.net/indexes('security-docs-v1')",
            schema=self.schema,
            access_token="test-token",
            timeout_seconds=30,
        )

        request = urlopen.call_args.args[0]
        self.assertEqual("PUT", request.get_method())
        self.assertEqual("Bearer test-token", request.get_header("Authorization"))
        self.assertEqual(200, status)
        self.assertEqual("security-docs-v1", payload["name"])


if __name__ == "__main__":
    unittest.main()
