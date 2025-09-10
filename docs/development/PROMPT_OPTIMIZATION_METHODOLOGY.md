# Prompt Optimization & Testing Methodology

**Created**: 2025-09-10  
**Updated**: 2025-09-10  
**Purpose**: Document the systematic framework for prompt optimization and testing using GPT-5 as judge  
**Status**: Production Ready - Core Framework  

## 📊 Overview

This methodology provides a systematic framework for **prompt optimization** using **GPT-5 as an impartial judge**. It can be applied to any unwanted behavior or performance issue, providing measurable results and iterative improvement.

## 🎯 Framework Application Process

### Step 1: Identify the Problem
When facing any unwanted behavior or performance issue:
1. **Document the specific issue** with examples
2. **Identify the root cause hypothesis** 
3. **Define expected vs actual behavior**

### Examples of Issues This Framework Addresses:
1. **Cross-contamination**: Mixing information from different programs/documents
2. **Fabrication**: Adding plausible but undocumented information  
3. **Search failures**: Not finding available information in documents
4. **Context issues**: Poor handling of follow-up questions
5. **Specificity problems**: Vague responses when specific information exists

### Step 2: Formulate Hypothesis
Based on the problem, create a hypothesis about what prompt changes might help.

### Example Problem & Hypothesis:
- **Issue**: "Assistant mixing certifications between different programs in Slack"
- **Hypothesis**: "Prompt needs stronger search guidance and cross-program isolation rules"
- **Expected**: Only mention certifications for the program asked about
- **Test Strategy**: Create questions that specifically target cross-program contamination

## 🔬 Framework Implementation

### Step 3: Apply Hypothesis to Prompt
Make targeted changes to the prompt based on your hypothesis:
- **Search improvements**: Better guidance for document search
- **Rule clarifications**: Stronger guidelines for specific behaviors  
- **Context handling**: Better instructions for follow-ups
- **Scope limitations**: Clearer boundaries on what to include/exclude

### Step 4: Design Strategic Test Questions

Create questions that specifically test your hypothesis:

#### Cross-contamination Test:
```
Question: "Programming languages in Data Science & Machine Learning bootcamp"
Purpose: Test if assistant mixes bootcamp with 1-year program
Expected: Only Python, SQL (from bootcamp curriculum)
```

#### Numerical Precision Test:
```
Question: "How many hours for Unit 3 in UX/UI Remote?"
Purpose: Test exact vs estimated numbers
Expected: Exact "32 hours" (not ~30 or "around 30")
```

#### Completeness Test:
```
Question: "AWS services in DevOps curriculum excluding Lambda/CloudFormation"
Purpose: Test comprehensive vs common assumption lists
Expected: Only documented services (EC2, S3, VPC, IAM, etc.)
```

#### Variant Confusion Test:
```
Question: "Programming languages in UX/UI Berlin bootcamp"
Purpose: Test assumptions about course content
Expected: HTML, CSS (documented) not assumption of "no programming"
```

### 2. Expected Answer Research

For each question, research factual answers using:

```bash
# Direct document search
grep "Unit 3.*32 hours" knowledge_base/database/UXUI_Remote_bootcamp_2025_07.md

# Tool/service extraction
grep "AWS|EC2|S3" knowledge_base/database/DevOps_bootcamp_2025_07.md

# Programming language search
grep -i "python|sql|javascript" knowledge_base/database/Data_Science_*.md
```

### Step 5: GPT-5 Judge Testing Pipeline

#### Test Implementation Template:
```python
def test_bias_case(question, expected_answer, rationale):
    # 1. Query assistant with MASTER_PROMPT
    assistant_response = query_assistant(question)
    
    # 2. Evaluate with GPT-5 judge
    evaluation = evaluate_with_gpt5(
        question=question,
        assistant_response=assistant_response,
        expected_answer=expected_answer,
        rationale=rationale
    )
    
    return evaluation
```

#### GPT-5 Judge Criteria:
```python
evaluation_criteria = {
    "accuracy": "Facts match documentation exactly",
    "completeness": "No missing required information",
    "precision": "No fabricated additions",
    "citations": "Proper source attribution", 
    "bias_risk": "BASSO/MEDIO/ALTO assessment"
}
```

### 4. Results Analysis

#### Scoring System:
- **10/10**: Perfect accuracy, no bias detected
- **8-9/10**: Minor additions, low bias risk
- **6-7/10**: Some fabrication, medium bias risk
- **1-5/10**: Major fabrication, high bias risk
- **0/10**: Complete failure or technical error

#### Bias Risk Assessment:
- **BASSO**: Minor context additions, factually correct
- **MEDIO**: Some assumptions, partially incorrect
- **ALTO**: Clear fabrication, cross-contamination

## 📈 Implementation Results

