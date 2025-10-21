#!/usr/bin/env python3
"""
Advanced Documentation Generator using Gemini API with minimal temperature for reduced hallucination.
Generates comprehensive _advanced_documentation.md from all source files.

This script:
1. Loads all required source files including drafts, data, and prompts
2. Uses Gemini API with temperature=0 for minimal hallucination
3. Generates publication-ready advanced documentation
4. Outputs to _advanced_documentation.md
"""

import json
import os
import glob
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from dotenv import load_dotenv

from google import genai
from google.genai import types
from system_prompt_advanced_documentation import SYSTEM_PROMPT_ADVANCED_DOCUMENTATION

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedDocumentationGenerator:
    def __init__(self):
        """Initialize the Advanced Documentation Generator."""
        load_dotenv()
        
        self.client = genai.Client()
        self.model_name = "gemini-flash-latest"  # Use standard Pro model name
        
        # System prompt for advanced documentation generation
        self.system_instruction = SYSTEM_PROMPT_ADVANCED_DOCUMENTATION

    def load_text_file(self, filepath: str) -> str:
        """Load text file and handle errors gracefully."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                logger.info(f"Loaded {filepath}: {len(content)} characters")
                return content
        except FileNotFoundError:
            logger.warning(f"File {filepath} not found")
            return ""
        except Exception as e:
            logger.error(f"Error loading {filepath}: {str(e)}")
            return ""

    def load_json_file(self, filepath: str) -> Optional[Dict]:
        """Load JSON file and handle errors gracefully."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded {filepath}: {type(data).__name__}")
                return data
        except FileNotFoundError:
            logger.warning(f"File {filepath} not found")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filepath}: {str(e)}")
            return None

    def load_csv_file(self, filepath: str) -> str:
        """Load CSV file as text for inclusion in prompt."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                logger.info(f"Loaded CSV {filepath}: {len(content.splitlines())} lines")
                return content
        except FileNotFoundError:
            logger.warning(f"CSV file {filepath} not found")
            return ""
        except Exception as e:
            logger.error(f"Error loading CSV {filepath}: {str(e)}")
            return ""

    def load_prompt_files(self) -> Dict[str, str]:
        """Load key prompt files (_prompt_classifier* and _prompt_extractor*)."""
        prompt_files = {}
        
        # Load key prompt files only (to avoid overwhelming the API)
        key_files = [
            "_prompt_classifier_candidate_meta_analysis.py",
            "_prompt_classifier_cochrane_bias.py",
            "_prompt_extractor_clinical_test.py"
        ]
        
        for filepath in key_files:
            if os.path.exists(filepath):
                content = self.load_text_file(filepath)
                if content:
                    prompt_files[filepath] = content[:2000]  # Limit to first 2000 chars
                
        logger.info(f"Loaded {len(prompt_files)} key prompt files")
        return prompt_files

    def collect_all_data(self) -> Dict[str, Any]:
        """Collect all required data files."""
        logger.info("Starting data collection...")
        
        data = {}
        
        # Load main documentation draft
        data['draft_documentation'] = self.load_text_file("_draft_documentation.md")
        
        # Load JSON files
        json_files = [
            "_classified_articles.json",
            "_suggested_analysis.json"
        ]
        
        for json_file in json_files:
            data[json_file] = self.load_json_file(json_file)
        
        # Load CSV files
        csv_files = [
            "_cohorts_and_tests.csv",
            "_extracted_datapoints.csv"
        ]
        
        for csv_file in csv_files:
            data[csv_file] = self.load_csv_file(csv_file)
        
        # Load text files
        text_files = [
            "_input_topic.md",
            "_meta_analysis_output.txt"
        ]
        
        for text_file in text_files:
            data[text_file] = self.load_text_file(text_file)
        
        # Load all prompt files
        data['prompt_files'] = self.load_prompt_files()
        
        logger.info(f"Data collection completed. Loaded {len(data)} data categories")
        return data

    def format_data_for_prompt(self, data: Dict[str, Any]) -> str:
        """Format all collected data into a comprehensive prompt."""
        
        prompt_parts = []
        
        # Add draft documentation
        if data.get('draft_documentation'):
            prompt_parts.append("## DRAFT DOCUMENTATION (_draft_documentation.md)")
            prompt_parts.append("```markdown")
            prompt_parts.append(data['draft_documentation'])
            prompt_parts.append("```\n")
        
        # Add input topic
        if data.get('_input_topic.md'):
            prompt_parts.append("## INPUT TOPIC (_input_topic.md)")
            prompt_parts.append("```")
            prompt_parts.append(data['_input_topic.md'])
            prompt_parts.append("```\n")
        
        # Add classified articles
        if data.get('_classified_articles.json'):
            prompt_parts.append("## CLASSIFIED ARTICLES (_classified_articles.json)")
            prompt_parts.append("```json")
            prompt_parts.append(json.dumps(data['_classified_articles.json'], indent=2))
            prompt_parts.append("```\n")
        
        # Add suggested analysis
        if data.get('_suggested_analysis.json'):
            prompt_parts.append("## SUGGESTED ANALYSIS (_suggested_analysis.json)")
            prompt_parts.append("```json")
            prompt_parts.append(json.dumps(data['_suggested_analysis.json'], indent=2))
            prompt_parts.append("```\n")
        
        # Add cohorts and tests CSV
        if data.get('_cohorts_and_tests.csv'):
            prompt_parts.append("## COHORTS AND TESTS (_cohorts_and_tests.csv)")
            prompt_parts.append("```csv")
            prompt_parts.append(data['_cohorts_and_tests.csv'])
            prompt_parts.append("```\n")
        
        # Add extracted datapoints CSV
        if data.get('_extracted_datapoints.csv'):
            prompt_parts.append("## EXTRACTED DATAPOINTS (_extracted_datapoints.csv)")
            prompt_parts.append("```csv")
            prompt_parts.append(data['_extracted_datapoints.csv'])
            prompt_parts.append("```\n")
        
        # Add meta-analysis output
        if data.get('_meta_analysis_output.txt'):
            prompt_parts.append("## META-ANALYSIS OUTPUT (_meta_analysis_output.txt)")
            prompt_parts.append("```")
            prompt_parts.append(data['_meta_analysis_output.txt'])
            prompt_parts.append("```\n")
        
        # Add prompt files
        prompt_files = data.get('prompt_files', {})
        if prompt_files:
            prompt_parts.append("## PROMPT FILES")
            for filepath, content in prompt_files.items():
                prompt_parts.append(f"### {filepath}")
                prompt_parts.append("```python")
                prompt_parts.append(content)
                prompt_parts.append("```\n")
        
        return "\n".join(prompt_parts)

    def generate_advanced_documentation(self, data: Dict[str, Any]) -> str:
        """Generate advanced documentation using Gemini API."""
        
        logger.info("Preparing data for Gemini API...")
        formatted_data = self.format_data_for_prompt(data)
        
        # Create the complete prompt
        full_prompt = f"""Based on the following comprehensive data, generate a complete, detailed, and publication-ready advanced documentation file.

