from sagemaker.processing import ScriptProcessor, ProcessingInput
import sagemaker
import boto3
from sagemaker import get_execution_role
from model_management import GetEndpointName

role = get_execution_role()
endpoint_name = GetEndpointName('recipe-recommender-models')
bucket = 'cs401r-mlops-final'
capture_data_prefix = f'data-capture/{endpoint_name}'
region = 'us-west-2'

session = sagemaker.Session(boto_session=boto3.Session(region_name=region))

script_processor = ScriptProcessor(
    image_uri='763104351884.dkr.ecr.us-west-2.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3',
    command=['python3'],
    role=role,
    instance_count=1,
    instance_type='ml.m5.large',
    base_job_name='embedding-monitor',
    sagemaker_session=session
)

script_processor.run(
    code='monitor.py',
    inputs=[
        ProcessingInput(
            source=f's3://{bucket}/{capture_data_prefix}',
            destination='/opt/ml/processing/input'
        )
    ],
    wait=True,
    logs=True
)
