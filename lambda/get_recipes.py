import json
import boto3
import os

# Initialize the SageMaker runtime client
sagemaker_runtime = boto3.client('sagemaker-runtime')

def lambda_handler(event, context):
    """
    Lambda function that processes recipe recommendation requests
    
    Parameters:
    - event: The input JSON event
    - context: Lambda context object
    
    Returns:
    - JSON response with recipe recommendations
    """
    try:
        # Extract user and request data from the input
        user_data = event.get('user', {})
        request_data = event.get('request', {})
        
        # Build the query string from user preferences and request
        query_string = build_query_string(user_data, request_data)
        
        # Call the SageMaker endpoint with the query string
        response = call_sagemaker_endpoint(query_string)
        
        return {
            'statusCode': 200,
            'body': response,
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
    except Exception as e:
        # Log the error and return an error response
        print(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error processing recipe recommendation request',
                'details': str(e)
            }),
            'headers': {
                'Content-Type': 'application/json'
            }
        }

def build_query_string(user_data, request_data):
    """
    Builds a query string from user data and request data
    
    Parameters:
    - user_data: Dictionary containing user information
    - request_data: Dictionary containing request details
    
    Returns:
    - String containing all relevant information for the model
    """
    query_parts = []
    
    # Add macros information
    macros = user_data.get('macros', {})
    if macros:
        for macro_type, level in macros.items():
            query_parts.append(f"{level} {macro_type}")
    
    # Add available ingredients
    ingredients = request_data.get('ingredients_available', [])
    if ingredients:
        query_parts.extend(ingredients)
    
    # Add user likes
    likes = user_data.get('likes', [])
    if likes:
        query_parts.extend(likes)
    
    # Add user dislikes (prefixed with "no")
    dislikes = user_data.get('dislikes', [])
    if dislikes:
        query_parts.extend([f"no {item}" for item in dislikes])
    
    # Add user allergies (prefixed with "allergy")
    allergies = user_data.get('allergies', [])
    if allergies:
        query_parts.extend([f"allergy {item}" for item in allergies])
    
    # Add max time
    max_time = request_data.get('max_time_minutes')
    if max_time:
        query_parts.append(f"max_time {max_time}")
    
    # Add meal type
    meal_type = request_data.get('meal_type')
    if meal_type:
        query_parts.append(meal_type)
    
    # Add spice level
    preferences = request_data.get('preferences', {})
    spice_level = preferences.get('spice_level')
    if spice_level:
        query_parts.append(f"spice {spice_level}")
    
    # Add diet type
    diet_type = preferences.get('diet_type')
    if diet_type:
        query_parts.append(diet_type)
    
    # Join all parts with spaces
    return " ".join(query_parts)

def call_sagemaker_endpoint(query_string):
    """
    Calls the SageMaker endpoint with the query string
    
    Parameters:
    - query_string: The formatted query string
    
    Returns:
    - JSON response from the SageMaker endpoint
    """
    # Get the SageMaker endpoint name from environment variable
    endpoint_name = os.environ.get('SAGEMAKER_ENDPOINT_NAME')
    
    if not endpoint_name:
        raise ValueError("SAGEMAKER_ENDPOINT_NAME environment variable is not set")
    
    # Prepare the request payload
    request_body = json.dumps({'query': query_string})
    
    # Call the SageMaker endpoint
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType='application/json',
        Body=request_body
    )
    
    # Parse and return the response
    response_body = response['Body'].read().decode('utf-8')
    return json.loads(response_body)