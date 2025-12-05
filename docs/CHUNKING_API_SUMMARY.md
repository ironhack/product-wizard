# Chunking Configuration via API - Summary

## Key Finding

**Chunking is set per-file when adding files to the vector store, NOT at the vector store level.**

## Correct API Approach

### Endpoint
```
POST /v1/vector_stores/{vector_store_id}/files
```

### Request Body (with chunking)
```json
{
  "file_id": "file_xxx",
  "chunking_strategy": {
    "type": "static",
    "static": {
      "max_chunk_size_tokens": 500,
      "chunk_overlap_tokens": 75
    }
  }
}
```

## Updated Scripts

### 1. `tools/rebuild_vector_store.py`
Now supports chunking during upload:
```bash
# Rebuild with 500 token chunks
python3 tools/rebuild_vector_store.py --chunk-size 500 --overlap 75
```

### 2. `tools/upload_vector_store_file.py`
Now supports chunking parameter:
```bash
# Upload single file with chunking
python3 tools/upload_vector_store_file.py file.txt --chunk-size 500 --overlap 75
```

## What Changed

1. **Removed vector store-level chunking**: Not supported via API
2. **Added per-file chunking**: Set during file upload
3. **Updated upload functions**: Now accept `chunk_size` and `chunk_overlap` parameters
4. **Individual file endpoint**: Uses `/files` endpoint when chunking specified (instead of `/file_batches`)

## Next Steps

To rebuild your vector store with 500-token chunks:

```bash
# Empty and rebuild with 500 token chunks
python3 tools/rebuild_vector_store.py --chunk-size 500 --overlap 75
```

This will:
1. ✅ Empty the vector store
2. ✅ Upload all files with 500-token chunking specified
3. ✅ Each file will be chunked at 500 tokens with 75 token overlap

## Documentation

- **Full API Documentation**: `docs/VECTOR_STORE_CHUNKING_API.md`
- **Configuration Guide**: `docs/CHUNKING_CONFIGURATION.md`

---

*Updated: 2025-01-28*
