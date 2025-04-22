import streamlit as st
import requests
import json
import ast

st.set_page_config(
    page_title="Recipe Finder",
    page_icon="🍽️",
    layout="wide"
)

# Main app header
st.title("🍽️ Recipe Finder")
st.markdown("Find personalized recipes based on your preferences and available ingredients")

# Create sidebar for user profile information
st.sidebar.title("User Profile")

# Username input
username = st.sidebar.text_input("Username", "User123")

# Allergies - multi-select with common options and ability to add custom ones
allergy_options = ["peanuts", "shellfish", "dairy", "gluten", "eggs", "soy", "tree nuts", "fish"]
allergies = st.sidebar.multiselect(
    "Select allergies",
    options=allergy_options,
    default=["peanuts"]
)

# Food preferences section
st.sidebar.subheader("Food Preferences")

# Food likes - text input with comma separation
likes_input = st.sidebar.text_input("Foods you like (comma separated)", "Chicken, Rice, Broccoli")
likes = [item.strip() for item in likes_input.split(",")] if likes_input else []

# Food dislikes - text input with comma separation
dislikes_input = st.sidebar.text_input("Foods you dislike (comma separated)", "Artichokes, Mushrooms")
dislikes = [item.strip() for item in dislikes_input.split(",")] if dislikes_input else []

# Macros section with select boxes
st.sidebar.subheader("Macros Preferences")
col1, col2, col3 = st.sidebar.columns(3)
with col1:
    protein = st.selectbox("Protein", ["low", "medium", "high"], index=2)
with col2:
    carbs = st.selectbox("Carbs", ["low", "medium", "high"], index=0)
with col3:
    fats = st.selectbox("Fats", ["low", "medium", "high"], index=1)

# Main content - Current request parameters
st.header("Recipe Search Parameters")

# Available ingredients multi-line input
ingredients_input = st.text_area("Ingredients Available (one per line)", "Rice\nCheese\nBeans")
ingredients_available = [item.strip() for item in ingredients_input.split("\n") if item.strip()]

# Recipe constraints - time, meal type and preferences
col1, col2 = st.columns(2)
with col1:
    max_time = st.slider("Maximum Preparation Time (minutes)", 5, 120, 30)
    meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack", "Dessert"])

with col2:
    spice_level = st.select_slider(
        "Spice Level",
        options=["mild", "medium", "hot", "very hot"],
        value="medium"
    )
    diet_type = st.selectbox(
        "Diet Type", 
        ["none", "vegetarian", "vegan", "keto", "paleo", "gluten-free", "dairy-free"]
    )

# Hardcoded API endpoint
api_endpoint = "https://59z9wfy750.execute-api.us-west-2.amazonaws.com/dev/recommender"

# Function to prepare request data
def prepare_request_data():
    # Filter out empty recipe ratings
    valid_recipes = [
    ]
    
    # Convert recipe IDs to integers if possible
    for recipe in valid_recipes:
        try:
            recipe["recipe_id"] = int(recipe["recipe_id"])
        except ValueError:
            # Keep as string if not convertible to int
            pass
    
    # Build the request JSON
    request_data = {
        "user": {
            "username": username,
            "allergies": allergies,
            "likes": likes,
            "dislikes": dislikes,
            "macros": {
                "protein": protein,
                "carbs": carbs,
                "fats": fats
            },
            "recipes_tried": valid_recipes
        },
        "request": {
            "ingredients_available": ingredients_available,
            "max_time_minutes": max_time,
            "meal_type": meal_type,
            "preferences": {
                "spice_level": spice_level,
                "diet_type": diet_type
            }
        }
    }
    
    return request_data

# Display the current request JSON
if st.checkbox("Show Request JSON"):
    request_data = prepare_request_data()
    st.json(request_data)

# Helper function to parse string representations of lists
def parse_list_string(list_string):
    try:
        if list_string and isinstance(list_string, str):
            # Remove quotes and brackets if present
            list_string = list_string.strip("[]")
            # Split by commas and clean up each item
            items = [item.strip().strip("'\"") for item in list_string.split(",")]
            return [item for item in items if item]
        elif isinstance(list_string, list):
            return list_string
        else:
            return []
    except Exception as e:
        st.error(f"Error parsing list: {str(e)}")
        return []

