import pandas as pd
import json
from sentence_transformers import SentenceTransformer, util
import time
import boto3
import shutil
import torch

from transformers import AutoModel, AutoTokenizer
import tarfile
import os
from urllib.parse import urlparse

import sagemaker
from sagemaker import get_execution_role, Model, image_uris
from sagemaker.model import ModelPackage
import shutil

from pinecone import Pinecone

def SelectModel(num_test=None):
    uri = "s3://cs401r-mlops-final/preprocessed-data/preprocessed_data.csv"
    full_data = pd.read_csv(uri)

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
        print(f"Best Match: {best_match.get("Name")}, Score: {best_score}")

    times_proportional = [1 - t / max(times) for t in times]
    scores_proportional = [1 - t / max(scores) for t in scores]
    total_score = [x + y for x, y in zip(times_proportional, scores_proportional)]

    model_idx = total_score.index(max(total_score))
    best_model = models_to_test[model_idx]

    print(f"Best Model: {best_model}")

    return best_model


def CreateModelGroup(group_name, group_description):
    client = boto3.client('sagemaker')

    response = client.create_model_package_group(
        ModelPackageGroupName=group_name,
        ModelPackageGroupDescription=group_description
    )


# create model
def RegisterModel(best_model, group_name):
    try:
        model_name = best_model[best_model.rfind('/')+1:]
    except:
        model_name = best_model

    ### Download Model
    model_uri = f"s3://cs401r-mlops-final/model_artifacts/models/{model_name}.tar.gz"
    parsed = urlparse(model_uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")

    model_id = best_model
    model_dir = f"{model_name}"
    tar_path = f"{model_name}.tar.gz"

    # Download model and tokenizer
    AutoModel.from_pretrained(model_id).save_pretrained(model_dir)
    AutoTokenizer.from_pretrained(model_id).save_pretrained(model_dir)

    if not os.path.exists(tar_path):
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(model_dir, arcname=".")

    # Upload to S3
    s3 = boto3.client("s3")
    s3.upload_file(tar_path, bucket, key)

    print("Model Downloaded")

    session = sagemaker.Session()
    region = session.boto_region_name
    role = sagemaker.get_execution_role()
    
    huggingface_image_uri = image_uris.retrieve(
        framework="huggingface",
        region=region,
        version="4.26.0",                  
        py_version="py39",                 
        base_framework_version="pytorch1.13.1",  
        image_scope="inference",           
        instance_type="ml.m5.large"
    )
    
    # Create a SageMaker Model object
    hf_model = Model(
        image_uri=huggingface_image_uri,
        model_data=model_uri,
        role=role,
        sagemaker_session=session,
        env={'HF_TASK': 'feature-extraction'}
    )
    
    # Register the model
    model_package = hf_model.register(
        content_types=["application/json"],
        response_types=["application/json"],
        inference_instances=["ml.m5.large"],
        transform_instances=["ml.m5.large"],
        model_package_group_name=group_name,
        approval_status="Approved"  # or "PendingManualApproval" if you want to review before deploying
    )

    print("Model Registered")

    model_package_arn = model_package.model_package_arn  # from the previous step

    # Create a model from the registered package
    registered_model = ModelPackage(
        role=role,
        model_package_arn=model_package_arn,
        sagemaker_session=session
    )

    version = model_package_arn.split("/")[-1]
    endpoint_name = f"{model_name}-endpoint-{version}"

    predictor = registered_model.deploy(
        initial_instance_count=1,
        instance_type="ml.m5.large",
        endpoint_name=endpoint_name,
        environment={
            "HF_TASK": "feature-extraction"
        }
    )

    print("Model Deployed")

    shutil.rmtree(model_dir)
    os.remove("all-MiniLM-L6-v2.tar.gz")
    print('Temp Model Artifacts Deleted')

def GetEndpointName(group_name):
    sm = boto3.client('sagemaker')
    runtime = boto3.client('sagemaker-runtime')

    # Step 1: Get all model package ARNs in the model group (approved or not)
    packages = sm.list_model_packages(
        ModelPackageGroupName=group_name,
        SortBy='CreationTime',
        SortOrder='Descending',
        MaxResults=10
    )['ModelPackageSummaryList']

    model_package_arns = {pkg['ModelPackageArn'] for pkg in packages}

    # Step 2: List all models and find ones that use any of these packages
    models = sm.list_models()['Models']
    model_names = []

    for model in models:
        model_desc = sm.describe_model(ModelName=model['ModelName'])
        containers = model_desc.get('Containers', [])
        if not containers:  # single-container
            containers = [model_desc.get('PrimaryContainer', {})]

        for container in containers:
            if container.get('ModelPackageName') in model_package_arns:
                model_names.append(model['ModelName'])
                break

    if not model_names:
        raise Exception("No SageMaker model found using packages from the model group.")

    # Step 3: Look for endpoint using any of those models
    endpoints = sm.list_endpoints()['Endpoints']
    endpoint_name = None

    for ep in endpoints:
        ep_desc = sm.describe_endpoint(EndpointName=ep['EndpointName'])
        ep_config_name = ep_desc['EndpointConfigName']
        ep_config = sm.describe_endpoint_config(EndpointConfigName=ep_config_name)
        for variant in ep_config['ProductionVariants']:
            if variant['ModelName'] in model_names:
                endpoint_name = ep['EndpointName']
                break
        if endpoint_name:
            break

    if not endpoint_name:
        raise Exception("No endpoint found using models from the model group.")

    return endpoint_name


