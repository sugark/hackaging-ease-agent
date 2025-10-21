#!/usr/bin/env python3
"""
Script to generate comprehensive draft documentation for meta-analysis project.
Collects data from various reports and extracts to create a structured markdown document.
"""

import json
import os
from pathlib import Path
import glob
from datetime import datetime

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas not available, CSV processing will be limited")

def load_json_file(filepath):
    """Load JSON file and handle errors gracefully."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: File {filepath} not found")
        return None
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON in {filepath}")
        return None

def load_text_file(filepath):
    """Load text file and handle errors gracefully."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Warning: File {filepath} not found")
        return ""

def count_articles_with_condition(data, condition_func):
    """Count articles that meet a specific condition."""
    if not data:
        return 0
    
    count = 0
    articles = data.get('articles', []) if isinstance(data, dict) else data
    
    for article in articles:
        if condition_func(article):
            count += 1
    
    return count

def extract_search_queries(search_data):
    """Extract search queries from generated search data."""
    if not search_data:
        return []
    
    queries = []
    generated_queries = search_data.get('generated_queries', {})
    query_list = generated_queries.get('queries', [])
    
    for query in query_list:
        query_string = query.get('query_string', '')
        if query_string:
            queries.append(query_string)
    
    return queries

def count_good_candidates(filtered_data):
    """Count articles marked as good candidates."""
    if not filtered_data:
        return 0
    
    # Check if metadata with good_candidates count exists
    if isinstance(filtered_data, dict):
        metadata = filtered_data.get('metadata', {})
        if 'good_candidates' in metadata:
            return metadata['good_candidates']
        
        # Fallback: count manually from classifications
        classifications = filtered_data.get('classifications', [])
        count = 0
        for classification in classifications:
            if isinstance(classification, dict) and classification.get('is_good_candidate') == True:
                count += 1
        return count
    
    return 0

def count_downloaded_articles(downloaded_data):
    """Count articles with valid PDF paths."""
    if not downloaded_data:
        return 0
    
    count = 0
    # Handle different data structures  
    if isinstance(downloaded_data, dict):
        articles = downloaded_data.get('articles', [])
    elif isinstance(downloaded_data, list):
        articles = downloaded_data
    else:
        return 0
    
    for article in articles:
        if isinstance(article, dict):
            pdf_path = article.get('pdf_path')
            if pdf_path and pdf_path.strip() and pdf_path != "null":
                count += 1
    
    return count

