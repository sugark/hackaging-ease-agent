#!/bin/bash

# ==============================================================================
# EASE AGENT - Complete Meta-Analysis Pipeline Runner
# ==============================================================================
# 
# This script executes the complete biomedical meta-analysis workflow from
# topic definition through final PDF report generation. The pipeline consists
# of multiple sequential steps that process scientific literature through:
# 1. Search query generation
# 2. PubMed literature retrieval
# 3. Abstract filtering and article download
# 4. AI-powered article classification
# 5. Clinical data extraction
# 6. Statistical meta-analysis
# 7. Comprehensive report generation
#
# Prerequisites:
# - Conda environment 'hackathlon-ease-agent' must be available
# - All required Python dependencies in requirements.txt
# - Environment variables configured (.env file with API keys)
# - Internet connection for PubMed and AI API access
#
# Usage: ./_run_all_at_once.sh
# 
# Output: Complete meta-analysis with PDF report and supporting files
# ==============================================================================

# ------------------------------------------------------------------------------
# ENVIRONMENT SETUP
# ------------------------------------------------------------------------------

echo "=== Initializing EASE Agent Meta-Analysis Pipeline ==="
echo "Timestamp: $(date)"

# Activate the dedicated conda environment for this project
echo "Activating conda environment: hackathlon-ease-agent"
conda activate hackathlon-ease-agent

# Install/update all required Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# ------------------------------------------------------------------------------
# PIPELINE CONFIGURATION
# ------------------------------------------------------------------------------

# Configure the research topic for meta-analysis
# This defines the central research question that drives all subsequent steps
echo "Configuring meta-analysis topic..."
echo "Resveratrol supplementation and type 2 diabetes: a systematic review and meta-analysis" > _input_topic.md
echo "Research topic configured: $(cat _input_topic.md)"

echo ""
echo "=== Starting Meta-Analysis Pipeline ==="
echo ""

# ------------------------------------------------------------------------------
# STEP 1: SEARCH QUERY GENERATION
# ------------------------------------------------------------------------------

echo "STEP 1: Generating PubMed search queries..."
echo "Input:  _input_topic.md"
echo "Output: _pubmed_generate_search_out.json"
echo "Purpose: Convert research topic into optimized PubMed search terms"
# 
# This step uses AI to transform the research topic into multiple targeted
# search queries optimized for PubMed's search syntax and medical subject headings
python pubmed_generate_search.py

echo "✓ Search queries generated successfully"
echo ""

# ------------------------------------------------------------------------------
# STEP 2: PUBMED LITERATURE RETRIEVAL
# ------------------------------------------------------------------------------

echo "STEP 2: Executing PubMed literature search..."
echo "Input:  _pubmed_generate_search_out.json"
echo "Output: _pubmed_fetched_meta_results.json"
echo "Purpose: Retrieve article metadata from PubMed using generated queries"
#
# This step executes the generated search queries against PubMed's API,
# retrieving article metadata including titles, abstracts, authors, and DOIs
python pubmed_fetch_meta.py
echo "✓ PubMed search completed successfully"
echo ""

# ------------------------------------------------------------------------------
# STEP 3: ABSTRACT FILTERING
# ------------------------------------------------------------------------------

echo "STEP 3: Filtering articles by abstract relevance..."
echo "Input:  _pubmed_fetched_meta_results.json"
echo "Output: _pubmed_filtered_articles.json"
echo "Purpose: AI-powered filtering to identify most relevant articles"
#
# This step uses AI to analyze article abstracts and filter out irrelevant
# studies, focusing on those most likely to contain useful meta-analysis data
python pubmed_filter_abstracts.py
echo "✓ Abstract filtering completed successfully"
echo ""

# ------------------------------------------------------------------------------
# STEP 4: FULL-TEXT ARTICLE DOWNLOAD
# ------------------------------------------------------------------------------

echo "STEP 4: Downloading full-text articles..."
echo "Input:  _pubmed_filtered_articles.json, _pubmed_fetched_meta_results.json"
echo "Output: _pubmed_downloaded_articles.json, downloaded_articles/"
echo "Purpose: Retrieve full-text PDFs for detailed analysis"
#
# This step attempts to download full-text articles using multiple methods:
# - DOI resolution to publisher sites
# - Open access repositories
# - Alternative academic sources
# Downloaded PDFs are stored in the downloaded_articles/ directory
python pubmed_download_articles.py
echo "✓ Article download completed successfully"
echo ""

# ------------------------------------------------------------------------------
# STEP 5: AI-POWERED ARTICLE CLASSIFICATION
# ------------------------------------------------------------------------------

echo "STEP 5: Classifying articles with AI analysis..."
echo "Input:  _pubmed_downloaded_articles.json"
echo "Output: _classified_articles.json"
echo "Purpose: Classify study types, populations, and data quality"
#
# This step uses multiple AI classifiers to analyze each article:
# - Study type (RCT, observational, review, etc.)
# - Population characteristics (age, health status, demographics)
# - Data quality and bias assessment
# - Methodological rigor evaluation
python gemini_classify_articles.py --max-articles 200
echo "✓ Article classification completed successfully"
echo ""

# ------------------------------------------------------------------------------
# STEP 6: COHORT AND TEST IDENTIFICATION
# ------------------------------------------------------------------------------