{formatted_data}

Please generate a comprehensive markdown document that synthesizes ALL the above information into a professional, technical documentation suitable for research archival or publication.

Follow the system instructions precisely:
- Use exact numbers and data from the provided files
- Maintain scientific rigor and formal tone
- Include all relevant details from classifications, extractions, and analyses
- Structure chronologically: Input → Methods → Results → Analysis → Discussion → Summary
- Reference specific data points, tables, and figures where appropriate
- Ensure the document is self-contained and publication-ready
"""

        try:
            logger.info("Calling Gemini API for advanced documentation generation...")
            
            # Use minimal temperature for reduced hallucination
            generation_config = types.GenerateContentConfig(
                temperature=0.0,  # Minimal hallucination
                top_p=0.8,
                top_k=40,
                candidate_count=1,
                max_output_tokens=4096,  # Reduced token limit
                stop_sequences=None,
                response_mime_type="text/plain"
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[self.system_instruction + "\n\n" + full_prompt],
                config=generation_config
            )
            
            if response and response.text:
                generated_content = response.text
                logger.info(f"Successfully generated documentation: {len(generated_content)} characters")
                return generated_content
            else:
                logger.error("No valid response generated from Gemini API")
                return ""
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return ""

    def save_documentation(self, content: str, output_file: str = "_advanced_documentation.md") -> bool:
        """Save the generated documentation to file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Advanced documentation saved to {output_file}")
            logger.info(f"Document length: {len(content)} characters")
            logger.info(f"Document lines: {len(content.splitlines())} lines")
            
            return True
        except Exception as e:
            logger.error(f"Error saving documentation to {output_file}: {str(e)}")
            return False

    def run(self) -> bool:
        """Main execution method."""
        try:
            logger.info("Starting Advanced Documentation Generation...")
            
            # Collect all data
            data = self.collect_all_data()
            
            # Verify we have the essential files
            if not data.get('draft_documentation'):
                logger.error("Critical: _draft_documentation.md not found or empty")
                return False
            
            # Generate advanced documentation
            advanced_doc = self.generate_advanced_documentation(data)
            
            if not advanced_doc:
                logger.error("Failed to generate advanced documentation")
                return False
            
            # Save the result
            success = self.save_documentation(advanced_doc)
            
            if success:
                logger.info("Advanced documentation generation completed successfully!")
                return True
            else:
                logger.error("Failed to save advanced documentation")
                return False
                
        except Exception as e:
            logger.error(f"Error during advanced documentation generation: {str(e)}")
            return False

def main():
    """Main function to run the advanced documentation generator."""
    generator = AdvancedDocumentationGenerator()
    
    success = generator.run()
    
    if success:
        print("\n✅ Advanced documentation generated successfully!")
        print("📄 Output: _advanced_documentation.md")
    else:
        print("\n❌ Advanced documentation generation failed!")
        print("Check the logs for details.")
    
    return success

if __name__ == "__main__":
    main()
