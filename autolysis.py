# /// script
# dependencies = [
#   "seaborn",
#   "matplotlib",
#   "httpx",
#   "chardet"
# ]
# ///

import os
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import httpx
import chardet

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
AIPROXY_TOKEN = (
    "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIxZjMwMDE2NTZAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.65Ak3RcBLflFkPSsRTn7cqX3gKSZjqKeRr06YnRvrjg"
)


def load_data(file_path):
    """
    Load CSV data with encoding detection.

    Parameters:
        file_path (str): Path to the CSV file.

    Returns:
        pd.DataFrame: Loaded DataFrame.
    """
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    encoding = result['encoding']
    return pd.read_csv(file_path, encoding=encoding)


def analyze_data(df):
    """
    Perform a detailed data analysis on the given DataFrame.

    Parameters:
        df (pd.DataFrame): Input DataFrame.

    Returns:
        dict: Analysis results including summary statistics, missing values, correlation, and unique values.
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

    # Unique values for categorical columns
    categorical_df = df.select_dtypes(include=['object', 'category'])
    unique_values = {col: df[col].nunique() for col in categorical_df.columns}

    return {
        "summary": summary,
        "missing_values": missing_values,
        "correlation": correlation,
        "unique_values": unique_values
    }


def visualize_data(df, output_dir='visualizations'):
    """
    Generate and save visualizations for numeric columns in a DataFrame.

    Parameters:
        df (pd.DataFrame): The DataFrame containing the data to visualize.
        output_dir (str): Directory to save the visualizations. Default is 'visualizations'.
    """
    if df.empty:
        raise ValueError("The input DataFrame is empty. Please provide a valid DataFrame.")

    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    sns.set(style="darkgrid")
    sns.set_palette("muted")
    numeric_columns = df.select_dtypes(include=['number']).columns

    image_files = []  # Track generated image files

    for column in numeric_columns:
        data = df[column].dropna()

        # Create a figure with subplots
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))

        # Histogram with KDE and rug plot
        sns.histplot(data, kde=True, ax=axes[0])
        axes[0].set_title(f'Distribution of {column}')
        axes[0].set_xlabel(column)
        axes[0].set_ylabel('Frequency')

        # Boxplot
        sns.boxplot(x=data, ax=axes[1], orient='h')
        axes[1].set_title(f'Boxplot of {column}')
        axes[1].set_xlabel(column)

        # Adjust layout
        plt.tight_layout()

        # Safe file naming
        safe_column_name = "".join(c if c.isalnum() else "_" for c in column)
        file_path = os.path.join(output_dir, f'{safe_column_name}_visualizations.png')

        # Save the plot
        plt.savefig(file_path)
        image_files.append(file_path)
        plt.close()

    print(f"Visualizations saved in the directory: {output_dir}")
    return image_files


def generate_narrative(analysis, image_files):
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
        f"Include references to the following visualizations:\n{image_list}"
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


def save_narrative(narrative, output_file='README.md'):
    """
    Save generated narrative to a file.

    Parameters:
        narrative (str): Narrative content.
        output_file (str): Path to the output file. Default is 'README.md'.
    """
    with open(output_file, 'w') as f:
        f.write(narrative)


def main(file_path):
    """
    Main function to orchestrate data analysis and visualization pipeline.

    Parameters:
        file_path (str): Path to the input dataset CSV file.
    """
    try:
        df = load_data(file_path)
        analysis = analyze_data(df)
        image_files = visualize_data(df)
        narrative = generate_narrative(analysis, image_files)
        save_narrative(narrative)
        print("Pipeline completed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python autolysis.py <dataset.csv>")
        sys.exit(1)
    main(sys.argv[1])
