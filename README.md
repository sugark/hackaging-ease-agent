# EASE Agent: AI-Powered Biomedical Meta-Analysis Pipeline

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Conda](https://img.shields.io/badge/conda-required-green.svg)](https://docs.conda.io/en/latest/)

**EASE Agent** is a comprehensive biomedical research automation platform that enables systematic literature review, meta-analysis, and data extraction workflows. Built for reproducible scientific research, the platform integrates advanced AI capabilities with robust data processing to streamline academic research tasks from literature search to publication-ready reports.

## 🔬 Features

### Core Capabilities
- **Automated Literature Search**: Intelligent PubMed query generation and article retrieval
- **AI-Powered Classification**: Multi-dimensional article analysis including study type, population, and bias assessment
- **Clinical Data Extraction**: Systematic extraction of quantitative data for meta-analysis
- **Statistical Analysis**: Automated meta-analysis with forest plots and heterogeneity assessment
- **Publication-Ready Reports**: Professional PDF generation with PRISMA-compliant documentation

### AI Pipeline Architecture
- **Framework-Free Design**: Direct API calls for transparency and debuggability
- **Standalone Steps**: Each pipeline component runs independently for easy debugging
- **JSON State Management**: Persistent state tracking between processing steps
- **Modular Workflow**: Easy to modify, extend, or debug individual components

## 🚀 Quick Start

### Prerequisites

1. **Conda Environment**
   ```bash
   conda create -n hackathlon-ease-agent python=3.13
   conda activate hackathlon-ease-agent
   ```

2. **API Keys**
   - Google Gemini API key for AI processing
   - NCBI email for PubMed access

3. **Environment Configuration**
   ```bash
   cp .env.sample .env
   # Edit .env with your API keys and configuration
   ```

### Installation

```bash
# Clone the repository
git clone https://github.com/sugark/hackaging-ease-agent.git
cd hackaging-ease-agent/ease_agent

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Configure your `.env` file with the following required variables:

```bash
# Google AI Configuration
GOOGLE_API_KEY=your_gemini_api_key_here
GOOGLE_GENAI_USE_VERTEXAI=FALSE

# NCBI/PubMed Configuration  
NCBI_EMAIL=your_email@example.com

# Processing Configuration
MAX_RESULTS_PER_QUERY=100
BATCH_SIZE=50
```

### Basic Usage

1. **Define Research Topic**
   ```bash
   echo "Your research question here" > _input_topic.md
   ```

2. **Run Complete Pipeline**
   ```bash
   ./_run_all_at_once.sh
   ```

3. **Review Results**
   - Statistical analysis: `_meta_analysis_output.txt`
   - Forest plots: `_meta_analysis_forest_*.png`
   - Final reports: `_advanced_documentation.md` and PDF versions

## 📋 Pipeline Overview

The EASE Agent pipeline consists of 12 sequential steps:

| Step | Component | Input | Output | Purpose |
|------|-----------|-------|--------|---------|
| 1 | `pubmed_generate_search.py` | `_input_topic.md` | `_pubmed_generate_search_out.json` | Generate optimized PubMed search queries |
| 2 | `pubmed_fetch_meta.py` | Search queries | `_pubmed_fetched_meta_results.json` | Retrieve article metadata from PubMed |
| 3 | `pubmed_filter_abstracts.py` | Article metadata | `_pubmed_filtered_articles.json` | AI-powered abstract relevance filtering |
| 4 | `pubmed_download_articles.py` | Filtered articles | `downloaded_articles/` | Download full-text PDFs |
| 5 | `gemini_classify_articles.py` | Downloaded articles | `_classified_articles.json` | Multi-dimensional article classification |
| 6 | `cohorts_and_tests_list.py` | Classified articles | `_cohorts_and_tests.csv` | Extract study populations and outcome measures |
| 7 | `cohorts_and_tests_suggest_analysis.py` | Cohorts and tests | `_suggested_analysis.json` | AI-recommended meta-analysis strategy |
| 8 | `gemini_extract_datapoints.py` | Analysis strategy | `_extracted_datapoints.csv` | Extract quantitative clinical data |
| 9 | `run_meta_analysis.py` | Extracted data | Statistical outputs | Perform meta-analysis with forest plots |
| 10 | `write_final_documentation.py` | Analysis results | `_draft_documentation.md` | Generate initial report |
| 11 | `write_final_documentation_advanced.py` | All outputs | `_advanced_documentation.md` | Create comprehensive publication-ready report |
| 12 | `write_final_documentation_into_pdf.py` | Documentation | PDF reports | Convert to professional PDF format |

## 🛠 Individual Component Usage

### Generate Search Queries
```bash
python pubmed_generate_search.py --topic "your research question"
```

### Fetch PubMed Metadata
```bash
python pubmed_fetch_meta.py --queries _pubmed_generate_search_out.json
```

### Classify Articles
```bash
python gemini_classify_articles.py --input _pubmed_downloaded_articles.json
```

### Extract Clinical Data
```bash
python gemini_extract_datapoints.py --strategy _suggested_analysis.json
```

### Run Meta-Analysis
```bash
python run_meta_analysis.py --data _extracted_datapoints.csv
```

## 📊 Output Files

### Primary Outputs
- **`_meta_analysis_output.txt`**: Complete statistical analysis results
- **`_meta_analysis_forest_*.png`**: Forest plots for visual interpretation
- **`_advanced_documentation.md`**: Comprehensive research report
- **PDF Reports**: Publication-ready formatted documents

### Intermediate Data
- **`_classified_articles.json`**: AI classification results
- **`_extracted_datapoints.csv`**: Quantitative data for analysis
- **`_cohorts_and_tests.csv`**: Study population catalog
- **`_suggested_analysis.json`**: AI-recommended analysis strategy

### Raw Data
- **`_pubmed_fetched_meta_results.json`**: PubMed search results
- **`downloaded_articles/`**: Full-text PDF collection

## 🏗 Architecture

### Design Philosophy
- **Transparency**: Direct API calls without complex frameworks
- **Debuggability**: Standalone components for easy troubleshooting
- **Modularity**: Independent steps with clear input/output contracts
- **Reproducibility**: JSON state management for workflow tracking

### AI Integration
- **Google Gemini API**: Primary AI engine for classification and extraction
- **Prompt Engineering**: Systematic prompt templates for consistent results
- **Context Caching**: Efficient processing of repeated document analysis
- **Error Handling**: Robust retry logic for API reliability

### Data Processing
- **Batch Processing**: Configurable batch sizes for large datasets
- **Rate Limiting**: Respectful API usage with built-in delays
- **Error Recovery**: Graceful handling of failed downloads and API errors
- **Progress Tracking**: Comprehensive logging throughout the pipeline

## 🧪 Example Research Topics

The pipeline has been tested with various biomedical research questions:

- "Resveratrol supplementation and type 2 diabetes: a systematic review and meta-analysis"
- "Omega-3 fatty acids in cardiovascular disease prevention"
- "Vitamin D supplementation and immune function"
- "Mediterranean diet and cognitive decline"

## 📈 Statistical Capabilities

### Meta-Analysis Features
- **Effect Size Calculation**: Standardized mean differences, odds ratios, risk ratios
- **Heterogeneity Assessment**: I² statistics and forest plot visualization
- **Subgroup Analysis**: Automated stratification by study characteristics
- **Publication Bias**: Funnel plots and statistical tests
- **Sensitivity Analysis**: Leave-one-out and influence diagnostics

### Supported Study Types
- Randomized Controlled Trials (RCTs)
- Observational studies (cohort, case-control)
- Cross-sectional studies
- Systematic reviews (data extraction)

## 🔧 Configuration

### Processing Parameters
```bash
# .env configuration options
MAX_RESULTS_PER_QUERY=100    # Maximum articles per search query
BATCH_SIZE=50                # Articles processed per batch
RETRY_ATTEMPTS=3             # API retry attempts
DELAY_BETWEEN_REQUESTS=1     # Seconds between API calls
```

### AI Model Settings
- **Primary Model**: `gemini-2.5-pro` for complex analysis
- **Secondary Model**: `gemini-flash-latest` for classification tasks
- **Temperature**: `0` for deterministic outputs
- **Context Caching**: Enabled for repeated document analysis

## 🚨 Troubleshooting

### Common Issues

**API Rate Limits**
```bash
# Increase delays in .env
DELAY_BETWEEN_REQUESTS=2
```

**PDF Download Failures**
```bash
# Check DOI resolver and access permissions
# Review download logs in _pubmed_download.log
```

**Memory Issues with Large Datasets**
```bash
# Reduce batch size
BATCH_SIZE=25
```

**Environment Activation**
```bash
# Ensure conda environment is properly activated
conda activate hackathlon-ease-agent
which python  # Should point to conda environment
```

### Debug Mode
```bash
# Run individual components with verbose logging
python -v pubmed_generate_search.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP8 formatting standards
- Include comprehensive docstrings
- Add type hints for all functions
- Use the logging framework (not print statements)
- Test with multiple research topics

## 📚 Citation

If you use EASE Agent in your research, please cite:

```bibtex
@software{ease_agent_2024,
  title={EASE Agent: AI-Powered Biomedical Meta-Analysis Pipeline},
  author={sugark},
  year={2024},
  url={https://github.com/sugark/hackaging-ease-agent}
}
```

## 🎯 Roadmap

### Upcoming Features
- [ ] Integration with additional databases (Cochrane, Embase)
- [ ] Support for non-English literature
- [ ] Real-time collaboration features
- [ ] Advanced visualization dashboard
- [ ] Machine learning model fine-tuning
- [ ] Clinical trial registry integration

### Performance Improvements
- [ ] Parallel processing for large datasets
- [ ] Advanced caching mechanisms
- [ ] GPU acceleration for AI models
- [ ] Distributed processing support

## 📞 Support

- **Documentation**: See individual script docstrings for detailed usage
- **Issues**: Report bugs and feature requests via [GitHub Issues](https://github.com/sugark/hackaging-ease-agent/issues)
- **Discussions**: Join community discussions for research collaboration
- **Repository**: [https://github.com/sugark/hackaging-ease-agent](https://github.com/sugark/hackaging-ease-agent)

---

**Built for reproducible biomedical research** 🔬📊📈