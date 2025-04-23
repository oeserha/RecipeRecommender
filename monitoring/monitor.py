import os, json, boto3
import numpy as np
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity

def load_recent_data(data_dir):
    pairs = []
    for fname in os.listdir(data_dir):
        if fname.endswith(".jsonl"):
            with open(os.path.join(data_dir, fname)) as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        response = json.loads(record['captureData']['endpointOutput']['data'])
                        if isinstance(response, list) and len(response) == 2:
                            pairs.append(np.array([response[0], response[1]]))
                    except:
                        continue
    return np.array(pairs)

def compute_cosine_metrics(pairs):
    sims = [cosine_similarity([pair[0]], [pair[1]])[0][0] for pair in pairs if pair.shape[0] == 2]
    sims = np.array(sims)
    return {
        "cosine_mean": float(sims.mean()),
        "cosine_std": float(sims.std()),
        "cosine_min": float(sims.min()),
        "cosine_max": float(sims.max())
    }

def push_to_cloudwatch(metrics, namespace="EmbeddingMonitor"):
    cw = boto3.client("cloudwatch")
    for k, v in metrics.items():
        cw.put_metric_data(
            Namespace=namespace,
            MetricData=[{
                "MetricName": k,
                "Timestamp": datetime.utcnow(),
                "Value": v,
                "Unit": "None"
            }]
        )

if __name__ == "__main__":
    data_dir = "/opt/ml/processing/input"
    pairs = load_recent_data(data_dir)
    if len(pairs) > 0:
        metrics = compute_cosine_metrics(pairs)
        push_to_cloudwatch(metrics)
        print("Metrics pushed:", metrics)
    else:
        print("No valid data found.")
