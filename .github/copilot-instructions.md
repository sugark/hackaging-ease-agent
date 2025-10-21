## Gemini API Usage Patterns


The `ease_agent` codebase uses the Google Gemini API for LLM-powered biomedical analysis, classification, and data extraction. Follow these conventions for all Gemini API usage:

- **Import and Initialization**:
    - Import as `from google import genai` and `from google.genai import types`.
    - Always load environment variables with `from dotenv import load_dotenv; load_dotenv()` before accessing the API key.
    - Configure the Gemini client with `genai.Client()` or `genai.configure(api_key=...)` as needed.
    - The API key should be read from the environment variable `GOOGLE_API_KEY` (set in `.env`).

- **Model Selection**:
    - Use `gemini-flash-latest` or `gemini-2.5-pro` as the model name, depending on the script's requirements.
    - Set model and temperature explicitly when needed (e.g., `temperature=0` for deterministic output).

- **Prompt Management**:
    - Store system and task prompts as separate `.py` files with docstrings.
    - Load and parse prompt templates at runtime, extracting the docstring content for use as the system prompt.
    - Format prompts with context-specific variables (e.g., selected clinical test, recommended cohorts).

- **Error Handling & Retry**:
    - Always implement retry logic for transient API errors (e.g., HTTP 429, 503) using exponential backoff or the `google.api_core.retry` module.
    - Log all API errors and warnings using the `logging` module.
- **Context Caching**:
    - Use Gemini context caching for efficient repeated analysis of the same article or document, when appropriate for the use case.
    - Context caching is optional and should be applied when it improves performance or reduces redundant API calls.

- **Batch Processing**:
    - For large-scale tasks, process articles or data in batches and respect API rate limits.
    - Use environment variables to configure batch size and delay between requests.

- **Security**:
    - Never hardcode API keys; always use environment variables and `.env` files.

- **Example Initialization Pattern**:
    ```python
    from dotenv import load_dotenv
    load_dotenv()
    import os
    from google import genai
    api_key = os.getenv('GOOGLE_API_KEY')
    client = genai.Client(api_key=api_key)
    ```

Follow these patterns for all Gemini API integration to ensure security, reproducibility, and maintainability.
budapest_hackathlon/
├── agent.py                   # Google AI agent definition (time tool example)
├── tools/
│   ├── pubmed/
│   │   ├── pubmed_search.py   # Main PubMed search implementation
│   │   └── test/              # Examples and tests
│   └── doi_downloader/        # Empty tool directory for expansion

# Copilot Instructions - ease_agent

## Project Overview

The `ease_agent` directory is a comprehensive biomedical research automation platform that enables systematic literature review, meta-analysis, and data extraction workflows. Built for reproducible scientific research, the codebase integrates advanced AI capabilities with robust data processing to streamline academic research tasks.

**Core Capabilities:**
- Automated PubMed literature search and retrieval
- AI-powered article classification and filtering
- Clinical data extraction for meta-analysis
- PDF download and document processing
- Statistical analysis and report generation

### AI Pipeline Architecture

This is an **AI Pipeline without frameworks** like LangChain or Google ADK. The design philosophy prioritizes simplicity and debuggability for first-time AI pipeline development:

**Pipeline Design Principles:**
- **Standalone Steps**: Each pipeline step runs as an independent main application
- **JSON State Management**: State/session/memory between steps is stored in JSON files
- **Framework-Free**: No complex AI frameworks - direct API calls for transparency
- **Debug-Friendly**: Easy to debug individual steps and inspect intermediate states
- **Migration Path**: Designed for later migration to advanced AI agent frameworks with fine-tuning

**Benefits of This Approach:**
- Clear understanding of each processing step
- Simple debugging and error isolation
- Transparent data flow between components
- Educational value for learning AI pipeline concepts
- Easy to modify and extend individual steps

---

## Development Philosophy

### Code Quality Standards
- **Python Standards**: Strict adherence to PEP8 formatting with 4-space indentation
- **Type Safety**: Comprehensive type hints for all function signatures and return values
- **Documentation**: Detailed docstrings for every module, class, and function explaining purpose, parameters, and behavior
- **Robustness**: Defensive programming with comprehensive error handling and graceful failure modes