echo "STEP 6: Identifying available cohorts and clinical tests..."
echo "Input:  _classified_articles.json"
echo "Output: _cohorts_and_tests.csv"
echo "Purpose: Extract all available study populations and outcome measures"
#
# This step systematically extracts and catalogs:
# - All study cohorts and their characteristics
# - Clinical tests and outcome measures used
# - Sample sizes and demographic information
# - Data availability for potential meta-analysis
python cohorts_and_tests_list.py
echo "✓ Cohort and test identification completed successfully"
echo ""

# ------------------------------------------------------------------------------
# STEP 7: META-ANALYSIS STRATEGY SUGGESTION
# ------------------------------------------------------------------------------

echo "STEP 7: Generating meta-analysis strategy recommendations..."
echo "Input:  _cohorts_and_tests.csv"
echo "Output: _suggested_analysis.json"
echo "Purpose: AI-powered recommendations for optimal meta-analysis approach"
#
# This step analyzes available data to suggest:
# - Most promising outcome measures for meta-analysis
# - Appropriate statistical methods (fixed/random effects)
# - Potential subgroup analyses
# - Data extraction priorities
python cohorts_and_tests_suggest_analysis.py
echo "✓ Meta-analysis strategy generated successfully"
echo ""

# ------------------------------------------------------------------------------
# STEP 8: CLINICAL DATA EXTRACTION
# ------------------------------------------------------------------------------

echo "STEP 8: Extracting clinical datapoints for meta-analysis..."
echo "Input:  _suggested_analysis.json, _classified_articles.json"
echo "Output: _extracted_datapoints.csv"
echo "Purpose: Extract quantitative data required for statistical analysis"
#
# This step performs targeted data extraction based on the suggested analysis:
# - Primary and secondary outcome measures
# - Sample sizes and demographic data
# - Effect sizes, confidence intervals, p-values
# - Study-specific characteristics for subgroup analysis
python gemini_extract_datapoints.py
echo "✓ Clinical data extraction completed successfully"
echo ""

# ------------------------------------------------------------------------------
# STEP 9: STATISTICAL META-ANALYSIS
# ------------------------------------------------------------------------------

echo "STEP 9: Performing statistical meta-analysis..."
echo "Input:  _extracted_datapoints.csv"
echo "Output: _meta_analysis_output.txt, _meta_analysis_forest_plot.png"
echo "Purpose: Execute statistical meta-analysis with forest plots"
#
# This step performs the core statistical analysis:
# - Calculate pooled effect sizes using appropriate models
# - Generate forest plots for visual representation
# - Assess heterogeneity between studies
# - Perform sensitivity and subgroup analyses
# - Test for publication bias
python run_meta_analysis.py
echo "✓ Statistical meta-analysis completed successfully"
echo ""

# ------------------------------------------------------------------------------
# STEP 10: DRAFT DOCUMENTATION GENERATION
# ------------------------------------------------------------------------------

echo "STEP 10: Creating draft documentation..."
echo "Input:  _meta_analysis_output.txt, _meta_analysis_forest_plot.png"
echo "Output: _draft_documentation.md"
echo "Purpose: Generate initial structured report of findings"
#
# This step creates a preliminary report including:
# - Executive summary of findings
# - Methodology description
# - Statistical results and interpretation
# - Visual representations (forest plots)
# - Basic discussion of clinical implications
python write_final_documentation.py
echo "✓ Draft documentation generated successfully"
echo ""

# ------------------------------------------------------------------------------
# STEP 11: ADVANCED DOCUMENTATION ENHANCEMENT
# ------------------------------------------------------------------------------

echo "STEP 11: Creating comprehensive advanced documentation..."
echo "Input:  Multiple pipeline outputs and configuration files"
echo "Output: _advanced_documentation.md"
echo "Purpose: Generate publication-ready comprehensive report"
#
# This step creates an enhanced report incorporating:
# - Complete methodology transparency
# - Detailed statistical analysis
# - Quality assessment and bias evaluation
# - Clinical significance discussion
# - Limitations and future research directions
# - PRISMA-compliant systematic review structure
python write_final_documentation_advanced.py
echo "✓ Advanced documentation generated successfully"
echo ""

# ------------------------------------------------------------------------------
# STEP 12: PDF REPORT GENERATION
# ------------------------------------------------------------------------------

echo "STEP 12: Converting documentation to PDF format..."
echo "Input:  _draft_documentation.md, _advanced_documentation.md"
echo "Output: Final PDF reports"
echo "Purpose: Create publication-ready PDF documents"
#
# This final step converts the markdown documentation to professionally
# formatted PDF reports suitable for:
# - Academic publication submission
# - Clinical decision-making support
# - Regulatory submission documentation
# - Stakeholder communication
python write_final_documentation_into_pdf.py --mode draft
python write_final_documentation_into_pdf.py --mode advanced
echo "✓ PDF reports generated successfully"
echo ""

# ------------------------------------------------------------------------------
# PIPELINE COMPLETION
# ------------------------------------------------------------------------------

echo "=== EASE Agent Meta-Analysis Pipeline Completed Successfully ==="
echo "Completion timestamp: $(date)"
echo ""
echo "Generated Outputs:"
echo "  📊 Statistical Analysis: _meta_analysis_output.txt"
echo "  📈 Forest Plot: _meta_analysis_forest_plot.png" 
echo "  📄 Draft Report: _draft_documentation.md"
echo "  📋 Advanced Report: _advanced_documentation.md"
echo "  📁 PDF Reports: Available in output directory"
echo "  💾 Raw Data: _extracted_datapoints.csv"
echo "  🔍 Article Classifications: _classified_articles.json"
echo ""
echo "Pipeline completed successfully. Review outputs for meta-analysis results."