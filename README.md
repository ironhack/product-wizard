# 🧙‍♂️ Product Wizard - Ironhack Sales Enablement Assistant

> An AI-powered assistant that provides accurate, citation-backed information about Ironhack courses for sales teams during live calls with prospective students.

## 🎯 Overview

Product Wizard is a Slack-integrated assistant built on OpenAI's GPT-4o model with file search capabilities. It helps Ironhack's sales team provide accurate course information with proper citations during phone calls with prospects.

### Key Features
- ✅ **Zero Fabrication Policy** - Only provides documented information
- ✅ **Perfect Citations** - References specific curriculum documents
- ✅ **Sales-Ready Responses** - Conversational tone for phone calls
- ✅ **Variant Awareness** - Distinguishes Remote vs Berlin programs
- ✅ **Multi-Course Support** - All Ironhack bootcamps and programs

## 📁 Project Structure

```
product-wizard/
│
├── src/                     # 🚀 Main Application
│   ├── app.py              # Slack middleware application for Heroku
│   └── __init__.py         # Package initialization
│
├── assistant_config/        # 🤖 AI Assistant Configuration  
│   └── MASTER_PROMPT.md    # OpenAI Assistant prompt configuration
│
├── knowledge_base/          # 📚 Course Information Database
│   ├── database/           # Original curriculum files (.md format)
│   ├── database_txt/       # Processed curriculum files (.txt format)
│   └── index.yaml         # Course structure for web visualization
│
├── tests/                   # 🧪 Testing & Validation
│   ├── test_config.py      # Centralized test configuration with dotenv
│   ├── model_tests/        # Model comparison and upgrade tests
│   ├── results/            # Test output files
│   └── archive/            # Old test files
│
├── deployment/              # 🚀 Deployment Assets
│   ├── docs/               # Documentation and reports  
│   ├── Procfile           # Original Heroku process config
│   ├── requirements.txt   # Original Python dependencies
│   └── runtime.txt        # Original Python version spec
│
├── tools/                   # 🛠️ Utility Scripts
├── scripts/                # 📜 Helper Scripts  
├── archive/                # 📦 Archived Files
│
├── .env.example            # Environment variables template
├── Procfile               # Heroku deployment configuration
├── requirements.txt       # Python dependencies (includes dotenv)
├── runtime.txt           # Python version specification
└── README.md             # This documentation
```

## 🚀 Quick Start

### 1. Setup Environment Variables
```bash
# Copy environment variables template
cp .env.example .env

# Edit .env with your credentials
# - OPENAI_API_KEY
# - OPENAI_ASSISTANT_ID
# - SLACK_BOT_TOKEN (for Heroku deployment)
# - SLACK_SIGNING_SECRET (for Heroku deployment)
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application (Local Development)
```bash
python src/app.py
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

### Current Performance (V5)
- **Fabrication Rate**: 0% (Zero fabrications detected)
- **Citation Quality**: 9.3/10 (Excellent file attribution)
- **Sales Readiness**: 95% (Ready for production use)
- **Model**: GPT-4o (Latest OpenAI model)

### Key Achievements
- ✅ Eliminated all major fabrications (DevOps GCP/Jenkins, fake schedules)
- ✅ Perfect citations with full document names
- ✅ Variant-aware responses (Remote vs Berlin)
- ✅ Sales-appropriate conversational tone

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

### Environment Variables (config.py)
```python
# OpenAI Configuration
OPENAI_API_KEY = "your_api_key_here"
OPENAI_ASSISTANT_ID = "your_assistant_id_here"

# Slack Configuration (optional)
SLACK_BOT_TOKEN = "your_slack_token_here"
SLACK_SIGNING_SECRET = "your_signing_secret_here"
```

### Assistant Configuration
- **Model**: GPT-4o (latest OpenAI model)
- **Tools**: File search enabled
- **Vector Store**: Attached with all curriculum documents
- **Prompt**: MASTER_PROMPT.md (V5 Enhanced Citations)

## 📚 Documentation

### Development Reports
- **[Final Report](docs/reports/FINAL_REPORT.md)** - Complete project analysis
- **[Citations Report](docs/reports/CITATIONS_FINAL_REPORT.md)** - Citation system analysis
- **[Model Comparison](docs/reports/MODEL_COMPARISON_FINAL.md)** - GPT model testing results

### Development History
- **[Prompt Evolution](docs/development/)** - MASTER_PROMPT V1-V5 development
- **[Test Archive](tests/archive/)** - Historical test files

## 🛠️ Development

### Adding New Tests
1. Use `tools/test_utils.py` for common functionality
2. Save results to `tests/results/`
3. Follow the established naming convention

### Updating the Prompt
1. Edit `MASTER_PROMPT.md`
2. Test with `python tests/test_citations_clean.py`
3. Verify no regressions with full test suite

### Model Updates
1. Update `config.py` with new model name
2. Run model comparison tests
3. Update documentation with performance metrics

## 🔒 Security

- **Never commit config.py** (contains API keys)
- **Use config.example.py** as template
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

*Last Updated: Current (V5 Enhanced Citations)*
*Status: Production Ready*