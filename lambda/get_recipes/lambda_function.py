import json
import boto3
import os
from pinecone import Pinecone

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
        print(f"[INFO] Received event: {json.dumps(event)}")
        
        # Extract user and request data from the input
        user_data = event.get('user', {})
        request_data = event.get('request', {})

        allergies = [s.lower() for s in user_data.get("allergies", [])]
        dislikes  = [s.lower() for s in user_data.get("dislikes",  [])]
        
        print(f"[INFO] User data: {json.dumps(user_data)}")
        print(f"[INFO] Request data: {json.dumps(request_data)}")
        print(f"[INFO] Allergies: {allergies}")
        print(f"[INFO] Dislikes : {dislikes}") 
        
        # Build the query string from user preferences and request
        query_string = build_query_string(user_data, request_data)
        print(f"[INFO] Built query string: {query_string}")
        
        # Call the SageMaker endpoint with the query string
        print("[INFO] Calling SageMaker endpoint...")
        embedding = call_sagemaker_endpoint(query_string)
        print(f"[INFO] Received embedding with length: {len(embedding)}")
        
        # Now use Pinecone to find similar recipes
        print("[INFO] Querying Pinecone...")
        recipes = query_pinecone(embedding)
        print(f"[INFO] Received {len(recipes)} recipes from Pinecone")

        # Filter out recipes that contain user allergies or dislikes
        print("[INFO] Filtering recipes for allergies and dislikes...")
        recipes = filterAllergiesAndDislikes(recipes, allergies, dislikes)
        print(f"[INFO] Filtered down to {len(recipes)} recipes after allergy/dislike check")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'recipes': recipes
            }),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
    except Exception as e:
        # Log the error and return an error response
        import traceback
        print(f"[ERROR] Error processing request: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
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
    print("[INFO] Building query string...")
    query_parts = []
    
    # Add macros information
    macros = user_data.get('macros', {})
    print(f"[INFO] Macros: {json.dumps(macros)}")
    if macros:
        for macro_type, level in macros.items():
            query_parts.append(f"{level} {macro_type}")
    
    # Add available ingredients
    ingredients = request_data.get('ingredients_available', [])
    print(f"[INFO] Ingredients: {json.dumps(ingredients)}")
    if ingredients:
        query_parts.extend(ingredients)
    
    # Add user likes
    likes = user_data.get('likes', [])
    print(f"[INFO] Likes: {json.dumps(likes)}")
    if likes:
        query_parts.extend(likes)
    
    # Add user dislikes (prefixed with "no")
    dislikes = user_data.get('dislikes', [])
    print(f"[INFO] Dislikes: {json.dumps(dislikes)}")
    if dislikes:
        query_parts.extend([f"no {item}" for item in dislikes])
    
    # Add user allergies (prefixed with "allergy")
    allergies = user_data.get('allergies', [])
    print(f"[INFO] Allergies: {json.dumps(allergies)}")
    if allergies:
        query_parts.extend([f"allergy {item}" for item in allergies])
    
    # Add max time
    max_time = request_data.get('max_time_minutes')
    print(f"[INFO] Max time: {max_time}")
    if max_time:
        query_parts.append(f"max_time {max_time}")
    
    # Add meal type
    meal_type = request_data.get('meal_type')
    print(f"[INFO] Meal type: {meal_type}")
    if meal_type:
        query_parts.append(meal_type)
    
    # Add spice level
    preferences = request_data.get('preferences', {})
    print(f"[INFO] Preferences: {json.dumps(preferences)}")
    spice_level = preferences.get('spice_level')
    print(f"[INFO] Spice level: {spice_level}")
    if spice_level:
        query_parts.append(f"spice {spice_level}")
    
    # Add diet type
    diet_type = preferences.get('diet_type')
    print(f"[INFO] Diet type: {diet_type}")
    if diet_type:
        query_parts.append(diet_type)
    
    # Join all parts with spaces
    result = " ".join(query_parts)
    print(f"[INFO] Final query string: {result}")
    return result

def call_sagemaker_endpoint(query_string):
    """
    Calls the SageMaker endpoint with the query string
    
    Parameters:
    - query_string: The formatted query string
    
    Returns:
    - Embedding vector from the SageMaker endpoint
    """
    # Get the SageMaker endpoint name from environment variable
    endpoint_name = os.environ.get('SAGEMAKER_ENDPOINT_NAME')
    print(f"[INFO] SageMaker endpoint name: {endpoint_name}")
    
    if not endpoint_name:
        raise ValueError("SAGEMAKER_ENDPOINT_NAME environment variable is not set")
    
    # Structure the request according to what the model expects
    request_body = json.dumps({"inputs": query_string})
    print(f"[INFO] Request body: {request_body}")
    
    # Call the SageMaker endpoint
    print(f"[INFO] Invoking SageMaker endpoint...")
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType='application/json',
        Body=request_body
    )
    
    # Parse the response
    response_body = response['Body'].read().decode('utf-8')
    print(f"[INFO] Response body length: {len(response_body)}")
    print(f"[INFO] Response body preview: {response_body[:100]}...")
    
    embedding_data = json.loads(response_body)
    print(f"[INFO] Embedding data type: {type(embedding_data)}")
    print(f"[INFO] Embedding data structure: {str(embedding_data)[:100]}...")
    
    # Take the first token embedding as the representation
    # This extracts the first vector from the array of token embeddings
    # Add more detailed logging to understand the structure
    print(f"[INFO] Embedding data length: {len(embedding_data)}")
    if embedding_data and len(embedding_data) > 0:
        print(f"[INFO] First element type: {type(embedding_data[0])}")
        print(f"[INFO] First element length: {len(embedding_data[0]) if hasattr(embedding_data[0], '__len__') else 'N/A'}")
        
        if embedding_data[0] and hasattr(embedding_data[0], '__len__') and len(embedding_data[0]) > 0:
            print(f"[INFO] First inner element type: {type(embedding_data[0][0])}")
            print(f"[INFO] First inner element length: {len(embedding_data[0][0]) if hasattr(embedding_data[0][0], '__len__') else 'N/A'}")
    
    # Check if the structure is as expected before accessing
    if not embedding_data or not isinstance(embedding_data, list) or len(embedding_data) == 0:
        raise ValueError("Unexpected embedding data structure: empty or not a list")
    
    if not embedding_data[0] or not isinstance(embedding_data[0], list) or len(embedding_data[0]) == 0:
        raise ValueError("Unexpected embedding data structure: first element empty or not a list")
    
    embedding_vector = embedding_data[0][0]
    print(f"[INFO] Extracted embedding vector length: {len(embedding_vector) if embedding_vector else 'N/A'}")
    
    return embedding_vector

