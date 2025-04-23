import json
import boto3
import shutil
import tarfile
import os
from urllib.parse import urlparse
import subprocess
import sys

# create model
def RegisterModel(best_model, group_name):
    from transformers import AutoModel, AutoTokenizer
    import sagemaker
    from sagemaker.model import Model, ModelPackage
    from sagemaker import image_uris

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
        approval_status="Approved"  # or "PendingManualApproval"
    )

    print("Model Registered")

    model_package_arn = model_package.model_package_arn

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--install-dependencies', action='store_true')
    parser.add_argument('--requirements-file', type=str, default='requirements.txt')
    parser.add_argument('--model-group-name', type=str, required=True)
    args = parser.parse_args()

    if args.install_dependencies:
        print("Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", args.requirements_file])
        print("Dependencies installed successfully.")

    best_model_path = "/opt/ml/processing/input/model/best_model.json"
    print(f"Reading best model from: {best_model_path}")
    
    with open(best_model_path, 'r') as f:
        best_model = json.load(f)['best_model']
    
    print(f"Best model selected: {best_model}")

    # Call your function
    RegisterModel(best_model, args.model_group_name)