# API submission and response display
if st.button("Find Recipes"):
    with st.spinner("Searching for recipes..."):
        try:
            request_data = prepare_request_data()
            # Send the request to the API
            
            # Check required fields
            if not username:
                st.error("Please enter a username")
            elif not ingredients_available:
                st.error("Please enter at least one available ingredient")
            else:
                # For testing, you can use a sample response instead of making an actual API call
                # Uncomment the real API call when ready
                response = requests.get(
                    api_endpoint,
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                # Create expander for API response details
                with st.expander("API Response Details", expanded=True):
                    st.write(f"Status Code: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            response_data = response.json()['body']
                            # Check if response_data is a string and parse it
                            if isinstance(response_data, str):
                                # Attempt to parse the string as JSON
                                try:
                                    response_data = json.loads(response_data)
                                except json.JSONDecodeError:
                                    st.error("Could not parse the API response as JSON")
                                    st.text(response_data)
                                    
                            
                            st.success("Recipes found successfully!")
                            
                            # Display the recipes
                            st.subheader("Recommended Recipes")
                            
                            # Handle different possible response formats
                            if isinstance(response_data, dict) and "recipes" in response_data:
                                recipes = response_data["recipes"]
                            elif isinstance(response_data, list):
                                recipes = response_data
                            else:
                                recipes = [response_data]

                            
                            # Display each recipe
                            for i, recipe in enumerate(recipes):
                                with st.container():
                                    # Get recipe metadata
                                    metadata = recipe.get('metadata', {})
                                    recipe_name = metadata.get('recipe_name', f"Recipe {recipe.get('id', i+1)}")
                                    
                                    st.markdown(f"### {i+1}. {recipe_name}")
                                    
                                    # Create columns for recipe details
                                    col1, col2, col3 = st.columns([2, 1, 1])
                                    
                                    with col1:
                                        # Description
                                        if "description" in metadata:
                                            st.markdown(f"*{metadata['description']}*")
                                        
                                        # Instructions
                                        if "instructions" in metadata:
                                            st.subheader("Instructions")
                                            try:
                                                # Try to parse the string as a Python list
                                                instructions = ast.literal_eval(metadata["instructions"]) if isinstance(metadata["instructions"], str) else metadata["instructions"]
                                                
                                                if isinstance(instructions, list):
                                                    for j, step in enumerate(instructions):
                                                        st.markdown(f"{j+1}. {step}")
                                                else:
                                                    st.write(instructions)
                                            except (ValueError, SyntaxError) as e:
                                                st.error(f"Could not parse instructions: {str(e)}")
                                                st.write(metadata["instructions"])
                                    
                                    with col2:
                                        # Ingredients
                                        st.subheader("Ingredients")
                                        
                                        try:
                                            # Get ingredients and amounts
                                            ingredients_list = parse_list_string(metadata.get("ingredients", "[]"))
                                            amounts_list = parse_list_string(metadata.get("amounts", "[]"))
                                            
                                            # Display ingredients with amounts if available
                                            if amounts_list:
                                                for j, amount in enumerate(amounts_list):
                                                    # If we have a matching ingredient quantity, display it
                                                    if j < len(ingredients_list):
                                                        st.write(f"• {amount}: {ingredients_list[j] if ingredients_list else ''}")
                                                    else:
                                                        st.write(f"• {amount}")
                                            elif ingredients_list:
                                                # If we only have ingredients without amounts
                                                for ingredient in ingredients_list:
                                                    st.write(f"• {ingredient}")
                                            else:
                                                st.write("No ingredients information available")
                                                
                                        except Exception as e:
                                            st.error(f"Error displaying ingredients: {str(e)}")
                                    
                                    with col3:
                                        # Recipe metrics
                                        total_time = 0
                                        try:
                                            # Add prep time if available
                                            if "prep_time" in metadata:
                                                prep_time = float(metadata["prep_time"])
                                                st.metric("Prep Time", f"{prep_time} hr" if prep_time >= 1 else f"{int(prep_time * 60)} min")
                                                total_time += prep_time
                                            
                                            # Add cook time if available
                                            if "cook_time" in metadata:
                                                if metadata["cook_time"] != "nan":
                                                    cook_time = float(metadata["cook_time"])
                                                    st.metric("Cook Time", f"{cook_time} hr" if cook_time >= 1 else f"{int(cook_time * 60)} min")
                                                    total_time += cook_time
                                            
                                            # Show total time
                                            if total_time > 0:
                                                st.metric("Total Time", f"{total_time} hr" if total_time >= 1 else f"{int(total_time * 60)} min")
                                            
                                            # Show units/servings
                                            if "units" in metadata:
                                                st.metric("Servings", metadata["units"])
                                                
                                            # Show match score
                                            if "score" in recipe:
                                                st.metric("Match Score", f"{recipe['score']:.2f}")
                                                
                                        except ValueError as e:
                                            st.error(f"Error calculating times: {str(e)}")
                                    
                                    st.divider()
                            
                        except json.JSONDecodeError:
                            st.error("Could not parse the API response as JSON")
                            st.text(response.text)
                    else:
                        st.error(f"Error: Received status code {response.status_code}")
                        st.text(response.text)
        except requests.RequestException as e:
            st.error(f"Request failed: {str(e)}")

# Add a footer with additional information
st.markdown("---")
st.markdown("Made with Streamlit ❤️")