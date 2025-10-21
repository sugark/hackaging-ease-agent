#!/usr/bin/env python3
"""
Extract structured data from _classified_articles.json and output to CSV format.

Usage:
    python cohorts_and_tests_list.py
    python cohorts_and_tests_list.py --input _classified_articles.json --output _cohorts_and_tests.csv
    python cohorts_and_tests_list.py --separate-files  # Creates 3 separate CSV files
"""

import json
import csv
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_cohorts(articles: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extract cohort data from articles."""
    cohort_data = []
    
    for article in articles:
        pmid = article.get('pmid', 'unknown')
        cohort_results = article.get('classifier_results', {}).get('cohort', {}).get('result', {})
        cohorts = cohort_results.get('cohorts', [])
        
        for cohort in cohorts:
            cohort_data.append({
                'pmid': pmid,
                'cohort_short_name': cohort.get('short_name', ''),
                'cohort_description': cohort.get('description', ''),
                'cohort_group_size': cohort.get('group_size', '')
            })
    
    # Sort by PMID
    cohort_data.sort(key=lambda x: x['pmid'])
    return cohort_data


def extract_clinical_tests(articles: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extract clinical test data from articles."""
    clinical_test_data = []
    
    for article in articles:
        pmid = article.get('pmid', 'unknown')
        clinical_results = article.get('classifier_results', {}).get('clinical_test', {}).get('result', {})
        clinical_tests = clinical_results.get('clinical_tests', [])
        
        for test in clinical_tests:
            clinical_test_data.append({
                'pmid': pmid,
                'clinical_tests_short_name': test.get('short_name', ''),
                'clinical_test_description': test.get('description', '')
            })
    
    # Sort by PMID
    clinical_test_data.sort(key=lambda x: x['pmid'])
    return clinical_test_data


def extract_species(articles: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extract species data from articles."""
    species_data = []
    
    for article in articles:
        pmid = article.get('pmid', 'unknown')
        species_results = article.get('classifier_results', {}).get('species', {}).get('result', {})
        species_list = species_results.get('species_identified', [])
        
        for species in species_list:
            species_data.append({
                'pmid': pmid,
                'species_scientific_name': species.get('scientific_name', ''),
                'species_common_name': species.get('common_name', '')
            })
    
    # Sort by PMID
    species_data.sort(key=lambda x: x['pmid'])
    return species_data


def write_csv(data: List[Dict[str, str]], filename: str, fieldnames: List[str]):
    """Write data to CSV file."""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        logger.info(f"Successfully wrote {len(data)} rows to {filename}")
    except Exception as e:
        logger.error(f"Error writing to {filename}: {str(e)}")


def write_combined_csv(cohort_data: List[Dict], clinical_data: List[Dict], species_data: List[Dict], filename: str):
    """Write all data types to a single CSV file with different row types."""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['pmid', 'data_type', 'field1', 'field2', 'field3']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # Write cohort data
            for item in cohort_data:
                writer.writerow({
                    'pmid': item['pmid'],
                    'data_type': 'cohort',
                    'field1': item['cohort_short_name'],
                    'field2': item['cohort_description'],
                    'field3': item['cohort_group_size']
                })
            
            # Write clinical test data
            for item in clinical_data:
                writer.writerow({
                    'pmid': item['pmid'],
                    'data_type': 'clinical_test',
                    'field1': item['clinical_tests_short_name'],
                    'field2': item['clinical_test_description'],
                    'field3': ''
                })
            
            # Write species data
            for item in species_data:
                writer.writerow({
                    'pmid': item['pmid'],
                    'data_type': 'species',
                    'field1': item['species_scientific_name'],
                    'field2': item['species_common_name'],
                    'field3': ''
                })
        
        total_rows = len(cohort_data) + len(clinical_data) + len(species_data)
        logger.info(f"Successfully wrote {total_rows} rows to {filename}")
        
    except Exception as e:
        logger.error(f"Error writing combined CSV to {filename}: {str(e)}")


def write_combined_csv_sorted(cohort_data: List[Dict], clinical_data: List[Dict], species_data: List[Dict], filename: str):
    """Write all data types to a single CSV file with all data sorted by PMID."""
    try:
        # Combine all data into a single list with PMID sorting
        all_data = []
        
        # Add cohort data
        for item in cohort_data:
            all_data.append({
                'pmid': item['pmid'],
                'data_type': 'cohort',
                'field1': item['cohort_short_name'],
                'field2': item['cohort_description'],
                'field3': item['cohort_group_size']
            })
        
        # Add clinical test data
        for item in clinical_data:
            all_data.append({
                'pmid': item['pmid'],
                'data_type': 'clinical_test',
                'field1': item['clinical_tests_short_name'],
                'field2': item['clinical_test_description'],
                'field3': ''
            })
        
        # Add species data
        for item in species_data:
            all_data.append({
                'pmid': item['pmid'],
                'data_type': 'species',
                'field1': item['species_scientific_name'],
                'field2': item['species_common_name'],
                'field3': ''
            })
        
        # Sort all data by PMID first, then by data_type for consistent ordering within each PMID
        all_data.sort(key=lambda x: (x['pmid'], x['data_type']))
        
        # Write sorted data to CSV
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            # Write the header lines as specified
            csvfile.write("csv format: 3 different type of data record, data type defined in column 2 (values: cohort, clinical_test, species); each data record belongs to a specific paper\n")
            csvfile.write("paper_pmid,cohort,cohort_short_name,cohort_description,cohort_group_size\n")
            csvfile.write("paper_pmid,clinical_test,clinical_tests_short_name,clinical_test_description\n")
            csvfile.write("paper_pmid,species,species_scientific_name,species_common_name\n")
            
            # Write the actual data
            fieldnames = ['pmid', 'data_type', 'field1', 'field2', 'field3']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_data)
        
        logger.info(f"Successfully wrote {len(all_data)} sorted rows to {filename}")
        
    except Exception as e:
        logger.error(f"Error writing sorted combined CSV to {filename}: {str(e)}")


def main():
    """Main function to extract data and generate CSV files."""
    parser = argparse.ArgumentParser(description='Extract data from _classified_articles.json to CSV format')
    parser.add_argument('--input', '-i', default='_classified_articles.json', 
                        help='Input JSON file (default: _classified_articles.json)')
    parser.add_argument('--output', '-o', default='_cohorts_and_tests.csv',
                        help='Output CSV file (default: _cohorts_and_tests.csv)')
    parser.add_argument('--separate-files', action='store_true',
                        help='Create separate CSV files for each data type')
    
    args = parser.parse_args()
    
    # Load the JSON file
    try:
        with open(args.input, 'r', encoding='utf-8') as file:
            data = json.load(file)
        logger.info(f"Successfully loaded {args.input}")
    except FileNotFoundError:
        logger.error(f"File {args.input} not found")
        return
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON file: {str(e)}")
        return
    
    articles = data.get('articles', [])
    logger.info(f"Found {len(articles)} articles")
    
    # Extract data
    logger.info("Extracting cohort data...")
    cohort_data = extract_cohorts(articles)
    
    logger.info("Extracting clinical test data...")
    clinical_data = extract_clinical_tests(articles)
    
    logger.info("Extracting species data...")
    species_data = extract_species(articles)
    
    logger.info(f"Extracted: {len(cohort_data)} cohorts, {len(clinical_data)} clinical tests, {len(species_data)} species")
    
    if args.separate_files:
        # Write separate CSV files
        write_csv(cohort_data, 'cohorts.csv', 
                 ['pmid', 'cohort_short_name', 'cohort_description', 'cohort_group_size'])
        
        write_csv(clinical_data, 'clinical_tests.csv',
                 ['pmid', 'clinical_tests_short_name', 'clinical_test_description'])
        
        write_csv(species_data, 'species.csv',
                 ['pmid', 'species_scientific_name', 'species_common_name'])
    else:
        # Write combined CSV file with sorting across all data types
        write_combined_csv_sorted(cohort_data, clinical_data, species_data, args.output)
    
    logger.info("Data extraction completed successfully!")


if __name__ == "__main__":
    main()