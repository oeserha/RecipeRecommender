# Install required packages quietly
!pip install -q s3fs pandas sagemaker
!pip install -q sentence-transformers pinecone

# Import necessary libraries
from sentence_transformers import SentenceTransformer  # For generating embeddings
import numpy as np
from pinecone import Pinecone, ServerlessSpec         # For vector database indexing
import pandas as pd
import sagemaker
from sagemaker.huggingface import HuggingFaceModel    # For deploying HuggingFace models on SageMaker
import boto3                                           # AWS SDK for Python to access S3
import io                                              # For handling byte streams

def embed_and_upsert(model_name):
    # Initialize S3 client and define the S3 bucket and file path
    s3 = boto3.client('s3')
    bucket = 'cs401r-mlops-final'
    key = 'preprocessed-data/preprocessed_data.csv'

    # Load preprocessed recipe data from S3 into a Pandas DataFrame
    obj = s3.get_object(Bucket=bucket, Key=key)
    df = pd.read_csv(io.BytesIO(obj['Body'].read()))
    print(f"Columns available: {df.columns.tolist()}")

    # Ensure required columns exist in the dataset
    if 'RecipeId' not in df.columns or 'EmbeddingSentence' not in df.columns:
        raise ValueError("Required columns 'RecipeId' or 'EmbeddingSentence' not found")

    # Limit data to 1,000 entries for testing/demo purposes
    recipe_ids = df['RecipeId'].tolist()[:1000]
    texts_to_embed = df['EmbeddingSentence'].astype(str).tolist()[:1000]
    recipe_name = df['Name'].tolist()[:1000]
    cook_time = df['CookTime'].tolist()[:1000]
    prep_time = df['PrepTime'].tolist()[:1000]
    description = df['Description'].tolist()[:1000]
    ingredients = df['RecipeIngredientQuantities'].tolist()[:1000]
    amounts = df["RecipeIngredientParts"].tolist()[:1000]
    units = df['RecipeServings'].tolist()[:1000]
    instructions = df['RecipeInstructions'].tolist()[:1000]

    # Create a dictionary mapping recipe IDs to their embedding text
    recipe_dict = dict(zip(recipe_ids, texts_to_embed))
    print(f"Found {len(texts_to_embed)} recipes to embed")

    # Load the sentence transformer model
    model = SentenceTransformer(model_name)

    # Generate embeddings in batches
    batch_size = 32
    all_embeddings = []
    for i in range(0, len(texts_to_embed), batch_size):
        batch_texts = texts_to_embed[i:i + batch_size]
        batch_embeddings = model.encode(batch_texts, show_progress_bar=True)
        all_embeddings.extend(batch_embeddings)

    # Convert NumPy arrays to lists for Pinecone compatibility
    embeddings_list = [embedding.tolist() for embedding in all_embeddings]
    print(f"Generated {len(embeddings_list)} embeddings of dimension {len(embeddings_list[0])}")

    # Initialize Pinecone and check if index exists
    pc_api_key = "NOT TELLING YOU"
    pc = Pinecone(api_key=pc_api_key)

    INDEX_NAME = "recipe-recommendations"
    DIMENSION = len(embeddings_list[0])  # Embedding dimensionality

    # Create index if it doesn't already exist
    existing_indexes = [index.name for index in pc.list_indexes()]
    if INDEX_NAME not in existing_indexes:
        pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        print(f"Created new index: {INDEX_NAME}")
    else:
        print(f"Using existing index: {INDEX_NAME}")

    # Connect to the index
    index = pc.Index(INDEX_NAME)

    # Prepare data to upsert to Pinecone (vector + metadata)
    vectors_to_upsert = []
    for i in range(len(recipe_ids)):
        vectors_to_upsert.append({
            "id": str(recipe_ids[i]),  # Pinecone requires string IDs
            "values": embeddings_list[i],  # The actual embedding
            "metadata": {
                "recipe_id": str(recipe_ids[i]),
                "recipe_name": str(recipe_name[i]),
                "ingredients": str(ingredients[i]),
                "amounts": str(amounts[i]),
                "units": str(units[i]),
                "instructions": str(instructions[i]),
                "cook_time": str(cook_time[i]),
                "prep_time": str(prep_time[i]),
                "description": str(description[i]),
            }
        })

    # Upsert data to Pinecone in batches
    batch_size = 100
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i:i + batch_size]
        index.upsert(vectors=batch)
        print(f"Upserted batch {i // batch_size + 1}/{(len(vectors_to_upsert) - 1) // batch_size + 1}")

    print(f"Successfully uploaded {len(vectors_to_upsert)} vectors to Pinecone")

# Run the full embedding + upsert pipeline using the specified SentenceTransformer model
embed_and_upsert('all-MiniLM-L6-v2')
