# Automated Retrieval Instructions

The Custom RAG Pipeline automatically handles document retrieval using sophisticated query enhancement and program grounding. These instructions guide the automated retrieval system.

## Automated Retrieval Features

### Query Enhancement
- **Context-Aware Processing**: Automatically incorporates conversation context and previous program/variant mentions
- **Program Token Grounding**: Uses extensive program token mapping to identify specific courses
- **Variant Detection**: Automatically detects and handles Remote vs Berlin variants
- **Intent Recognition**: Identifies query types (duration, certifications, coverage, hardware requirements)

### Dynamic Retrieval Strategies
- **Context-Aware Queries**: Enhanced queries for pronouns and references ("that bootcamp", "this program")
- **Comparison Queries**: Specialized retrieval for program comparisons and variant differences
- **Overview Queries**: Comprehensive retrieval for detailed program information
- **Default Queries**: Standard retrieval for general inquiries

### Retrieval Priority System
- **Program-Specific Files**: Prioritize documents matching the exact program mentioned
- **Filename Matching**: Use program tokens to match file names to user queries
- **Cross-Program Prevention**: Avoid retrieving documents from unrelated programs
- **Variant Completeness**: When location unspecified, retrieve both Remote and Berlin variants

### Quality Assurance
- **Evidence Extraction**: Automatically extract evidence chunks from retrieved documents
- **Citation Generation**: Generate accurate source citations for all retrieved content
- **Validation Integration**: Prepare retrieved content for automated validation pipeline
