from fastapi.testclient import TestClient

EXPECTED_OPERATIONS = {
    "/api/v1/chat": {"post"},
    "/api/v1/conversations": {"get"},
    "/api/v1/conversations/{conversation_id}": {"get", "delete"},
    "/api/v1/knowledge": {"get", "post"},
    "/api/v1/knowledge/{knowledge_base_id}": {"delete"},
    "/api/v1/knowledge/search": {"post"},
    "/api/v1/documents": {"get"},
    "/api/v1/documents/upload": {"post"},
    "/api/v1/documents/{document_id}": {"delete"},
    "/api/v1/settings": {"get", "put"},
    "/api/v1/health": {"get"},
    "/api/v1/model/status": {"get"},
}


def test_openapi_contains_baseline_contract(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    for path, methods in EXPECTED_OPERATIONS.items():
        assert path in schema["paths"]
        assert methods.issubset(schema["paths"][path])
