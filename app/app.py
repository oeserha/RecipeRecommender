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
api_endpoint = st.text_input("API Endpoint URL", "https://59z9wfy750.execute-api.us-west-2.amazonaws.com/dev/recommender")

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
            print(request_data)  # Debugging line to check request data
            # Send the request to the API
            
            # Check required fields
            if not username:
                st.error("Please enter a username")
            elif not ingredients_available:
                st.error("Please enter at least one available ingredient")
            else:
                # For testing, you can use a sample response instead of making an actual API call
                # Uncomment the real API call when ready
                """
                response = requests.get(
                    api_endpoint,
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                """
                
                # For testing - using the sample response
                # Convert the provided response to a proper response object with the json method
                class MockResponse:
                    def __init__(self, json_data, status_code):
                        self.json_data = json_data
                        self.status_code = status_code
                        self.text = json.dumps(json_data)
                    
                    def json(self):
                        return self.json_data
                
                # Parse the provided sample response
                sample_json = json.loads('''
                {
                  "statusCode": 200,
                  "body": "{\\\"recipes\\\": [{\\\"id\\\": \\\"114\\\", \\\"score\\\": 0.363749355, \\\"metadata\\\": {\\\"amounts\\\": \\\"['boneless skinless chicken breast halves', 'ham slices', 'swiss cheese', 'all-purpose flour', 'parmesan cheese', 'salt', 'dried sage', 'pepper', 'dry white wine', 'cornstarch', 'water', 'rice']\\\", \\\"cook_time\\\": \\\"6.0\\\", \\\"description\\\": \\\"Make and share this Chicken Breasts Saltimbocca recipe from Food.com.\\\", \\\"ingredients\\\": \\\"['6', '6', '6', '1/4', '1/4', '1', '1/2', '1/4', '1/3', '1', '1/2', '1/4', '1/4']\\\", \\\"instructions\\\": \\\"['Pound chicken breast halves until thin between  two sheets of waxed paper or  foil.', 'Place a slice of ham and cheese on each chicken piece.  Roll up and tuck  ends in; secure with small skewers or  wooden picks.', 'Combine flour, Parmesan  cheese, salt, sage and pepper in a shallow bowl.', 'Coat chicken rolls in flour  mixture.  Refrigerate chicken at least 1 hour.', 'In a large skillet, heat oil  over medium heat.  Add chicken rolls and cook, turning, until browned on all  sides.', 'Place browned chicken in a slow cooker.', 'Combine soup and wine and pour  over chicken rolls.', 'Cover and cook on LOW 4 to 5 hours or until chicken is  tender.', 'Turn control to HIGH.', 'In a small bowl, dissolve cornstarch in water;  stir into cooking juices in cooker.', 'Cover and cook on HIGH 10 minutes.', 'Serve  with hot rice.']\\\", \\\"prep_time\\\": \\\"1.0\\\", \\\"recipe_id\\\": \\\"114\\\", \\\"recipe_name\\\": \\\"Chicken Breasts Saltimbocca\\\", \\\"units\\\": \\\"6.0\\\"}}, {\\\"id\\\": \\\"1141\\\", \\\"score\\\": 0.362307489, \\\"metadata\\\": {\\\"amounts\\\": \\\"['broth', 'butter', 'onions', 'garlic', 'squash', 'sage', 'white wine', 'red wine', 'marsala', 'arborio rice', 'pepper', 'parmesan cheese']\\\", \\\"cook_time\\\": \\\"0.8333333333333334\\\", \\\"description\\\": \\\"Make and share this Squash & Golden Onion Risotto recipe from Food.com.\\\", \\\"ingredients\\\": \\\"['5', '1/4', '3', '2 -4', '2 -3', '1', '3/4', '1/4', '1', '1 1/2']\\\", \\\"instructions\\\": \\\"['Heat broth in one saucepan.', 'Melt 1/4 cup butter in a large saucepan.', 'When butter foams, add onion and garlic.  Saute over med. heat until pale yellow.', 'Add squash and sage; cook until starting to become tender.', 'Add wines and reduce.', 'Add balsamic vinegar and lower heat.', 'And rice, mix well.', 'When rice is coated, stir in 1-2 ladles of broth, cook until absorbed.', 'Continue this routine for 15-20 min.', 'Season with pepper.  Serve with Parmesan.']\\\", \\\"prep_time\\\": \\\"0.6666666666666666\\\", \\\"recipe_id\\\": \\\"1141\\\", \\\"recipe_name\\\": \\\"Squash & Golden Onion Risotto\\\", \\\"units\\\": \\\"6.0\\\"}}, {\\\"id\\\": \\\"364\\\", \\\"score\\\": 0.360193819, \\\"metadata\\\": {\\\"amounts\\\": \\\"['olive oil', 'onion', 'garlic', 'zucchini', 'salt', 'pepper', 'fresh basil', 'flat-leaf Italian parsley', 'fat-free parmesan cheese']\\\", \\\"cook_time\\\": \\\"0.25\\\", \\\"description\\\": \\\"Make and share this Zucchini Frittatas II recipe from Food.com.\\\", \\\"ingredients\\\": \\\"['1', '1', '2', '2', '1/2', '4', '2', '2', '2']\\\", \\\"instructions\\\": \\\"['Heat 1/2 Tbsp. oil in a 10-inch, heavy-bottomed, oven-proof skillet. Add onion  and saute until tender and translucent. Stir in garlic and zucchini and continue sauteing until squash is just tender.', 'Season with salt and pepper and remove  from heat. In a mixing bowl, whisk together eggs, basil and parsley.', 'Stir in  sauteed vegetables.', 'Add remaining 1/2 tablespoon oil to same skillet over medium heat, tilting pan to coat bottom and sides.', 'Add egg-vegetable mixture, spreading evenly.', 'Reduce heat to low and cover pan.', 'Cook 10 to 15 minutes, until set.  Preheat broiler.', 'Sprinkle grated cheese on top of frittata if desired and broil  briefly until lightly browned.', 'Cut into 3 wedges.', 'Serve immediately from the pan or transfer to a large round plate or platter.']\\\", \\\"prep_time\\\": \\\"0.8333333333333334\\\", \\\"recipe_id\\\": \\\"364\\\", \\\"recipe_name\\\": \\\"Zucchini Frittatas II\\\", \\\"units\\\": \\\"3.0\\\"}}, {\\\"id\\\": \\\"405\\\", \\\"score\\\": 0.358385861, \\\"metadata\\\": {\\\"amounts\\\": \\\"['onion', 'green pepper', 'garlic clove', 'chicken breasts', 'salt', 'pepper', 'dried oregano', 'parmesan cheese', 'swiss cheese', 'fresh parsley', 'egg', 'water']\\\", \\\"cook_time\\\": \\\"1.4166666666666667\\\", \\\"description\\\": \\\"Make and share this Whole Wheat Calzone recipe from Food.com.\\\", \\\"ingredients\\\": \\\"['2', '1/4', '1/2', '1/2', '1', '4', '1/4', '1', '1/2', '1/2', '1', '1/4', '1', '1', '1']\\\", \\\"instructions\\\": \\\"['In medium skillet, heat 2 tablespoons oil; saute onion, green and red peppers, and garlic for 3 minutes, stirring constantly.', 'Add  chicken, salt, pepper and oregano; stir occasionally until meat  is browned, about 10 minutes.', 'Drain off excess fat. Remove  skillet from heat.', 'Stir in Parmesan cheese, Swiss cheese, parsley and beaten egg; mix  well and set aside.', 'Make bread mix according to directions.', 'Divide in 4 parts and roll each into a 9-inch circle.', 'Place 1/4 of meat mixture on each.', 'Moisten edges with water; fold to enclose filling, and press edges to seal.', 'On a lightly greased baking sheet, cover and let rise for 15 minutes.', 'Brush tops with egg yolk and water.', 'Bake at 350 degrees Fahrenheit for 20 to 30 minutes or until golden brown and sound hollow when tapped.']\\\", \\\"prep_time\\\": \\\"0.3333333333333333\\\", \\\"recipe_id\\\": \\\"405\\\", \\\"recipe_name\\\": \\\"Whole Wheat Calzone\\\", \\\"units\\\": \\\"4.0\\\"}}, {\\\"id\\\": \\\"715\\\", \\\"score\\\": 0.35396716, \\\"metadata\\\": {\\\"amounts\\\": \\\"['chicken piece', 'chili powder', 'ginger', 'salt', 'garam masala', 'soy sauce', 'plain yogurt', 'curry leaf', 'ginger', 'garlic', 'green chili', 'spring onion', 'coriander leaves']\\\", \\\"cook_time\\\": \\\"nan\\\", \\\"description\\\": \\\"Make and share this Unusual Chicken recipe from Food.com.\\\", \\\"ingredients\\\": \\\"[]\\\", \\\"instructions\\\": \\\"['Mix together and marinate chicken for about 5 to 6 hours or overnight in a covered dish in the refrigerator.', 'Add one beaten egg and corn flour to cover. Place some ground nut oil in a wok heat oil and deep fry on a low heat. The meat is now ready to eat.', 'If a hotter dish is required: Take some curry leaves, ginger, garlic, green chilies, spring onions, coriander leaves. Place all the above in a wok with hot oil and fry for a couple of minutes.', 'Add some yogurt and tomato sauce and stir. Now add the chicken and some red food coloring and stir fry again to cover all the meat with the sauce.']\\\", \\\"prep_time\\\": \\\"0.0\\\", \\\"recipe_id\\\": \\\"715\\\", \\\"recipe_name\\\": \\\"Unusual Chicken\\\", \\\"units\\\": \\\"1.0\\\"}}]}",
                  "headers": {
                    "Content-Type": "application/json"
                  }
                }
                ''')
                
                # Get the recipes from the body
                body_json = json.loads(sample_json["body"])
                recipes = body_json.get("recipes", [])
                
                response = MockResponse({"recipes": recipes}, 200)
                
                print(response)  # Debugging line to check response
                
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