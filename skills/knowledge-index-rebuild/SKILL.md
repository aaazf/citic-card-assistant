---
name: knowledge-index-rebuild
description: Safely rebuild, validate, activate, or roll back versioned RAG indexes for the local 小智 Knowledge Base when an Embedding model, vector dimension, or index configuration changes.
metadata:
  short-description: Rebuild and verify versioned knowledge indexes
---

# Knowledge Index Rebuild

Use this skill when the knowledge base reports a vector-dimension mismatch, an Embedding model is changed, a new index must be built beside the active one, or a failed rebuild must be diagnosed.

## Core invariant

Never mix vectors from different Embedding models or dimensions.

```text
one collection = one embedding provider + model + vector dimension + chunk policy
```

Changing only the LLM does not require a rebuild. Changing the Embedding model always requires a new vector index, even when the new dimension happens to equal the old dimension.

## Required outcome

A rebuild is complete only when all of these are true:

- A new collection exists; the active collection was not modified in place.
- The new version reaches `ready`.
- `processed_documents == total_documents`.
- `failed_documents == 0`.
- `dimension` equals the dimension returned by the configured Embedding model.
- `total_chunks > 0` for a non-empty knowledge base.
- Activation succeeds only after validation.
- A real question returns an answer with valid citations and readable source chunks.
- The old ready index remains available for rollback.

## Project boundary

This project uses:

- FastAPI for API orchestration.
- SQLite for documents, settings, conversations, and index-version metadata.
- Chroma for vectors, chunks, and retrieval metadata.
- React for the knowledge-base and chat UI.

Relevant existing API endpoints:

```text
GET  /api/v1/settings
POST /api/v1/settings/test-model
GET  /api/v1/indexes
POST /api/v1/indexes/rebuild
POST /api/v1/indexes/{version_id}/activate
POST /api/v1/chat
GET  /api/v1/documents/{document_id}/chunks/{chunk_id}
```

Relevant code:

```text
backend/app/services/index_service.py
backend/app/vectorstores/active.py
backend/app/providers/openai_compatible.py
backend/app/api/v1/indexes.py
frontend/src/pages/settings-page.tsx
```

## Execution steps

### 1. Inspect the baseline

Read the current settings and index list before changing anything.

```powershell
$settings = Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/settings'
$indexes = Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/indexes'
$settings.embedding | ConvertTo-Json -Depth 5
$indexes | ConvertTo-Json -Depth 8
```

Record:

- Active collection name.
- Active model and dimension.
- Current Embedding provider, model, and base URL.
- Document and chunk counts.
- Whether any version is already `building`.

Do not start a second rebuild while one is building.

### 2. Test the Embedding configuration

Use the current form values or stored configuration. A blank API key means use the saved key.

```powershell
$body = @{
  kind = 'embedding'
  provider = $settings.embedding.provider
  model = $settings.embedding.model
  base_url = $settings.embedding.base_url
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri 'http://127.0.0.1:8000/api/v1/settings/test-model' `
  -ContentType 'application/json' `
  -Body $body | ConvertTo-Json -Depth 5
```

The test must return:

```text
connected = true
dimension = the actual vector dimension
```

If it returns HTTP 400, do not rebuild yet. Fix the provider configuration or request format first.

### 3. Create a separate new index

Start a rebuild. The API must create a new collection and return `status = building`.

```powershell
$newVersion = Invoke-RestMethod -Method Post `
  -Uri 'http://127.0.0.1:8000/api/v1/indexes/rebuild'

$newVersion | ConvertTo-Json -Depth 6
```

The active index must remain queryable during this step.

### 4. Poll until the build reaches a terminal state

Poll `GET /api/v1/indexes` rather than assuming success from the initial 202 response.

```powershell
$versionId = $newVersion.id
while ($true) {
  $list = Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/indexes'
  $version = $list.versions | Where-Object { $_.id -eq $versionId }
  $version | Select-Object status, dimension, processed_documents, total_documents, failed_documents, total_chunks, error_message
  if ($version.status -ne 'building') { break }
  Start-Sleep -Seconds 2
}
```

The only successful terminal state is:

```text
status = ready
failed_documents = 0
processed_documents = total_documents
dimension = tested dimension
total_chunks > 0
```

### 5. Diagnose failures without switching

If `status = failed`, keep the old active index. Diagnose from the version and document-level records.

Common checks:

- Inspect `error_message`.
- Inspect `index_documents` for the failed document and chunk count.
- Confirm the source file still exists.
- Confirm the document contains extractable text.
- Confirm the Embedding batch size is accepted by the provider.
- Confirm provider, model, base URL, and dimension did not change mid-build.

Do not activate a failed version.

### 6. Activate only after validation

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/indexes/$versionId/activate" |
  ConvertTo-Json -Depth 6
```

