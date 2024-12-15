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
from scipy.stats import skew, kurtosis, ttest_ind

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
AIPROXY_TOKEN = (
    "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIxZjMwMDE2NTZAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.65Ak3RcBLflFkPSsRTn7cqX3gKSZjqKeRr06YnRvrjg"
)

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
        dict: Analysis results including summary statistics, missing values, correlation, skewness, kurtosis, variance, and hypothesis testing.
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

    # Variance and Standard Deviation
    variance = numeric_df.var().to_dict() if not numeric_df.empty else {}
    std_dev = numeric_df.std().to_dict() if not numeric_df.empty else {}

    # Skewness and Kurtosis
    skewness = numeric_df.apply(skew).to_dict() if not numeric_df.empty else {}
    kurtosis_vals = numeric_df.apply(kurtosis).to_dict() if not numeric_df.empty else {}

    # Hypothesis Testing (Example: T-tests between numeric columns if applicable)
    hypothesis_tests = {}
    numeric_columns = numeric_df.columns
    if len(numeric_columns) > 1:
        for i in range(len(numeric_columns)):
            for j in range(i + 1, len(numeric_columns)):
                col1, col2 = numeric_columns[i], numeric_columns[j]
                t_stat, p_val = ttest_ind(df[col1].dropna(), df[col2].dropna())
                hypothesis_tests[f"{col1} vs {col2}"] = {"t_stat": t_stat, "p_val": p_val}

    # Unique values for categorical columns
    categorical_df = df.select_dtypes(include=['object', 'category'])
    unique_values = {col: df[col].nunique() for col in categorical_df.columns}

    return {
        "summary": summary,
        "missing_values": missing_values,
        "correlation": correlation,
        "variance": variance,
        "std_dev": std_dev,
        "skewness": skewness,
        "kurtosis": kurtosis_vals,
        "hypothesis_tests": hypothesis_tests,
        "unique_values": unique_values
    }

def generate_visualizations(df, output_dir='visualizations'):
    """
    Generate and save a heatmap visualization for numeric columns in a DataFrame.

    Parameters:
        df (pd.DataFrame): The DataFrame containing the data to visualize.
        output_dir (str): Directory to save the visualizations. Default is 'visualizations'.

    Returns:
        list: List of file paths for the generated visualizations.
    """
    if df.empty:
        raise ValueError("The input DataFrame is empty. Please provide a valid DataFrame.")

    os.makedirs(output_dir, exist_ok=True)

    sns.set(style="darkgrid")
    numeric_columns = df.select_dtypes(include=['number'])

    if numeric_columns.empty:
        raise ValueError("No numeric columns found for visualization.")

    # Compute the correlation matrix for numeric columns
    correlation_matrix = numeric_columns.corr()

    # Plot the heatmap
    plt.figure(figsize=(6, 6))  # Small size for compact output
    sns.heatmap(correlation_matrix, annot=False, fmt=".2f", cmap='coolwarm', cbar=True)
    plt.title('Heatmap of Numeric Columns Correlation')
    plt.tight_layout()

    # Save as a single 512x512 PNG file
    output_file = os.path.join(output_dir, 'heatmap.png')
    plt.savefig(output_file, dpi=85)  # Adjust DPI to ensure 512x512 px resolution
    plt.close()

    print(f"Heatmap visualization saved as: {output_file}")
    return [output_file]


def request_narrative(analysis, image_files):
    """
    Generate narrative using a language model based on analysis results.

    Parameters:
        analysis (dict): Analysis results.
        image_files (list): List of paths to generated visualization images.

    Returns:
        str: Generated narrative or error message.
    """
    headers = {
        'Authorization': f'Bearer {AIPROXY_TOKEN}',
        'Content-Type': 'application/json'
    }
    image_list = "\n".join([f"- ![Visualization]({image})" for image in image_files])
    prompt = (
        f"Offer a comprehensive analysis based on the data summary provided below: {analysis}\n"
        f"Include references to the following heat map visualizations:\n{image_list}"
        f"Understand the data deeply. use the visuals provided for better understanding"
        #f"Generate graphs in png format (like pi chart or histogram) apart from the one that is provided based on the data summary provided and include that in the report at relevent context."
        f"Be consice and precice, concentrate on the insites (the intersting parts of the data analysis)"
        f"Produce a report neatly, It shuld contain a understandabe structure (Headers and sub headings and so on)"
        f"note down the implications of your findings (i.e. what to do with the insights)"
        f"Include the Image (provided) too in the report and analyse the contents (at the relevent context)."
    )
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = httpx.post(API_URL, headers=headers, json=data, timeout=30.0)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e}")
    except httpx.RequestError as e:
        print(f"Request error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return "Narrative generation failed due to an error."

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

        print("Step 3: Generating visualizations...")
        image_files = generate_visualizations(df)

        print("Step 4: Generating narrative...")
        narrative = request_narrative(analysis, image_files)

        print("Step 5: Saving narrative to file...")
        save_narrative_to_file(narrative)

        print("Pipeline completed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python autolysis.py <dataset.csv>")
        sys.exit(1)
    main_pipeline(sys.argv[1])
