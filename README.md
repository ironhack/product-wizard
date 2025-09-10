# 🧙‍♂️ Product Wizard - Ironhack Sales Enablement Assistant

> An AI-powered assistant that provides accurate, citation-backed information about Ironhack courses for sales teams during live calls with prospective students.

## 🎯 Overview

Product Wizard is a comprehensive system that serves three main purposes:

1. **🤖 OpenAI Responses API with Knowledge Base** - AI assistant with vector store containing Ironhack course information
2. **🔗 Slack Integration Middleware** - Heroku app connecting the assistant to Slack
3. **🛠️ Development & Testing Tools** - Utilities for prompt optimization, testing, and deployment

### Key Features
- ✅ **Zero Fabrication Policy** - Only provides documented information
- ✅ **Perfect Citations** - References specific curriculum documents
- ✅ **Sales-Ready Responses** - Conversational tone for phone calls
- ✅ **Variant Awareness** - Distinguishes Remote vs Berlin programs
- ✅ **Multi-Course Support** - All Ironhack bootcamps and programs

## 📁 Repository Structure

This repository contains three fundamental components:

### 1. 🧠 Knowledge Base & Assistant Configuration

```
assistant_config/
└── MASTER_PROMPT.md       # Current assistant prompt (production version)

knowledge_base/
├── database/              # Course information in Markdown format (easier to maintain)
├── database_txt/          # Course information in TXT format (loaded to OpenAI vector store)
└── [previous location of index.yaml - now in root]

index.yaml                 # Course structure configuration for third-party applications
```

**Note**: When you modify a Markdown file in `database/`, you must also update the corresponding TXT file in `database_txt/`.

### 2. 🚀 Heroku Middleware Application

```
src/
├── app_response.py        # Responses API Slack middleware (production)
├── app_assistants.py      # Legacy Assistants API version (backup)
└── __init__.py           # Package initialization

Procfile                   # Heroku deployment configuration
requirements.txt           # Python dependencies
runtime.txt               # Python version specification
```

### 3. 🧪 Development & Testing Tools

```
tests/                     # Local testing and assistant optimization
├── model_tests/          # Model comparison and upgrade tests
├── results/              # Test output files and reports
├── archive/              # Historical test files
└── test_*.py            # Various test scripts for prompt optimization

tools/                     # Utility scripts
├── deploy_prompt.py      # Deploy prompts to OpenAI assistant in production
├── assistant_tester.py   # Assistant testing utilities
├── cleanup_repo.py       # Repository maintenance tools
└── *.py                 # Other development utilities

docs/                      # Documentation and development history
├── development/          # All prompt versions and development history
│   ├── MASTER_PROMPT_V*.md  # Historical prompt versions (V1-V6)
│   └── [Latest version is duplicated as backup in assistant_config/]
└── reports/              # Results from various optimization scripts
    ├── FINAL_REPORT.md
    ├── CITATIONS_FINAL_REPORT.md
    └── *.md
```

## 🔄 Development Workflow

### Prompt Management
- **Current Version**: `assistant_config/MASTER_PROMPT.md` (production)
- **Version History**: `docs/development/MASTER_PROMPT_V*.md` (backup)
- **Process**: When updating the master prompt, create a new version in `docs/development/`

### Knowledge Base Updates
1. Edit Markdown files in `knowledge_base/database/`
2. Update corresponding TXT files in `knowledge_base/database_txt/`
3. Deploy changes to OpenAI vector store

### Testing & Optimization
- Use scripts in `tests/` for local prompt optimization
- Results are automatically saved to `tests/results/`
- Use `tools/` for deployment and maintenance

## 🚀 Quick Start

### 1. Setup Environment Variables
```bash
# Copy environment variables template
cp .env.example .env

# Edit .env with your credentials
# - OPENAI_API_KEY
# - OPENAI_VECTOR_STORE_ID (Responses API)
# - OPENAI_ASSISTANT_ID (Legacy - for app_assistants.py)
# - SLACK_BOT_TOKEN (for Heroku deployment)
# - SLACK_SIGNING_SECRET (for Heroku deployment)
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application (Local Development)
```bash
python src/app_response.py
```

### 4. Test the Assistant
```bash
# Quick test
python tools/assistant_tester.py