def query_pinecone(embedding_vector):
    """
    Queries Pinecone to find recipes with similar embeddings
    
    Parameters:
    - embedding_vector: The embedding vector from SageMaker
    
    Returns:
    - List of recipe objects from Pinecone
    """
    # Initialize Pinecone client
    pinecone_api_key = os.environ.get('PINECONE_API_KEY')
    index_name = os.environ.get('PINECONE_INDEX_NAME')
    
    print(f"[INFO] Pinecone API key exists: {bool(pinecone_api_key)}")
    print(f"[INFO] Pinecone index name: {index_name}")
    
    if not all([pinecone_api_key, index_name]):
        raise ValueError("One or more Pinecone environment variables are not set")
    
    # Initialize Pinecone
    print("[INFO] Initializing Pinecone client...")
    pc = Pinecone(api_key=pinecone_api_key)
    
    # Connect to the index
    print(f"[INFO] Connecting to Pinecone index: {index_name}")
    index = pc.Index(index_name)
    
    # Perform the query
    top_k = int(os.environ.get('PINECONE_TOP_K', '5'))  # Default to 5 results if not specified
    print(f"[INFO] Querying Pinecone with top_k: {top_k}")
    
    query_response = index.query(
        vector=embedding_vector,
        top_k=top_k,
        include_values=True,
        include_metadata=True
    )
    
    print(f"[INFO] Pinecone query response received")
    
    # Extract and format the recipes
    recipes = []
    print(f"[INFO] Processing {len(query_response.matches) if hasattr(query_response, 'matches') else 0} matches")
    
    for match in query_response.matches:
        print(f"[INFO] Processing match with ID: {match.id}")
        print(f"[INFO] Match score: {match.score}")
        
        # Add the recipe with its score and metadata
        recipe = {
            'id': match.id,
            'score': match.score,
            'metadata': match.metadata
        }
        print(f"[INFO] Recipe ID: {match.id}")
        print(f"[INFO] Recipe score: {match.score}")
        recipes.append(recipe)
    
    print(f"[INFO] Returning {len(recipes)} recipes")
    return recipes

def filterAllergiesAndDislikes(
    matches: list,
    allergies: list[str] | None = None,
    dislikes:  list[str] | None = None
) -> list:
    """
    Returns list of matches that do not contain any allergens or disliked items.
    """
    allergies = set(a.lower() for a in (allergies or []))
    dislikes  = set(d.lower() for d in (dislikes  or []))

    safe_matches = []
    for m in matches:
        ing_raw  = m.get("metadata", {}).get("ingredients")
        ing_set  = set(i.lower() for i in _to_token_list(ing_raw))

        if ing_set & allergies:
            continue                
        if ing_set & dislikes:
            continue               

        safe_matches.append(m)

    return safe_matches

def _to_token_list(raw):
    """
    Normalize the 'ingredients' field into a list[str].
    """
    if raw is None:
        return []

    # Already a list?  Good.
    if isinstance(raw, list):
        return raw

    # String?  Strip brackets & quotes, then split on commas
    if isinstance(raw, str):
        cleaned = re.sub(r"[\[\]\"'()]", "", raw)
        return [tok.strip() for tok in cleaned.split(",") if tok.strip()]

    return []   # fallback