### Round 1 (Pre-optimization):
```json
{
  "data_science_languages": {
    "score": 6,
    "bias_risk": "ALTO",
    "issues": ["Added R, JavaScript, NoSQL not in curriculum"]
  },
  "cybersecurity_prework": {
    "score": 8, 
    "bias_risk": "ALTO",
    "issues": ["Missing specific '9x Labs, 5x Assessment' details"]
  },
  "aws_lambda_location": {
    "score": 6,
    "bias_risk": "ALTO", 
    "issues": ["Said 'Unit 2' instead of 'Unit 1'"]
  }
}
```

### Root Cause Discovery:
Vector search investigation revealed:
- Two different Data Science programs in vector store
- Cross-contamination between `bootcamp_2025_07.md` and `1_Year_Program_Germany_2025_07.md`
- Assistant mixing information from both documents

### Solution Implementation:
Enhanced MASTER_PROMPT with program disambiguation and search guidance:
```markdown
### CRITICAL: Program Disambiguation & Information Retrieval
**ALWAYS distinguish between these different Data Science programs:**
- **Data Science & Machine Learning bootcamp** (400 hours) - Python, SQL only
- **Data Science and AI 1-Year Program Germany** (1,582 hours) - Multiple languages
- **When asked about "Data Science", clarify which program** the user means

**NEVER hardcode specific details in the prompt - always retrieve information from documentation:**
- Use search tools to find current, accurate information
- Rely on vector search and document retrieval, not memorized facts
- Let the knowledge base be the single source of truth
```

### Round 2 (Post-optimization):
```json
{
  "average_score": 9.0,
  "score_range": "8-10",
  "high_bias_risk": 0,
  "low_bias_risk": 4,
  "improvements": [
    "Numerical precision: 10/10 (perfect)",
    "Service completeness: 8/10 (minimal bias)",
    "Project structure: 9/10 (excellent)",
    "Variant confusion: 9/10 (excellent)"
  ]
}
```

## 🛠️ Testing Files

### Core Test Files:
- `tests/test_bias_fabrication.py` - Original bias detection with 4 strategic questions
- `tests/test_bias_fabrication_round2.py` - Validation with 4 new questions  
- `tests/test_vector_search_investigation.py` - Root cause analysis tool

### Usage:
```bash
# Run bias detection tests
python tests/test_bias_fabrication.py
python tests/test_bias_fabrication_round2.py

# Investigate vector search behavior
python tests/test_vector_search_investigation.py
```

### Results Storage:
- All results saved to `tests/results/bias_detection_results_YYYYMMDD_HHMMSS.json`
- Includes detailed GPT-5 evaluations and bias analysis
- Preserved for future comparison and regression testing

## 🔄 Continuous Integration

### Pre-deployment Testing:
1. Run bias detection tests before any MASTER_PROMPT changes
2. Require 8/10+ average score before deployment
3. Investigate any new HIGH bias risk patterns

### Regression Prevention:
1. Preserve all test files (never delete)
2. Add new test cases when bias patterns are discovered
3. Regular re-testing with historical questions

### Quality Gates:
- **Deployment Blocker**: Average score < 7/10
- **Investigation Required**: Any HIGH bias risk results
- **Acceptable**: BASSO bias risk with score 8+

## 💡 Best Practices

### Information Retrieval Principles:
1. **Never hardcode answers in prompts** - always rely on document search
2. **Teach search strategies** rather than specific facts
3. **Emphasize knowledge base as single source of truth**
4. **Guide retrieval behavior** rather than providing fallback information
5. **Test that assistant searches properly** rather than relying on prompt knowledge

### Question Design:
1. **Target specific vulnerabilities** in your prompt/system
2. **Use real curriculum edge cases** that might cause confusion
3. **Test cross-contamination** between similar documents/programs
4. **Include control questions** where "I don't know" is correct

### Expected Answer Creation:
1. **Research in actual source documents** - never assume
2. **Use grep/search** to find exact text and numbers
3. **Quote directly** from source material when possible
4. **Include document references** in expected answers

### GPT-5 Judge Optimization:
1. **Specific evaluation criteria** for your domain
2. **Clear scoring rubric** (1-10 with specific meanings)  
3. **JSON response format** for easy parsing
4. **Domain-specific bias categories** relevant to your use case

### Results Analysis:
1. **Track trends over time** - regression detection
2. **Categorize bias types** - systematic improvement
3. **Root cause investigation** for unexpected results
4. **Document improvements** for future reference

## 🎯 Future Applications

This methodology can be adapted for:
- **Educational content** accuracy validation
- **Technical documentation** consistency checking  
- **Customer service** response quality control
- **Content moderation** bias detection
- **Multi-language** consistency validation

## 📚 References

- [OpenAI Responses API Documentation](https://platform.openai.com/docs)
- [Vector Search Best Practices](https://platform.openai.com/docs/assistants/tools/file-search)
- [GPT-4o Model Specifications](https://platform.openai.com/docs/models/gpt-4o)

---

*This methodology successfully improved Product Wizard assistant accuracy from 6/10 to 9/10 average scores, eliminating major fabrication patterns and ensuring reliable sales enablement responses.*
