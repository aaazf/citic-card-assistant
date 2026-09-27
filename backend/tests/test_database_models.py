from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import inspect


def test_database_schema_is_initialized(client: TestClient, test_app: FastAPI) -> None:
    with client:
        table_names = set(inspect(test_app.state.database.engine).get_table_names())

    assert {
        "knowledge_bases",
        "documents",
        "conversations",
        "messages",
        "model_configs",
        "system_settings",
    }.issubset(table_names)
