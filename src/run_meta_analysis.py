import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import StringIO
import sys

def calculate_smd(n1, m1, sd1, n2, m2, sd2):
    """Calculates the standardized mean difference (Hedges' g)."""
    # Cohen's d
    sd_pooled = np.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / (n1 + n2 - 2))
    if sd_pooled == 0:
        return 0, 0
    d = (m1 - m2) / sd_pooled
    
    # Hedges' g
    j = 1 - (3 / (4 * (n1 + n2 - 2) - 1))
    g = j * d
    
    # Standard error of g
    se_g = np.sqrt((n1 + n2) / (n1 * n2) + (g**2) / (2 * (n1 + n2)))
    
    return g, se_g

def plot_forest(df, outcome_name, output_file):
    """Generates and saves a forest plot."""
    fig, ax = plt.subplots(figsize=(10, 5))
    
    y = np.arange(len(df))
    
    ax.errorbar(df['g'], y, xerr=1.96 * df['se_g'], fmt='o', capsize=5, label='Study SMD (95% CI)')
    
    # Pooled effect
    pooled_g = df['pooled_g'].iloc[0]
    pooled_se = df['pooled_se'].iloc[0]
    ax.errorbar(pooled_g, len(df), xerr=1.96 * pooled_se, fmt='D', capsize=7, color='red', label=f'Pooled SMD (95% CI): {pooled_g:.2f} [{pooled_g - 1.96*pooled_se:.2f}, {pooled_g + 1.96*pooled_se:.2f}]')

    ax.axvline(0, linestyle='--', color='gray')
    
    ax.set_yticks(np.arange(len(df) + 1))
    ax.set_yticklabels(list(df['author_year']) + ['Pooled'])
    ax.set_xlabel("Standardized Mean Difference (Hedges' g)")
    ax.set_title(f"Forest Plot for {outcome_name.replace('_', ' ')}")
    ax.legend()
    plt.tight_layout()
    
    # Chart filename convention: meta_analysis{chartname}.png
    chart_filename = f"_meta_analysis_forest_{outcome_name}.png"
    plt.savefig(chart_filename)
    
    # Write chart details to output file
    chart_name = f"Forest Plot - {outcome_name.replace('_', ' ')}"
    output_file.write(f"\nChart: {chart_name}\n")
    output_file.write(f"Filename: {chart_filename}\n")
    output_file.write(f"Description: Forest plot showing standardized mean differences for {outcome_name.replace('_', ' ')} with 95% confidence intervals\n")
    
    print(f"Saved forest plot to {chart_filename}")
    plt.close()

def main():
    # Redirect output to file
    output_filename = "_meta_analysis_output.txt"
    
    # Open output file and redirect stdout
    with open(output_filename, 'w') as output_file:
        # Create a custom print function that writes to both console and file
        def tee_print(*args, **kwargs):
            print(*args, **kwargs)  # Print to console
            print(*args, **kwargs, file=output_file)  # Print to file
            output_file.flush()  # Ensure immediate write
        
        # Read data from the extracted datapoints CSV file
        try:
            df = pd.read_csv('_extracted_datapoints.csv')
            tee_print(f"Successfully loaded {len(df)} rows from _extracted_datapoints.csv")
            tee_print(f"Columns: {list(df.columns)}")
            tee_print(f"Outcomes available: {df['outcome_name'].unique()}")
            tee_print(f"Studies: {df['author_year'].unique()}")
            tee_print()
        except FileNotFoundError:
            tee_print("Error: _extracted_datapoints.csv file not found!")
            return
        except Exception as e:
            tee_print(f"Error reading CSV file: {e}")
            return

        # Clean the data - remove rows with missing essential values
        essential_cols = ['sample_size_intervention', 'sample_size_control', 
                         'intervention_post_mean', 'intervention_post_sd', 
                         'control_post_mean', 'control_post_sd']
        
        # Convert to numeric and handle missing values
        for col in essential_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Keep only rows with complete data for meta-analysis
        df_clean = df.dropna(subset=essential_cols)
        tee_print(f"After cleaning missing values: {len(df_clean)} rows remaining")
        
        if len(df_clean) == 0:
            tee_print("No complete data available for meta-analysis!")
            return

        # Find outcomes that have multiple studies
        common_outcomes = df_clean.groupby('outcome_name').filter(lambda x: len(x) > 1)['outcome_name'].unique()
        tee_print(f"Outcomes with multiple studies: {common_outcomes}")
        tee_print()

        if len(common_outcomes) == 0:
            tee_print("No outcomes with multiple studies found for meta-analysis!")
            # Still analyze single studies
            single_outcomes = df_clean['outcome_name'].unique()
            tee_print(f"Single study outcomes available: {single_outcomes}")
            
            for outcome in single_outcomes:
                tee_print(f"--- Single study analysis for {outcome} ---")
                outcome_df = df_clean[df_clean['outcome_name'] == outcome].copy()
                tee_print(outcome_df[['author_year', 'intervention_post_mean', 'intervention_post_sd', 
                                'control_post_mean', 'control_post_sd']])
                tee_print()
            return

        # Write header for charts section
        output_file.write("\n" + "="*50 + "\n")
        output_file.write("GENERATED CHARTS\n")
        output_file.write("="*50 + "\n")

        for outcome in common_outcomes:
            tee_print(f"--- Meta-analysis for {outcome} ---")
            outcome_df = df_clean[df_clean['outcome_name'] == outcome].copy()
            
            # Calculate standardized mean difference for each study
            smd_results = outcome_df.apply(lambda row: calculate_smd(
                row['sample_size_intervention'], row['intervention_post_mean'], row['intervention_post_sd'],
                row['sample_size_control'], row['control_post_mean'], row['control_post_sd']
            ), axis=1)
            
            outcome_df[['g', 'se_g']] = pd.DataFrame(smd_results.tolist(), index=outcome_df.index)
            
            # Remove studies with invalid SMD calculations (infinite or NaN values)
            valid_smd = outcome_df['se_g'].notna() & np.isfinite(outcome_df['se_g']) & (outcome_df['se_g'] > 0)
            outcome_df = outcome_df[valid_smd]
            
            if len(outcome_df) < 2:
                tee_print(f"Insufficient valid data for meta-analysis of {outcome}")
                continue
            
            # Meta-analysis (fixed-effect model)
            outcome_df['w'] = 1 / outcome_df['se_g']**2
            pooled_g = np.sum(outcome_df['w'] * outcome_df['g']) / np.sum(outcome_df['w'])
            pooled_se = np.sqrt(1 / np.sum(outcome_df['w']))
            
            outcome_df['pooled_g'] = pooled_g
            outcome_df['pooled_se'] = pooled_se
            
            tee_print(outcome_df[['author_year', 'intervention_name', 'dose_mg_per_day', 'g', 'se_g']])
            tee_print(f"Pooled SMD (Hedges' g): {pooled_g:.3f}")
            tee_print(f"Standard Error of Pooled SMD: {pooled_se:.3f}")
            tee_print(f"95% CI: [{pooled_g - 1.96*pooled_se:.3f}, {pooled_g + 1.96*pooled_se:.3f}]")
            
            # Plotting
            plot_forest(outcome_df, outcome, output_file)
            tee_print("-" * (len(outcome) + 24))
            tee_print("\n")
    
    print(f"\nMeta-analysis output written to: {output_filename}")

if __name__ == "__main__":
    main()
