!pip install -q s3fs pandas sagemaker

!pip install -q sentence-transformers pinecone

from sentence_transformers import SentenceTransformer
import numpy as np

from pinecone import Pinecone, ServerlessSpec

import pandas as pd
import sagemaker
from sagemaker.huggingface import HuggingFaceModel

import boto3
import pandas as pd
import io


def embed_and_upsert(model_name):

    s3 = boto3.client('s3')
    bucket = 'cs401r-mlops-final'
    key = 'preprocessed-data/preprocessed_data.csv'
    
    obj = s3.get_object(Bucket=bucket, Key=key)
    df = pd.read_csv(io.BytesIO(obj['Body'].read()))
    print(f"Columns available: {df.columns.tolist()}")
    
    print("Columns available:", df.columns.tolist())
    
    if 'RecipeId' not in df.columns or 'EmbeddingSentence' not in df.columns:
        raise ValueError("Required columns 'RecipeId' or 'EmbeddingSentence' not found")
    
    recipe_ids = df['RecipeId'].tolist()
    # recipe_ids = recipe_ids[:1000]
    texts_to_embed = df['EmbeddingSentence'].astype(str).tolist()
    # texts_to_embed = texts_to_embed[:1000]
    
    recipe_dict = dict(zip(recipe_ids, texts_to_embed))
    
    print(f"Found {len(texts_to_embed)} recipes to embed")
    
    model = SentenceTransformer(model_name)
    
    batch_size = 32
    all_embeddings = []
    
    for i in range(0, len(texts_to_embed), batch_size):
        batch_texts = texts_to_embed[i:i + batch_size]
        batch_embeddings = model.encode(batch_texts, show_progress_bar=True)
        all_embeddings.extend(batch_embeddings)
    
    embeddings_list = [embedding.tolist() for embedding in all_embeddings]
    
    print(f"Generated {len(embeddings_list)} embeddings of dimension {len(embeddings_list[0])}")
    
    pc_api_key ="NOT_TELLING_YOU"
    pc = Pinecone(api_key=pc_api_key)
    
    INDEX_NAME = "recipe-recommendations"
    DIMENSION = len(embeddings_list[0])
    
    existing_indexes = [index.name for index in pc.list_indexes()]
    
    if INDEX_NAME not in existing_indexes:
        pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        print(f"Created new index: {INDEX_NAME}")
    else:
        print(f"Using existing index: {INDEX_NAME}")
    
    index = pc.Index(INDEX_NAME)
    
    vectors_to_upsert = []
    
    for i in range(len(recipe_ids)):
        vectors_to_upsert.append({
            "id": str(recipe_ids[i]),
            "values": embeddings_list[i], 
            "metadata": {
                "recipe_id": str(recipe_ids[i]),
            }
        })
    
    batch_size = 100
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i:i + batch_size]
        index.upsert(vectors=batch)
        print(f"Upserted batch {i//batch_size + 1}/{(len(vectors_to_upsert)-1)//batch_size + 1}")
    
    print(f"Successfully uploaded {len(vectors_to_upsert)} vectors to Pinecone")

embed_and_upsert('all-MiniLM-L6-v2')























