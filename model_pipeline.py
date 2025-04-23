import boto3
import sagemaker
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep
from sagemaker.workflow.properties import PropertyFile
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.processing import ScriptProcessor
from sagemaker import image_uris
import json
import os

# Initialize SageMaker session
session = sagemaker.Session()
region = session.boto_region_name
role = sagemaker.get_execution_role()
bucket = "cs401r-mlops-final"
prefix = "mlops-pipeline"

# Define the model group name
model_group_name = "recipe-recommender-models"

# Upload requirements.txt to S3
requirements_file = "requirements.txt"
requirements_s3_uri = f"s3://{bucket}/{prefix}/requirements/{requirements_file}"
boto3.Session().resource('s3').Object(
    bucket, f"{prefix}/requirements/{requirements_file}"
).upload_file(requirements_file)

# Define the Python processor for model selection
selection_processor = ScriptProcessor(
    image_uri=image_uris.retrieve(
        framework="pytorch",
        region=region,
        version="1.13.1",
        py_version="py39",
        image_scope="training",
        instance_type="ml.m5.large"
    ),
    role=role,
    instance_count=1,
    instance_type="ml.m5.large",
    base_job_name="model-selection",
    command=["python"],
    env={'PIP_PACKAGES': 'sentence-transformers'}
)

# Define the model selection step
best_model_output = ProcessingOutput(
    output_name="best_model",
    source="/opt/ml/processing/output",
    destination=f"s3://{bucket}/{prefix}/model-selection"
)

# Define PropertyFile for best model
best_model_property_file = PropertyFile(
    name="BestModelSelection",
    output_name="best_model",
    path="best_model.json"
)

model_selection_step = ProcessingStep(
    name="ModelSelection",
    processor=selection_processor,
    code="pipeline_steps/model_selection.py",
    inputs=[
        ProcessingInput(
            source=requirements_s3_uri,
            destination="/opt/ml/processing/input/requirements"
        )
    ],
    outputs=[best_model_output],
    property_files=[best_model_property_file],
    job_arguments=[
        "--install-dependencies",
        "--requirements-file", "/opt/ml/processing/input/requirements/requirements.txt"
    ]
)

# Define the Python processor for model registration and deployment
deploy_processor = ScriptProcessor(
    image_uri=image_uris.retrieve(
        framework="pytorch",
        region=region,
        version="1.13.1",
        py_version="py39",
        image_scope="training",
        instance_type="ml.m5.large"
    ),
    role=role,
    instance_count=1,
    instance_type="ml.m5.large",
    base_job_name="model-registration",
    command=["python"],
    env={'PIP_PACKAGES': 'sentence-transformers'}
)

# Define the model registration step
model_reg_step = ProcessingStep(
    name="ModelRegistrationAndDeployment",
    processor=deploy_processor,
    code="pipeline_steps/model_reg_deploy.py",
    job_arguments=[
        "--install-dependencies",
        "--model-group-name", model_group_name,
        "--requirements-file", "/opt/ml/processing/input/requirements/requirements.txt"
    ],
    inputs=[
        ProcessingInput(
            source=model_selection_step.properties.ProcessingOutputConfig.Outputs["best_model"].S3Output.S3Uri,
            destination="/opt/ml/processing/input/model"
        ),
        ProcessingInput(
            source=requirements_s3_uri,
            destination="/opt/ml/processing/input/requirements"
        )
    ]
)

# Create the pipeline
pipeline = Pipeline(
    name="RecipeModelManagerPipeline",
    steps=[model_selection_step, model_reg_step],
    sagemaker_session=session
)

# Define the pipeline parameters
pipeline_definition = pipeline.definition()
pipeline.upsert(role_arn=role)

# Execute the pipeline
execution = pipeline.start()