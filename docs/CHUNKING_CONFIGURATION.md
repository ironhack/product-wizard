# Vector Store Chunking Configuration Guide

## Overview

OpenAI vector stores support configurable chunking strategies to optimize document retrieval. This guide explains how to configure chunking for your RAG system.

## Chunking Strategies

### 1. Auto Chunking (Default)
**Type**: `auto`

OpenAI automatically determines optimal chunk boundaries based on document structure:
- Aligns chunks with semantic units (paragraphs, sentences)
- Adapts to document structure automatically
- No configuration needed

**Best For**: 
- General use cases
- Documents with clear structure
- When you want OpenAI to handle optimization

### 2. Static Chunking
**Type**: `static`

Manual control over chunk size and overlap:
- `max_chunk_size_tokens`: Maximum tokens per chunk
- `chunk_overlap_tokens`: Overlapping tokens between consecutive chunks

**Best For**:
- Fine-tuning retrieval for specific document types
- When you need consistent chunk sizes
- When optimizing for specific query types

## Configuration Tool

Use the provided script to configure chunking:

```bash
# Check current configuration
python3 tools/configure_vector_store_chunking.py --check

# Use auto chunking (default)
python3 tools/configure_vector_store_chunking.py --auto

# Use static chunking with custom parameters
python3 tools/configure_vector_store_chunking.py --static --max-tokens 800 --overlap 200
```

## Best Practices

### Chunk Size Guidelines

| Chunk Size | Use Case | Pros | Cons |
|------------|----------|------|------|
| **200-400 tokens** | High precision queries | Better retrieval precision | May split relevant info across chunks |
| **400-800 tokens** | Balanced (recommended) | Good balance of precision and context | Standard default |
| **800-1600 tokens** | Context-heavy queries | Retains more context | May dilute relevance |

### Overlap Guidelines

| Overlap | Percentage | Use Case |
|---------|------------|----------|
| **10-20%** | Recommended | Preserves context across boundaries |
| **5-10%** | Minimal | When chunks are large (>800 tokens) |
| **20-30%** | High | When information spans multiple chunks |

**Example**: For 800 token chunks, use 80-160 token overlap (10-20%)

### Recommended Configurations

#### High Precision (Small Chunks)
```bash
python3 tools/configure_vector_store_chunking.py --static --max-tokens 400 --overlap 40
```
- Best for: Specific technology/tool questions
- Trade-off: May require retrieving more chunks

#### Balanced (Default)
```bash
python3 tools/configure_vector_store_chunking.py --static --max-tokens 800 --overlap 200
```
- Best for: General curriculum questions
- Trade-off: Good balance of precision and context

#### Context-Heavy (Large Chunks)
```bash
python3 tools/configure_vector_store_chunking.py --static --max-tokens 1200 --overlap 240
```
- Best for: Comparison queries, comprehensive answers
- Trade-off: May include less relevant content

## Current System Configuration

Your RAG v2 system currently uses:
- **Default**: Auto chunking (OpenAI managed)
- **Retrieval**: Top-K varies by query type (10-20 chunks)
- **Expansion**: Can retrieve up to 25 chunks when needed

## When to Change Chunking Strategy

### Consider Static Chunking If:
- ✅ Retrieval quality needs optimization
- ✅ Specific document types need different chunk sizes
- ✅ You're seeing information split across chunks
- ✅ You want consistent chunk sizes for testing

### Keep Auto Chunking If:
- ✅ Current retrieval quality is good
- ✅ Documents have clear structure
- ✅ You want OpenAI to optimize automatically

## Impact of Chunking Changes

**Important**: Changing chunking strategy affects:
- ✅ **New files**: Will use new chunking strategy immediately
- ⚠️ **Existing files**: May need to be re-uploaded for changes to take effect

**To apply changes to existing files**:
1. Update chunking configuration
2. Re-upload files using `tools/upload_vector_store_file.py`
3. Files will be re-chunked with new strategy

## Monitoring Chunk Quality

After changing chunking strategy, monitor:
- **Retrieval precision**: Are relevant chunks being retrieved?
- **Response quality**: Are answers complete and accurate?
- **Chunk diversity**: Are chunks from different document sections?
- **Cross-contamination**: Are chunks mixing between programs?

Use your test suite to evaluate:
```bash
python3 tests/rag_v2_test.py --manual "Your test question"
```

## Comparison with Guide's Approach

| Aspect | Guide's Manual Chunking | OpenAI Vector Store |
|--------|------------------------|---------------------|
| **Control** | Full control (word count) | Token-based control |
| **Maintenance** | Manual chunking code | Managed by OpenAI |
| **Flexibility** | Can customize per document | Vector store-level setting |
| **Complexity** | More code to maintain | Simple configuration |

**Recommendation**: Use OpenAI's managed chunking (auto or static) for production systems. Manual chunking is useful for learning but adds complexity.

## Troubleshooting

### Chunks Too Small
**Symptoms**: Information split across multiple chunks  
**Solution**: Increase `max_chunk_size_tokens` (e.g., 800 → 1200)

### Chunks Too Large
**Symptoms**: Low retrieval precision, irrelevant content  
**Solution**: Decrease `max_chunk_size_tokens` (e.g., 800 → 400)

### Missing Context at Boundaries
**Symptoms**: Information cut off at chunk edges  
**Solution**: Increase `chunk_overlap_tokens` (e.g., 200 → 300)

### Too Much Redundancy
**Symptoms**: Same information in multiple chunks  
**Solution**: Decrease `chunk_overlap_tokens` (e.g., 200 → 100)

## References

- OpenAI Vector Store API: https://platform.openai.com/docs/api-reference/vector-stores
- Chunking Best Practices: Industry standard 10-20% overlap
- Your RAG v2 System: Uses hybrid retrieval with top-K adaptation

---

*Last Updated: 2025-01-28*
