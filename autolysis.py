# /// script
# dependencies = [
#   "seaborn",
#   "matplotlib",
#   "httpx",
#   "chardet",
#   "scipy"
# ]
# ///

import os
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import httpx
import chardet
from scipy.stats import skew, kurtosis

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN", "")

def detect_encoding(file_path):
    """
    Detect the encoding of a file.

    Parameters:
        file_path (str): Path to the file.

    Returns:
        str: Detected encoding of the file.
    """
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    return result['encoding']

def validate_file(file_path):
    """
    Validate that the file exists and is a CSV.

    Parameters:
        file_path (str): Path to the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a CSV.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if not file_path.endswith('.csv'):
        raise ValueError(f"Invalid file format. Expected a CSV file: {file_path}")

def load_data(file_path):
    """
    Load CSV data with encoding detection.

    Parameters:
        file_path (str): Path to the CSV file.

    Returns:
        pd.DataFrame: Loaded DataFrame.
    """
    encoding = detect_encoding(file_path)
    return pd.read_csv(file_path, encoding=encoding)

def perform_analysis(df):
    """
    Perform a detailed data analysis on the given DataFrame.

    Parameters:
        df (pd.DataFrame): Input DataFrame.

    Returns:
        dict: Analysis results including summary statistics, missing values, correlation, skewness, and kurtosis.
    """
    if df.empty:
        raise ValueError("The DataFrame is empty. Please provide valid data.")

    # Descriptive statistics
    summary = df.describe(include='all').to_dict()

    # Missing values analysis
    missing_values_count = df.isnull().sum()
    missing_values_percent = (missing_values_count / len(df)) * 100
    missing_values = {
        "count": missing_values_count.to_dict(),
        "percent": missing_values_percent.to_dict()
    }

    # Correlation analysis
    numeric_df = df.select_dtypes(include=['number'])
    correlation = numeric_df.corr().to_dict() if not numeric_df.empty else {}

    # Skewness and Kurtosis
    skewness = numeric_df.apply(skew).to_dict() if not numeric_df.empty else {}
    kurtosis_vals = numeric_df.apply(kurtosis).to_dict() if not numeric_df.empty else {}

    return {
        "summary": summary,
        "missing_values": missing_values,
        "correlation": correlation,
        "skewness": skewness,
        "kurtosis": kurtosis_vals
    }

def generate_visualization(df, output_file='visualization.png'):
    """
    Generate and save a single visualization for numeric columns in a DataFrame.

    Parameters:
        df (pd.DataFrame): The DataFrame containing the data to visualize.
        output_file (str): Path to save the visualization. Default is 'visualization.png'.

    Returns:
        str: File path of the generated visualization.
    """
    if df.empty:
        raise ValueError("The input DataFrame is empty. Please provide a valid DataFrame.")

    sns.set(style="darkgrid")
    sns.set_palette("muted")
    numeric_columns = df.select_dtypes(include=['number']).columns

    if numeric_columns.empty:
        raise ValueError("No numeric columns found for visualization.")

    # Select the first numeric column for visualization
    column = numeric_columns[0]
    data = df[column].dropna()

    # Create a single figure
    plt.figure(figsize=(8, 6))
    sns.histplot(data, kde=True)
    plt.title(f'Distribution of {column}')
    plt.xlabel(column)
    plt.ylabel('Frequency')

    # Save the plot
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()

    print(f"Visualization saved as: {output_file}")
    return output_file

def request_narrative(analysis, visualization_file):
    """
    Request a narrative based on analysis results and visualization.

    Parameters:
        analysis (dict): Analysis results.
        visualization_file (str): Path to the visualization file.

    Returns:
        str: Generated narrative.
    """
    summary = analysis.get("summary", {})
    missing_values = analysis.get("missing_values", {})
    correlation = analysis.get("correlation", {})
    skewness = analysis.get("skewness", {})
    kurtosis_vals = analysis.get("kurtosis", {})

    dynamic_prompt = (
        f"You are a data analyst. Generate a concise report for the dataset with the following details:\n"
        f"Summary statistics: {summary}\n"
        f"Missing values: {missing_values}\n"
        f"Correlation matrix: {correlation}\n"
        f"Skewness: {skewness}\n"
        f"Kurtosis: {kurtosis_vals}\n"
        f"Also include a note that the visualization can be found at {visualization_file}."
        f"The report should have clear structure and must be neatly written."
    )

    return dynamic_prompt

def save_narrative_to_file(narrative, output_file='README.md'):
    """
    Save generated narrative to a file.

    Parameters:
        narrative (str): Narrative content.
        output_file (str): Path to the output file. Default is 'README.md'.
    """
    with open(output_file, 'w') as f:
        f.write(narrative)

def main_pipeline(file_path):
    """
    Main function to orchestrate data analysis and visualization pipeline.

    Parameters:
        file_path (str): Path to the input dataset CSV file.
    """
    try:
        validate_file(file_path)
        print("Step 1: Loading data...")
        df = load_data(file_path)

        print("Step 2: Performing data analysis...")
        analysis = perform_analysis(df)

        print("Step 3: Generating visualization...")
        visualization_file = generate_visualization(df)

        print("Step 4: Generating narrative...")
        narrative = request_narrative(analysis, visualization_file)

        print("Step 5: Saving narrative...")
        save_narrative_to_file(narrative)

        print("Pipeline completed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python autolysis.py <dataset.csv>")
        sys.exit(1)
    main_pipeline(sys.argv[1])
