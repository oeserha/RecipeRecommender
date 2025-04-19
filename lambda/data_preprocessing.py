import json
import re

import isodate
import boto3
import pandas as pd
import io
import os

# Hard-coded S3 bucket name
S3_BUCKET_NAME = "cs401r-mlops-final"
INPUT_PREFIX = "raw-data/"
OUTPUT_PREFIX = "preprocessed-data/"
RECIPES_FILE = "recipes.csv"
REVIEWS_FILE = "reviews.csv"
OUTPUT_FILE = "preprocessed_data.csv"

# Function to convert R vectors like c("item1", "item2") to Python lists
def convert_r_vector(value):
    if isinstance(value, str) and value.startswith('c(') and value.endswith(')'):
        # Extract items between quotes
        items = re.findall(r'"([^"]*)"', value)
        return items
    return value

# Function to convert ISO 8601 duration format (PT24H) to hours
def convert_duration(value):
    if isinstance(value, str) and value.startswith('PT'):
        try:
            duration = isodate.parse_duration(value)
            return duration.total_seconds() / 3600  # Convert to hours
        except:
            return value
    return value

def create_embedding_sentences(df):
    # Create a sentence for each recipe
    sentences = []
    for index, row in df.iterrows():
        s = ""
        keywords = row['Keywords']
        ingredients = row['RecipeIngredientParts']
        if isinstance(keywords, list):
            for i in keywords:
                s += i + " "
        for i in ingredients:
            s += i + " "
        s = s.strip()
        sentences.append(s)
    df['EmbeddingSentence'] = sentences
    return df

def lambda_handler(event, context):
    """
    AWS Lambda function that:
    1. Reads the CSV files from an S3 bucket
    2. Processes the data (e.g., converts R vectors to lists, handles durations, merges data)
    3. Writes the processed data back to S3 in a different path
    """
    try:
        recipe_data_key = os.path.join(INPUT_PREFIX, RECIPES_FILE)
        reviews_data_key = os.path.join(INPUT_PREFIX, REVIEWS_FILE)

        preprocessed_data_key = os.path.join(OUTPUT_PREFIX, OUTPUT_FILE)
        
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Read the CSV file from S3
        print(f"Reading CSV from s3://{S3_BUCKET_NAME}/{recipe_data_key}")
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=recipe_data_key)
        recipe_csv_content = response['Body'].read()
        
        recipe_df = pd.read_csv(io.BytesIO(recipe_csv_content))

        print(f"Reading CSV from s3://{S3_BUCKET_NAME}/{reviews_data_key}")
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=reviews_data_key)
        reviews_csv_content = response['Body'].read()

        reviews_df = pd.read_csv(io.BytesIO(reviews_csv_content))
        
        
        # Apply the conversion functions to all columns
        for col in recipe_df.columns:
            # Try to detect if the column contains R vectors
            if recipe_df[col].dtype == 'object':
                sample = recipe_df[col].dropna().iloc[0] if not recipe_df[col].dropna().empty else None
                if sample and isinstance(sample, str):
                    if sample.startswith('c('):
                        recipe_df[col] = recipe_df[col].apply(convert_r_vector)
                    elif sample.startswith('PT'):
                        recipe_df[col] = recipe_df[col].apply(convert_duration)

        def rank_macro_column(column):
            low_threshold = column.quantile(1/3)
            high_threshold = column.quantile(2/3)
            return column.apply(lambda x: 'low' if x <= low_threshold else 'high' if x > high_threshold else 'medium')

        # Apply the ranking function to the relevant columns
        recipe_df['FatRanking'] = rank_macro_column(recipe_df['FatContent'])
        recipe_df['ProteinRanking'] = rank_macro_column(recipe_df['ProteinContent'])
        recipe_df['CarbohydrateRanking'] = rank_macro_column(recipe_df['CarbohydrateContent'])

        augmented_df = create_embedding_sentences(recipe_df)

        reviews_df['Rating'] = reviews_df['Rating'].astype(float)
        reviews_df['Rating'] = reviews_df['Rating'].fillna(0)

        grouped_reviews_df = reviews_df.groupby('RecipeId').agg({'Rating': 'mean'}).reset_index()
        grouped_reviews_df = grouped_reviews_df.rename(columns={'Rating': 'AverageRating'})

        # Merge the two DataFrames on 'RecipeId'
        processed_df = pd.merge(augmented_df, grouped_reviews_df, on='RecipeId', how='left')
        processed_df['AverageRating'] = processed_df['AverageRating'].fillna(0)
        processed_df['AverageRating'] = processed_df['AverageRating'].astype(float)

        # =============================================
        # END OF DATA PROCESSING LOGIC
        # =============================================
        
        print(f"Processed data shape: {processed_df.shape}")
        
        # Convert the processed DataFrame back to CSV
        csv_buffer = io.StringIO()
        processed_df.to_csv(csv_buffer, index=False)
        
        # Write the processed CSV back to S3
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=preprocessed_data_key,
            Body=csv_buffer.getvalue(),
            ContentType='text/csv'
        )
        
        print(f"Processed CSV written to s3://{S3_BUCKET_NAME}/{preprocessed_data_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'CSV processed successfully',
                'input_files': {
                    'recipes': f"s3://{S3_BUCKET_NAME}/{recipe_data_key}",
                    'reviews': f"s3://{S3_BUCKET_NAME}/{reviews_data_key}"
                },
                'output_file': f"s3://{S3_BUCKET_NAME}/{preprocessed_data_key}",
                'rows_processed': len(recipe_df),
                'rows_output': len(processed_df)
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error processing CSV',
                'error': str(e)
            })
        }