Activation must verify collection count and dimension before updating the active version pointer.

### 7. Run an end-to-end retrieval test

Ask a question that should retrieve a known document.

```powershell
$chatBody = @{
  message = '总结 AI Agent 的特点'
  conversation_id = $null
  knowledge_base_id = '<known-knowledge-base-id>'
  allow_general_fallback = $false
  top_k = 5
} | ConvertTo-Json

$answer = Invoke-RestMethod -Method Post `
  -Uri 'http://127.0.0.1:8000/api/v1/chat' `
  -ContentType 'application/json' `
  -Body $chatBody

$answer | ConvertTo-Json -Depth 8
```

Success criteria:

- `route` is `knowledge` or an intentional `hybrid`.
- `citations` is not empty when the question is answerable.
- Citation filename is expected.
- Citation score is above the selected threshold.
- The cited chunk can be fetched and contains supporting text.

### 8. Keep rollback available

Return the old ready index to the active pointer if the new index fails validation or retrieval quality is worse.

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/indexes/<old-ready-version-id>/activate"
```

Delete old or failed versions only after the new index has been validated and no rollback is needed. Never delete the active collection.

## Decision rules

| Situation | Decision |
| --- | --- |
| Only the LLM changes | No rebuild |
| Embedding model or dimension changes | Build a new collection |
| Active index and settings fingerprints differ | Block query or rebuild |
| New version is `building` | Keep old active; do not upload new documents |
| New version is `failed` | Keep old active; inspect failure |
| New version is `ready` but validation fails | Do not activate; fix and rebuild |
| New version passes all checks | Activate new index |
| Retrieval quality regresses | Activate the old ready version |

## Known failure causes and fixes

| Failure | Meaning | Correct action |
| --- | --- | --- |
| `Collection expecting embedding with dimension of 2048, got 1024` | The active collection was built with a different model/dimension | Restore the original model or rebuild a new 1024-dim collection |
| `batch size is invalid, it should not be larger than 10` | Provider batch limit is smaller than the application batch size | Set the Embedding batch size to 10 or less |
| HTTP 400 from `/embeddings` | Provider rejected model, input, dimension, or batch | Test one input, then retest a small batch |
| HTTP 401/403 | API key missing, invalid, or unauthorized | Reconfigure and test the key |
| HTTP 404 on `/embeddings` | Provider does not implement an Embedding endpoint | Use a provider that supports Embeddings |
| `processed_documents < total_documents` | Rebuild stopped before all documents finished | Inspect the failed document and retry a new rebuild |
| `failed_documents > 0` | At least one source failed parsing or Embedding | Fix the source or parser, then rebuild |
| `No extractable text` | File contains no text or the parser failed | Inspect the original file and loader |
| Config changed during build | Settings no longer match the version fingerprint | Keep the old index and rebuild with stable settings |
| Metadata modification changes distance function | Chroma `hnsw:space` was changed after collection creation | Do not modify `hnsw:space`; keep cosine distance |
| Query returns 409 | Active index and current Embedding configuration are incompatible | Restore the matching model or activate a compatible index |

## Hard rules

- Do not pad, truncate, or convert vectors between dimensions.
- Do not write 1024-dim vectors into a 2048-dim collection.
- Do not reuse vectors generated by a different Embedding model.
- Do not rebuild by clearing the active collection in place.
- Do not activate an index with failed documents or incomplete counts.
- Do not delete the old index before the new index passes end-to-end retrieval.
- Do not store API keys in logs, prompts, screenshots, or documentation.

## Reuse prompt

```text
Use $knowledge-index-rebuild to inspect the active index, test the configured Embedding dimension,
create a separate rebuild version, diagnose failures without switching, activate only after all
documents are ready, and verify the result with a cited end-to-end question.
```

## Current verified baseline

As of the last successful run:

```text
Embedding model: text-embedding-v4
Provider: DashScope OpenAI-compatible endpoint
Dimension: 1024
Documents: 3
Chunks: 628
Failed documents: 0
Active status: ready
Old 2048-dim index: retained for rollback
Backend tests: 55 passed
Frontend tests: 9 passed
Build: passed
```

## Completion report

Report all of the following:

```text
Active collection:
Embedding model and dimension:
New version status:
Processed / total documents:
Failed documents:
Total chunks:
Activation result:
Question used for verification:
Route and citation count:
Old index retained for rollback:
Outstanding failures or limitations:
```
