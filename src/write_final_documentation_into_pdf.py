#!/usr/bin/env python3
"""
PDF Generation Script for Meta-Analysis Documentation
Converts the draft markdown documentation to PDF format
"""

import os
import argparse
from md2pdf.core import md2pdf

# CLI Usage Examples:
# 
# Generate advanced report (default):
#   python write_final_documentation_into_pdf.py
#   python write_final_documentation_into_pdf.py --mode advanced
#
# Generate draft report:
#   python write_final_documentation_into_pdf.py --mode draft
#
# Show help:
#   python write_final_documentation_into_pdf.py --help
#
# File mappings:
#   draft mode:    _draft_documentation.md    -> _draft_meta_analysis_report.pdf    (using _draft_meta_analysis_report.css)
#   advanced mode: _advanced_documentation.md -> _advanced_meta_analysis_report.pdf (using _advanced_meta_analysis_report.css)

def main():
    """Generate PDF from markdown documentation"""
    
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Convert markdown documentation to PDF')
    parser.add_argument('--mode', choices=['draft', 'advanced'], 
                       default='advanced',
                       help='Documentation mode: draft or advanced (default: advanced)')
    
    args = parser.parse_args()
    
    # Configure files based on mode
    if args.mode == 'draft':
        draft_file = '_draft_documentation.md'
        output_pdf = '_draft_meta_analysis_report.pdf'
        css_file = './styles/_draft_meta_analysis_report.css'
    else:  # advanced
        draft_file = '_advanced_documentation.md'
        output_pdf = '_advanced_meta_analysis_report.pdf'
        css_file = './styles/_advanced_meta_analysis_report.css'
    
    # Check if input file exists
    if not os.path.exists(draft_file):
        print(f"Error: Input file {draft_file} not found!")
        return
    
    try:
        print(f"Converting {draft_file} to {output_pdf} using {css_file}...")
        
        # Convert markdown to PDF
        md2pdf(
            output_pdf,                   # output PDF file path
            md_content="",               # empty - reading from file
            md_file_path=draft_file,     # input markdown file
            css_file_path=css_file,      # mode-specific CSS
            base_url="."                 # ensure image paths resolve correctly
        )
        
        print(f"Successfully generated PDF: {output_pdf}")
        
        # Check if output file was created
        if os.path.exists(output_pdf):
            file_size = os.path.getsize(output_pdf)
            print(f"PDF file size: {file_size:,} bytes")
        else:
            print("Warning: PDF file was not created")
            
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        print("Make sure md2pdf is installed: pip install md2pdf")

if __name__ == "__main__":
    main()