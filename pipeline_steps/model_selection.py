import json
import sys
import pandas as pd
from sentence_transformers import SentenceTransformer, util
import time
import boto3
import os
import subprocess

subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers"])

def SelectModel(num_test=None):

    # get recipe data
    uri = "s3://cs401r-mlops-final/preprocessed-data/preprocessed_data.csv"
    full_data = pd.read_csv(uri)

    # get test json
    bucket = "cs401r-mlops-final"
    json_key = "raw-data/test_request.txt"

    s3 = boto3.client("s3")

    json_response = s3.get_object(Bucket=bucket, Key=json_key)
    json_body = json_response['Body'].read().decode('utf-8')
    dict_request = json.loads(json_body)

    models_to_test = [
        "bert-base-uncased",
        "distilbert-base-uncased",
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/all-MiniLM-L12-v2",
        "sentence-transformers/all-mpnet-base-v2",
        "roberta-base"
    ]

    query = str(dict_request.get('request'))

    if num_test is not None:
        candidate_sentences = full_data['EmbeddingSentence'].loc[:num_test]
    else:
        candidate_sentences = full_data['EmbeddingSentence']

    matches = []
    scores = []
    times = []

    # getting best model
    for model_name in models_to_test:
        print(f"Testing model: {model_name}")
        model = SentenceTransformer(model_name)
        start = time.time()

        query_embedding = model.encode(query, convert_to_tensor=True)
        candidate_embeddings = model.encode(candidate_sentences, convert_to_tensor=True)
        cosine_scores = util.cos_sim(query_embedding, candidate_embeddings)[0]

        best_idx = cosine_scores.argmax().item()
        best_score = cosine_scores[best_idx].item()
        best_match = full_data[['RecipeId', 'Name']].loc[best_idx].to_dict()

        end = time.time()

        matches.append(best_match)
        scores.append(best_score)
        times.append((end - start) * 1000)
        # print(f"Best Match: {best_match.get("Name")}, Score: {best_score}")

    times_proportional = [1 - t / max(times) for t in times]
    scores_proportional = [1 - t / max(scores) for t in scores]
    total_score = [x + y for x, y in zip(times_proportional, scores_proportional)]

    model_idx = total_score.index(max(total_score))
    best_model = models_to_test[model_idx]

    print(f"Best Model: {best_model}")

    return best_model

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--install-dependencies', action='store_true')
    parser.add_argument('--requirements-file', type=str, default='requirements.txt')
    parser.add_argument('--num-test', type=int, default=1000)
    args = parser.parse_args()

    if args.install_dependencies:
        print("Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", args.requirements_file])
        print("Dependencies installed successfully.")

    best_model = SelectModel(num_test=args.num_test)

    # Save best model name to file
    output_dir = "/opt/ml/processing/output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "best_model.json")

    with open(output_path, "w") as f:
        json.dump({"best_model": best_model}, f)

    print(f"Best model ({best_model}) saved to {output_path}")
    sys.stdout.flush()