### Architectural Principles
- **Class-Based Design**: Major functionality organized into well-defined classes with clear responsibilities
- **Data Classes**: Use `@dataclass` for structured data containers (e.g., `DownloadResult`, `PubMedArticle`, `CandidateArticle`)
- **Separation of Concerns**: Distinct modules for search, classification, extraction, and analysis workflows
- **Configuration Management**: Environment-based configuration using `.env` files for secrets and settings

---

## Google Gemini API Integration

### Standard Implementation Pattern
```python
from dotenv import load_dotenv
load_dotenv()
import os
from google import genai
from google.genai import types

# Always use environment variables for API keys
api_key = os.getenv('GOOGLE_API_KEY')
client = genai.Client(api_key=api_key)
```

### Model Configuration
- **Primary Models**: Use `gemini-flash-latest` for general tasks, `gemini-2.5-pro` for complex analysis
- **Temperature Control**: Set explicit temperature values (`temperature=0` for deterministic outputs)
- **Prompt Engineering**: Store system prompts as separate `.py` files with docstring content extraction

### Reliability Features
- **Mandatory Retry Logic**: Always implement retry mechanisms for API rate limits (HTTP 429, 503)
- **Context Caching**: Apply when processing the same documents multiple times to optimize performance
- **Batch Processing**: Process large datasets in configurable batches with rate limiting
- **Error Logging**: Use the logging framework for all API interactions and error states

---

## Environment & Dependencies

### Core Libraries
```python
# Standard library essentials
import os, json, logging, argparse, pathlib, datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Third-party requirements
from dotenv import load_dotenv          # Environment management
import requests, httpx                  # HTTP operations  
from Bio import Entrez                  # PubMed/NCBI integration
from google import genai               # Gemini API
import pandas as pd                    # Data analysis (optional)
from md2pdf.core import md2pdf         # PDF generation
from scidownl import scihub_download   # Academic paper downloads
from bs4 import BeautifulSoup         # HTML parsing
```

### Configuration Management
- **Environment Loading**: Always call `load_dotenv()` at script initialization
- **Required Secrets**: `GOOGLE_API_KEY`, `NCBI_EMAIL` stored in `.env` files
- **Directory Configuration**: Use environment variables for paths (e.g., `DOI_PDFS_DIR`)
- **Conda Environment**: Use `conda activate hackathlon` for consistent Python environment

---

## Script Structure & CLI Design

### Standard Script Template
```python
#!/usr/bin/env python3
"""
Module Description: Purpose, workflow, and usage summary.

CLI Usage Examples:
# Basic usage
python script.py --input data.json

# Advanced options  
python script.py --mode advanced --output results.csv

Dependencies: list required packages
Environment: required environment variables
"""

# Standard imports and setup
import logging
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Entry point with argument parsing and workflow coordination."""
    parser = argparse.ArgumentParser(description='Clear description')
    # Add arguments with help text
    args = parser.parse_args()
    
    # Main workflow implementation
    
if __name__ == "__main__":
    main()
```

### CLI Best Practices
- **Argument Parser**: Use `argparse` with comprehensive help text and usage examples
- **Usage Documentation**: Include CLI examples as comments at the top of each script
- **Default Values**: Provide sensible defaults for optional parameters
- **Validation**: Validate inputs and provide clear error messages

---

## Logging & Error Management

### Logging Framework
- **Primary Tool**: Use `logging` module exclusively for status, progress, and error messages
- **Output Restrictions**: Never use `print()` except for direct user-facing CLI output
- **Log Levels**: INFO for progress, WARNING for recoverable issues, ERROR for failures
- **Formatting**: Consistent timestamp and level formatting across all modules

### Error Handling Strategy
- **Defensive Programming**: Wrap all file I/O, network calls, and API requests in try/except blocks
- **Graceful Degradation**: Continue processing when possible, log errors and skip problematic items
- **Context Preservation**: Include relevant context (file paths, API endpoints, data identifiers) in error messages
- **User Communication**: Provide actionable error messages with suggestions for resolution

---

## Testing & Quality Assurance

### Test Organization
- **Location**: All tests in `tools/*/test/` directories
- **Framework**: Use `unittest` for structured test cases
- **Execution**: Tests should be runnable as standalone scripts
- **Coverage**: Include both unit tests and integration examples

### Test Categories
- **Offline Tests**: Validate core logic without external dependencies
- **Mock Tests**: Use temporary directories and mocked network calls
- **Integration Examples**: Demonstrate real usage patterns with live APIs
- **Import Validation**: Ensure all dependencies are correctly installed

---