# Citation quality test
python tests/test_citations_clean.py
```

## 🧪 Testing Suite

### Available Tests

| Test | Purpose | Command |
|------|---------|---------|
| **Citation Quality** | Verify proper file citations | `python tests/test_citations_clean.py` |
| **Fabrication Check** | Ensure no invented information | `python tests/test_sales_scenarios.py` |
| **Model Comparison** | Compare different GPT models | `python tests/model_tests/model_comparison_test.py` |

### Test Results
All test results are saved to `tests/results/` with timestamps and detailed analysis.

## 📊 Performance Metrics

### Current Performance (V8 - Responses API)
- **Fabrication Rate**: 0% (Zero fabrications detected)
- **Citation Quality**: 9.3/10 (Excellent file attribution)
- **Sales Readiness**: 96.8% (Excellent production readiness)
- **Response Speed**: 2.4x faster than legacy API (11.7s vs 28s avg)
- **API**: OpenAI Responses API with GPT-4o (GPT-5 ready)

### Key Achievements
- ✅ **Migrated to Responses API** - Future-proof, 2.4x faster performance
- ✅ **Eliminated all major fabrications** (DevOps GCP/Jenkins, fake schedules)
- ✅ **Perfect citations** with full document names
- ✅ **Variant-aware responses** (Remote vs Berlin)
- ✅ **Sales-appropriate conversational tone**
- ✅ **Threaded conversation support** for Slack integration

## 🎯 Usage Examples

### For Sales Team

**Question**: "What technologies are covered in the Web Development bootcamp?"

**Response**: 
> According to the Web Development bootcamp curriculum, the program covers a comprehensive range of technologies. For the Berlin onsite bootcamp, the tools used include HTML & CSS, JavaScript (ES6+), TypeScript, Node.js, Express.js, Next.js, React, MongoDB... 【Web_Dev_Berlin_onsite_bootcamp_2025_07.txt】

**Benefits**:
- Clear source attribution
- Specific curriculum reference
- Variant distinction (Berlin vs Remote)
- Professional but conversational tone

## 🔧 Configuration

### Environment Variables
```python
# OpenAI Configuration
OPENAI_API_KEY = "your_api_key_here"
OPENAI_VECTOR_STORE_ID = "your_vector_store_id_here"  # For Responses API
OPENAI_ASSISTANT_ID = "your_assistant_id_here"        # Legacy (backup only)

# Slack Configuration (for middleware)
SLACK_BOT_TOKEN = "your_slack_token_here"
SLACK_SIGNING_SECRET = "your_signing_secret_here"
```

### API Configuration
- **API**: OpenAI Responses API (production) + Assistants API (backup)
- **Model**: GPT-4o (ready for GPT-5 upgrade)
- **Tools**: File search with vector store
- **Vector Store**: Contains all curriculum documents from `knowledge_base/database_txt/`
- **Prompt**: `assistant_config/MASTER_PROMPT.md` (Current version)

## 🛠️ Development

### Adding New Tests
1. Use `tools/test_utils.py` for common functionality
2. Save results to `tests/results/`
3. Follow the established naming convention

### Updating the Prompt
1. Edit `assistant_config/MASTER_PROMPT.md`
2. Create backup version in `docs/development/MASTER_PROMPT_V[X].md`
3. Test with `python tests/test_citations_clean.py`
4. Deploy with `python tools/deploy_prompt.py`

### Knowledge Base Updates
1. Edit Markdown files in `knowledge_base/database/`
2. Update corresponding TXT files in `knowledge_base/database_txt/`
3. Verify with local tests before deployment

### Model Updates
1. Run model comparison tests
2. Update documentation with performance metrics
3. Deploy changes to production

## 📁 File Relationships

### Key Files & Their Purposes
- **`assistant_config/MASTER_PROMPT.md`**: Current production prompt (convenient access)
- **`index.yaml`**: Course structure for third-party applications (moved to root)
- **`knowledge_base/database/*.md`**: Source files (easier to maintain)
- **`knowledge_base/database_txt/*.txt`**: Vector store files (what OpenAI loads)
- **`docs/development/MASTER_PROMPT_V*.md`**: Version history and backups

### Redundancy by Design
- The current prompt exists both in `assistant_config/` and `docs/development/` (latest version)
- This redundancy is intentional: `assistant_config/` for quick access, `docs/development/` for versioning

## 🔒 Security

- **Never commit sensitive API keys**
- **Use `.env` file for local development**
- **Keep API keys secure** and rotate regularly
- **Monitor usage** for unexpected costs

## 📞 Support

For technical issues:
1. Check test results in `tests/results/`
2. Run diagnostic tools in `tools/`
3. Review documentation in `docs/`

## 🏆 Success Metrics

- **Zero Fabrications**: No invented information
- **Perfect Citations**: Full document attribution
- **Sales Ready**: Appropriate for live calls
- **Accurate Information**: 100% curriculum-based
- **Professional Tone**: Conversational but authoritative

---

*Last Updated: Current (V8 - Responses API Migration)*
*Status: Production Ready - Deployed with Responses API*