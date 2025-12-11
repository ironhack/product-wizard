# Vector Store Chunking Configuration via API

## Overview

OpenAI vector stores support chunking configuration, but **chunking is set per-file when adding files to the vector store**, not at the vector store level.

## API Endpoint

**Endpoint**: `POST /v1/vector_stores/{vector_store_id}/files/{file_id}`

**Purpose**: Update chunking strategy for a specific file in the vector store

## Chunking Strategy Format

### Static Chunking (Manual Control)

```json
{
  "chunking_strategy": {
    "type": "static",
    "static": {
      "max_chunk_size_tokens": 500,
      "chunk_overlap_tokens": 75
    }
  }
}
```

### Auto Chunking (Default)

```json
{
  "chunking_strategy": {
    "type": "auto"
  }
}
```

## Constraints

- `max_chunk_size_tokens`: Must be between **100** and **4,096** tokens
- `chunk_overlap_tokens`: Must be non-negative and **not exceed half** of `max_chunk_size_tokens`

## cURL Example

```bash
curl --request POST \
  --url https://api.openai.com/v1/vector_stores/{vector_store_id}/files/{file_id} \
  --header 'Authorization: Bearer YOUR_API_KEY' \
  --header 'Content-Type: application/json' \
  --header 'OpenAI-Beta: assistants=v2' \
  --data '{
    "chunking_strategy": {
      "type": "static",
      "static": {
        "max_chunk_size_tokens": 500,
        "chunk_overlap_tokens": 75
      }
    }
  }'
```

## Python SDK Example

### Method 1: When Adding File to Vector Store

```python
from openai import OpenAI

client = OpenAI(api_key='your-api-key')

# Upload file first
with open('document.txt', 'rb') as file:
    file_response = client.files.create(
        file=file,
        purpose='assistants'
    )
file_id = file_response.id

# Add to vector store WITH chunking strategy
response = client.vector_stores.files.create(
    vector_store_id='vs_xxx',
    file_id=file_id,
    chunking_strategy={
        "type": "static",
        "static": {
            "max_chunk_size_tokens": 500,
            "chunk_overlap_tokens": 75
        }
    }
)
```

### Method 2: Update Existing File Chunking

```python
from openai import OpenAI
import urllib.request
import json

client = OpenAI(api_key='your-api-key')
vector_store_id = 'vs_xxx'
file_id = 'file_xxx'

# Use HTTP API directly (Python SDK doesn't have direct update method)
url = f"https://api.openai.com/v1/vector_stores/{vector_store_id}/files/{file_id}"
headers = {
    'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}',
    'Content-Type': 'application/json',
    'OpenAI-Beta': 'assistants=v2'
}

data = {
    "chunking_strategy": {
        "type": "static",
        "static": {
            "max_chunk_size_tokens": 500,
            "chunk_overlap_tokens": 75
        }
    }
}

req = urllib.request.Request(
    url,
    data=json.dumps(data).encode('utf-8'),
    headers=headers,
    method='POST'
)

with urllib.request.urlopen(req) as response:
    result = json.loads(response.read().decode('utf-8'))
    print(result)
```

## Important Notes

### ⚠️ Chunking Must Be Set Per-File

- **Vector store-level chunking**: Not supported via API (only via dashboard)
- **File-level chunking**: Must be specified when adding each file
- **Updating existing files**: Requires re-uploading with new chunking strategy

### 🔄 To Change Chunking for Existing Files

1. **Delete file from vector store**
2. **Re-upload file** with new chunking strategy specified
3. **Wait for processing** to complete

### 📋 Best Practices

1. **Set chunking during upload**: Always specify `chunking_strategy` when adding files
2. **Consistent chunking**: Use the same chunking strategy for all files in a vector store
3. **Monitor chunk quality**: Test retrieval after changing chunk sizes
4. **Re-upload if needed**: If chunking wasn't set correctly, delete and re-upload

## Recommended Chunk Sizes

| Use Case | Chunk Size | Overlap | Notes |
|----------|------------|---------|-------|
| **High Precision** | 200-400 tokens | 20-40 tokens (10%) | Better retrieval precision, may split info |
| **Balanced** | 400-800 tokens | 40-120 tokens (10-15%) | Good balance (recommended) |
| **Context-Heavy** | 800-1600 tokens | 80-240 tokens (10-15%) | More context, may dilute relevance |

## Example: 500 Token Chunks with 75 Token Overlap

```python
chunking_strategy = {
    "type": "static",
    "static": {
        "max_chunk_size_tokens": 500,
        "chunk_overlap_tokens": 75  # 15% overlap
    }
}
```

This configuration:
- Creates chunks of up to 500 tokens
- Overlaps consecutive chunks by 75 tokens (15%)
- Good balance for curriculum documents

## References

- OpenAI API Documentation: https://platform.openai.com/docs/api-reference/vector-stores
- Retrieval Guide: https://platform.openai.com/docs/guides/retrieval
- Python SDK Issues: https://github.com/openai/openai-python/issues/2380

---

*Last Updated: 2025-01-28*