## Data Processing Conventions

### File Format Standards
- **Encoding**: Always use UTF-8 for text file operations
- **CSV Handling**: Use semicolon separators for multi-value fields, handle missing data gracefully
- **JSON Structure**: Consistent field naming and nested structure patterns
- **PDF Processing**: Validate file headers and content types

### Batch Processing Guidelines
- **Rate Limiting**: Implement delays between API calls (configurable via environment variables)
- **Progress Tracking**: Log batch progress and completion statistics
- **Failure Resilience**: Continue processing remaining items when individual operations fail
- **Memory Management**: Process large datasets in manageable chunks

This guide ensures consistent, maintainable, and robust code development across the entire `ease_agent` research automation platform.

---

## Code Style & Structure

- **PEP8**: Follow PEP8 for formatting, indentation (4 spaces), and naming conventions.
- **Docstrings**: Every module, class, and function must have a clear, descriptive docstring explaining its purpose and usage.
- **Type Hints**: Use Python type hints for all function arguments and return values.
- **Logging**: Always use the `logging` module for all status, error, and progress messages. Do not use `print()` for output except for direct CLI user feedback.
- **Error Handling**: Always handle file, network, and API errors gracefully with try/except and informative messages.
- **Main Function**: All executable scripts must use a `main()` function and the `if __name__ == "__main__": main()` pattern.
- **CLI**: Use `argparse` for command-line interfaces. Provide clear help messages and usage examples as comments at the top of scripts.
- **Environment Variables**: Use `python-dotenv` (`from dotenv import load_dotenv`) to load secrets and configuration from `.env` files. Always call `load_dotenv()` before accessing environment variables.
- **Class Design**: Use classes for all major components (e.g., data extractors, downloaders, analyzers). Use `@dataclass` for simple data containers.
- **Test Organization**: Place all tests in `tools/*/test/` directories. Use `unittest` for test cases and provide CLI test runners.

---

## Libraries & Dependencies

- **Core**: `os`, `json`, `logging`, `argparse`, `pathlib`, `datetime`, `typing`, `dataclasses`
- **Third-party**: 
    - `python-dotenv` for environment management
    - `requests`, `httpx` for HTTP
    - `biopython` for PubMed/NCBI
    - `google-generativeai` for Gemini API
    - `pandas`, `numpy` for data analysis (optional)
    - `md2pdf` for PDF generation
    - `scidownl`, `beautifulsoup4` for DOI/PDF downloaders

---

## Environment & Configuration

- Always load environment variables at the start of scripts:
    ```python
    from dotenv import load_dotenv
    load_dotenv()
    ```
- Required secrets (e.g., `GOOGLE_API_KEY`, `NCBI_EMAIL`) must be set in `.env` and accessed via `os.getenv`.
- Download/output directories can be configured via environment variables (e.g., `DOI_PDFS_DIR`).

---

## Class & Function Patterns

- **Data Classes**: Use `@dataclass` for result and entity containers (e.g., `DownloadResult`, `PubMedArticle`, `CandidateArticle`).
- **Component Classes**: Each major workflow (e.g., article processing, cohort analysis, PDF download) is encapsulated in a class with clear methods and initialization.
- **Prompt Templates**: System and task prompts for LLMs are stored as separate `.py` files with docstrings, loaded and parsed at runtime.

---

## Commenting & Documentation

- Each script starts with a module-level docstring summarizing its purpose, workflow, and CLI usage.
- Each class and function has a docstring describing its arguments, return values, and side effects.
- Inline comments are used sparingly, only to clarify non-obvious logic.

---

## Example Main Function Pattern

```python
def main():
        """Entry point for the script."""
        # ... argument parsing, setup, workflow calls ...

if __name__ == "__main__":
        main()
```

---

## Testing

- Tests are written using `unittest` and placed in `tools/*/test/`.
- Test files include usage examples and can be run directly as scripts.
- Use temporary directories and mocks for file/network operations in tests.

---

## Additional Conventions

- **Retry Logic**: For network/API calls, implement retry with exponential backoff for transient errors.
- **Batch Processing**: For large datasets or API calls, process in batches and respect rate limits.
- **CSV/JSON I/O**: Always use UTF-8 encoding and handle missing/invalid data gracefully.
- **CLI Help**: Provide usage examples as comments at the top of each script.

---

This style guide ensures all code in `ease_agent` is robust, maintainable, and ready for collaborative research automation.