def create_bias_assessment_table(extracted_file, classified_data):
    """Create Cochrane bias assessment table."""
    if not os.path.exists(extracted_file) or not classified_data:
        return "No bias assessment data available.\n"
    
    # Get PMIDs and author_year from extracted datapoints
    article_info = {}
    
    if PANDAS_AVAILABLE:
        try:
            extracted_df = pd.read_csv(extracted_file)
            if 'study_id' in extracted_df.columns and 'author_year' in extracted_df.columns:
                for _, row in extracted_df.iterrows():
                    pmid = str(row['study_id'])
                    author_year = row['author_year']
                    article_info[pmid] = author_year
        except Exception as e:
            print(f"Error reading CSV with pandas: {e}")
    else:
        # Basic CSV reading without pandas
        try:
            with open(extracted_file, 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    header = lines[0].strip().split(',')
                    pmid_idx = header.index('pmid') if 'pmid' in header else -1
                    author_idx = header.index('author_year') if 'author_year' in header else -1
                    
                    if pmid_idx >= 0 and author_idx >= 0:
                        for line in lines[1:]:
                            parts = line.strip().split(',')
                            if len(parts) > max(pmid_idx, author_idx):
                                pmid = parts[pmid_idx].strip('"')
                                author_year = parts[author_idx].strip('"')
                                article_info[pmid] = author_year
        except Exception as e:
            print(f"Error reading CSV manually: {e}")
    
    # Create bias table
    bias_table = "| PMID | Author Year | Randomization | Deviations | Missing Data | Measurement | Selection |\n"
    bias_table += "|------|-------------|---------------|------------|--------------|-------------|----------|\n"
    
    # Handle different data structures for classified_data
    if isinstance(classified_data, dict):
        articles = classified_data.get('articles', [])
    elif isinstance(classified_data, list):
        articles = classified_data
    else:
        return "Invalid classified data format.\n"
    
    for article in articles:
        if not isinstance(article, dict):
            continue
            
        pmid = str(article.get('pmid', ''))
        author_year = article_info.get(pmid, 'Unknown')
        if author_year == 'Unknown':
            continue
        
        # Fix path: classifier_results.cochrane_bias.result
        classifier_results = article.get('classifier_results', {})
        cochrane_bias = classifier_results.get('cochrane_bias', {}).get('result', {})
        bias_assessment = cochrane_bias.get('bias_assessment', [])
        
        
        # Initialize bias domains
        bias_domains = {
            'randomization': 'N/A',
            'deviations': 'N/A', 
            'missing_data': 'N/A',
            'measurement': 'N/A',
            'selection': 'N/A'
        }
        
        # Parse bias assessment
        for bias in bias_assessment:
            if not isinstance(bias, dict):
                continue
            domain = bias.get('bias_domain', '').lower()
            is_present = bias.get('is_present', False)
            
            if 'randomization' in domain:
                bias_domains['randomization'] = str(is_present)
            elif 'deviation' in domain:
                bias_domains['deviations'] = str(is_present)
            elif 'missing' in domain:
                bias_domains['missing_data'] = str(is_present)
            elif 'measurement' in domain:
                bias_domains['measurement'] = str(is_present)
            elif 'selection' in domain:
                bias_domains['selection'] = str(is_present)
        
        bias_table += f"| {pmid} | {author_year} | {bias_domains['randomization']} | {bias_domains['deviations']} | {bias_domains['missing_data']} | {bias_domains['measurement']} | {bias_domains['selection']} |\n"
    
    return bias_table

def get_meta_analysis_images():
    """Get list of meta-analysis result images."""
    image_files = glob.glob("_meta_analysis_*.png")
    return sorted(image_files)

def generate_documentation():
    """Generate the complete draft documentation."""
    
    print("Starting documentation generation...")
    
    # Initialize documentation content
    doc_content = "# Meta-Analysis Project Documentation\n\n"
    doc_content += f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    
    # Creator information
    doc_content += "**Creator:** krisztian.sugar@frogs.hu \"budapest\" team\n\n"
    
    # 1. Topic Section
    print("Processing topic section...")
    doc_content += "## 1. Input Topic\n\n"
    topic_content = load_text_file("_input_topic.md")
    if topic_content:
        doc_content += f"**Topic:** {topic_content}\n\n"
    else:
        doc_content += "**Topic:** Not available\n\n"
    
    # 2. Search Section
    print("Processing search section...")
    doc_content += "## 2. Database Search\n\n"
    doc_content += "Due to missing license I was only using PubMed API.\n\n"
    
    # Load search queries
    search_data = load_json_file("_pubmed_generate_search_out.json")
    queries = extract_search_queries(search_data)
    
    doc_content += "**Search queries generated by LLM:**\n"
    for i, query in enumerate(queries, 1):
        doc_content += f"{i}. `{query}`\n"
    doc_content += "\n"
    
    # Count fetched articles
    fetched_data = load_json_file("_pubmed_fetched_meta_results.json")
    article_count = 0
    if fetched_data:
        articles = fetched_data.get('articles', [])
        article_count = len(articles)
    
    doc_content += f"**Search results:** {article_count} articles retrieved\n\n"
    
    # 3. Pre-filter Section
    print("Processing pre-filter section...")
    doc_content += "## 3. Abstract-Based Pre-filtering\n\n"
    doc_content += "Based on fetched PubMed metadata, articles were pre-filtered using LLM analysis of abstracts.\n\n"
    
    doc_content += "**GOOD CANDIDATES should have:**\n"
    doc_content += "- Clear randomized controlled trial (RCT) or systematic review methodology\n"
    doc_content += "- Well-defined study population and intervention\n"
    doc_content += "- Measurable primary and secondary outcomes\n"
    doc_content += "- Statistical analysis with effect sizes, confidence intervals, or p-values\n"
    doc_content += "- Clinical relevance and significance\n"
    doc_content += "- Adequate sample size\n"
    doc_content += "- Clear inclusion/exclusion criteria\n\n"
    
    doc_content += "**BAD CANDIDATES typically have:**\n"
    doc_content += "- Case reports or case series (small n<10)\n"
    doc_content += "- Editorial comments, letters, or opinions\n"
    doc_content += "- Animal studies or in vitro studies only\n"
    doc_content += "- Lack of control groups\n"
    doc_content += "- Unclear methodology or outcomes\n"
    doc_content += "- Preliminary or pilot studies without sufficient power\n"
    doc_content += "- Studies with major methodological flaws\n"
    doc_content += "- Conference abstracts without full methodology\n\n"
    
    # Count good candidates
    filtered_data = load_json_file("_pubmed_filtered_articles.json")
    good_candidates = count_good_candidates(filtered_data)
    doc_content += f"**Result:** {good_candidates} articles remained after abstract filtering\n\n"
    
    # 4. Download Section
    print("Processing download section...")
    doc_content += "## 4. Full-Text Article Download\n\n"
    doc_content += "As lack of license only publicly available open access articles were downloaded.\n"
    doc_content += "Download attempted using PubMed API, with fallback to DOI link following.\n\n"
    
    downloaded_data = load_json_file("_pubmed_downloaded_articles.json")
    downloaded_count = count_downloaded_articles(downloaded_data)
    doc_content += f"**Result:** {downloaded_count} articles successfully downloaded\n\n"
    
    # 5. Classification Section
    print("Processing classification section...")
    doc_content += "## 5. Article Classification\n\n"
    doc_content += "Remaining full-text articles were classified one-by-one using LLM analysis:\n\n"
    doc_content += "**Classification categories:**\n"
    doc_content += "- `article_type`: Article type classification\n"
    doc_content += "- `candidate_meta_analysis`: Suitability for meta-analysis\n"
    doc_content += "- `cochrane_bias`: Cochrane bias risk assessment\n"
    doc_content += "- `data_type`: Type of data presented\n"
    doc_content += "- `species`: Species studied\n"
    doc_content += "- `study_type`: Study design type\n"
    doc_content += "- `clinical_test`: Clinical tests/measurements\n"
    doc_content += "- `cohort`: Cohort characteristics\n\n"
    doc_content += "Each classification includes evidence references from the source text.\n\n"
    
    # 6. Analysis Target Section
    print("Processing analysis target section...")
    doc_content += "## 6. Meta-Analysis Target Selection\n\n"
    doc_content += "Based on available cohorts and clinical tests, LLM analysis identified:\n"
    doc_content += "*\"The most suitable clinical test for meta-analysis — one that provides the strongest evidence base and the widest coverage across studies.\"*\n\n"
    doc_content += "Due to limited time and resources, only 1 meta-analysis target was selected.\n\n"
    
    suggested_analysis = load_json_file("_suggested_analysis.json")
    if suggested_analysis:
        doc_content += "**Selected target:**\n"
        doc_content += f"<code>json\n{json.dumps(suggested_analysis, indent=2)}\n</code>\n\n"
    else:
        doc_content += "**Selected target:** Data not available\n\n"
    
    # 7. Data Extraction Section
    print("Processing data extraction section...")
    doc_content += "## 7. Data Point Extraction\n\n"
    doc_content += "Based on the suggested meta-analysis target, all PDFs were processed individually to extract relevant data using multimodal Pro LLM.\n\n"
    
    csv_file = "_extracted_datapoints.csv"
    if os.path.exists(csv_file):
        if PANDAS_AVAILABLE:
            try:
                extracted_df = pd.read_csv(csv_file)
                if not extracted_df.empty:
                    doc_content += "**Sample extracted datapoints:**\n"
                    doc_content += "<code>\n"
                    doc_content += extracted_df.head(3).to_string(index=False)
                    doc_content += "\n</code>\n\n"
                else:
                    doc_content += "**Extracted datapoints:** No data available\n\n"
            except Exception as e:
                doc_content += f"**Extracted datapoints:** Error reading file: {str(e)}\n\n"
        else:
            # Read first 3 lines manually
            try:
                with open(csv_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        doc_content += "**Sample extracted datapoints:**\n"
                        doc_content += "<code>\n"
                        for i, line in enumerate(lines[:4]):  # Header + 3 data rows
                            doc_content += line.strip() + "\n"
                        doc_content += "</code>\n\n"
                    else:
                        doc_content += "**Extracted datapoints:** No data available\n\n"
            except Exception as e:
                doc_content += f"**Extracted datapoints:** Error reading file: {str(e)}\n\n"
    else:
        doc_content += "**Extracted datapoints:** File not found\n\n"
    
    # 8. Meta-Analysis Section
    print("Processing meta-analysis section...")
    doc_content += "## 8. Meta-Analysis Execution\n\n"
    doc_content += "LLM generated Python code to create Forest plots and statistical tables for the meta-analysis.\n\n"
    
    # 9. Cochrane Bias Assessment
    print("Processing bias assessment section...")
    doc_content += "## 9. Cochrane Bias Risk Assessment\n\n"
    
    try:
        classified_data = load_json_file("_classified_articles.json")
        bias_table = create_bias_assessment_table("_extracted_datapoints.csv", classified_data)
        doc_content += bias_table
        doc_content += "\n"
    except Exception as e:
        doc_content += f"Bias assessment table could not be generated: {str(e)}\n\n"
    
    # 10. Results Section
    print("Processing results section...")
    doc_content += "## 10. Results\n\n"
    
    # Topic reminder
    if topic_content:
        doc_content += f"**Topic:** {topic_content}\n\n"
    
    # Meta-analyzed articles
    csv_file = "_extracted_datapoints.csv"
    if os.path.exists(csv_file):
        if PANDAS_AVAILABLE:
            try:
                extracted_df = pd.read_csv(csv_file)
                if not extracted_df.empty and 'pmid' in extracted_df.columns:
                    doc_content += "**Meta-analyzed articles:**\n"
                    for _, row in extracted_df.iterrows():
                        pmid = row.get('pmid', 'N/A')
                        author_year = row.get('author_year', 'N/A')
                        title = row.get('title', 'N/A')
                        doc_content += f"- PMID: {pmid}, {author_year}: {title}\n"
                    doc_content += "\n"
            except Exception as e:
                doc_content += f"**Meta-analyzed articles:** Error reading data: {str(e)}\n\n"
        else:
            # Read manually without pandas
            try:
                with open(csv_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        header = lines[0].strip().split(',')
                        pmid_idx = header.index('pmid') if 'pmid' in header else -1
                        author_idx = header.index('author_year') if 'author_year' in header else -1
                        title_idx = header.index('title') if 'title' in header else -1
                        
                        if pmid_idx >= 0:
                            doc_content += "**Meta-analyzed articles:**\n"
                            for line in lines[1:]:
                                parts = line.strip().split(',')
                                if len(parts) > pmid_idx:
                                    pmid = parts[pmid_idx].strip('"') if pmid_idx >= 0 else 'N/A'
                                    author_year = parts[author_idx].strip('"') if author_idx >= 0 and len(parts) > author_idx else 'N/A'
                                    title = parts[title_idx].strip('"') if title_idx >= 0 and len(parts) > title_idx else 'N/A'
                                    doc_content += f"- PMID: {pmid}, {author_year}: {title}\n"
                            doc_content += "\n"
            except Exception as e:
                doc_content += f"**Meta-analyzed articles:** Error reading file: {str(e)}\n\n"
    else:
        doc_content += "**Meta-analyzed articles:** Data not available\n\n"
    
    # Result images
    image_files = get_meta_analysis_images()
    if image_files:
        doc_content += "**Generated visualizations:**\n"
        for img_file in image_files:
            doc_content += f"![{img_file}]({img_file})\n"
        doc_content += "\n"
    
    # Meta-analysis output
    meta_output = load_text_file("_meta_analysis_output.txt")
    if meta_output:
        doc_content += "**Statistical Results:**\n"
        doc_content += f"<code>\n{meta_output}\n</code>\n\n"
    else:
        doc_content += "**Statistical Results:** Not available\n\n"
    
    # Write documentation to file
    output_file = "_draft_documentation.md"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        print(f"Documentation successfully written to {output_file}")
    except Exception as e:
        print(f"Error writing documentation: {str(e)}")
    
    return doc_content

def main():
    """Main function to run the documentation generation."""
    try:
        documentation = generate_documentation()
        print("\nDocumentation generation completed!")
        return True
    except Exception as e:
        print(f"Error during documentation generation: {str(e)}")
        return False

if __name__ == "__main__":
    main()
