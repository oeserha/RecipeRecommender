import streamlit as st
import requests
import json

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
username = st.sidebar.text_input("Username")

# Allergies - multi-select with common options and ability to add custom ones
allergy_options = ["peanuts", "shellfish", "dairy", "gluten", "eggs", "soy", "tree nuts", "fish"]
allergies = st.sidebar.multiselect(
    "Select allergies",
    options=allergy_options,
    default=[]
)

# Food preferences section
st.sidebar.subheader("Food Preferences")

# Food likes - text input with comma separation
likes_input = st.sidebar.text_input("Foods you like (comma separated)")
likes = [item.strip() for item in likes_input.split(",")] if likes_input else []

# Food dislikes - text input with comma separation
dislikes_input = st.sidebar.text_input("Foods you dislike (comma separated)")
dislikes = [item.strip() for item in dislikes_input.split(",")] if dislikes_input else []

# Macros section with select boxes
st.sidebar.subheader("Macros Preferences")
col1, col2, col3 = st.sidebar.columns(3)
with col1:
    protein = st.selectbox("Protein", ["low", "medium", "high"], index=1)
with col2:
    carbs = st.selectbox("Carbs", ["low", "medium", "high"], index=1)
with col3:
    fats = st.selectbox("Fats", ["low", "medium", "high"], index=1)

# Previous recipes ratings section - container that can dynamically add more items
st.sidebar.subheader("Rate Previous Recipes")

# Initialize session state for recipes if it doesn't exist
if 'recipes_tried' not in st.session_state:
    st.session_state.recipes_tried = [{"recipe_id": "", "rating": "3"}]

# Function to add another recipe rating field
def add_recipe_rating():
    st.session_state.recipes_tried.append({"recipe_id": "", "rating": "3"})

# Function to remove a recipe rating field
def remove_recipe_rating(index):
    if len(st.session_state.recipes_tried) > 1:
        st.session_state.recipes_tried.pop(index)

# Display recipe rating inputs
for i, recipe in enumerate(st.session_state.recipes_tried):
    cols = st.sidebar.columns([3, 2, 1])
    with cols[0]:
        st.session_state.recipes_tried[i]["recipe_id"] = st.text_input(
            "Recipe ID", 
            value=recipe["recipe_id"], 
            key=f"recipe_id_{i}"
        )
    with cols[1]:
        st.session_state.recipes_tried[i]["rating"] = st.select_slider(
            "Rating",
            options=["1", "2", "3", "4", "5"],
            value=recipe["rating"],
            key=f"rating_{i}"
        )
    with cols[2]:
        if st.button("🗑️", key=f"delete_{i}"):
            remove_recipe_rating(i)
            st.rerun()

# Button to add another recipe rating
st.sidebar.button("Add Recipe Rating", on_click=add_recipe_rating)

# Main content - Current request parameters
st.header("Recipe Search Parameters")

# Available ingredients multi-line input
ingredients_input = st.text_area("Ingredients Available (one per line)")
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

# API Endpoint configuration
st.header("API Configuration")
api_endpoint = st.text_input("API Endpoint URL", "https://your-api-endpoint.amazonaws.com/recipes")

# Function to prepare request data
def prepare_request_data():
    # Filter out empty recipe ratings
    valid_recipes = [
        recipe for recipe in st.session_state.recipes_tried 
        if recipe["recipe_id"] and recipe["recipe_id"].strip()
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

# API submission and response display
if st.button("Find Recipes"):
    with st.spinner("Searching for recipes..."):
        try:
            request_data = prepare_request_data()
            
            # Check required fields
            if not username:
                st.error("Please enter a username")
            elif not ingredients_available:
                st.error("Please enter at least one available ingredient")
            else:
                response = requests.post(
                    api_endpoint,
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                # Create expander for API response details
                with st.expander("API Response Details", expanded=True):
                    st.write(f"Status Code: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            response_data = response.json()
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
                                    st.markdown(f"### {i+1}. {recipe.get('name', 'Recipe')}")
                                    
                                    # Create three columns for recipe details
                                    col1, col2, col3 = st.columns([2, 1, 1])
                                    
                                    with col1:
                                        if "description" in recipe:
                                            st.markdown(f"*{recipe['description']}*")
                                        
                                        if "instructions" in recipe:
                                            st.subheader("Instructions")
                                            instructions = recipe["instructions"]
                                            if isinstance(instructions, list):
                                                for j, step in enumerate(instructions):
                                                    st.markdown(f"{j+1}. {step}")
                                            else:
                                                st.write(instructions)
                                    
                                    with col2:
                                        if "ingredients" in recipe:
                                            st.subheader("Ingredients")
                                            ingredients = recipe["ingredients"]
                                            if isinstance(ingredients, list):
                                                for ingredient in ingredients:
                                                    if isinstance(ingredient, dict):
                                                        st.write(f"• {ingredient.get('name', '')}: {ingredient.get('amount', '')}")
                                                    else:
                                                        st.write(f"• {ingredient}")
                                            else:
                                                st.write(ingredients)
                                    
                                    with col3:
                                        if "cooking_time" in recipe:
                                            st.metric("Cooking Time", f"{recipe['cooking_time']} min")
                                        if "calories" in recipe:
                                            st.metric("Calories", recipe['calories'])
                                        if "protein" in recipe:
                                            st.metric("Protein", f"{recipe['protein']}g")
                                    
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