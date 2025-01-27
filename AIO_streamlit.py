import streamlit as strl
# BTW there is a customized config.toml in /.streamlit for colour changes
import pandas as pd

# File paths
file_paths = {
    "selection": 'Ingredients_selection_table.csv',
    "quantities": 'Ingredients_qt._table.csv',
    "ingredients": "Ingredients_qt._table.csv",
    "recipes": "Pasta_Exp_recipes.csv",
    "recipes_details": "Recipes.csv",
    "pasta_base_grouped": "Pasta_base_grouped.csv"
}

# Load ingredient list
ingredients_list = pd.read_csv(file_paths["selection"])

# Some basic functions
def clean_ing_name(ingredient):
    return ingredient.split(' [')[0].strip() if isinstance(ingredient, str) else ingredient

def save_quantities(selected_ingredients, quantities):
    # Update the quantity data
    qt_data = pd.read_csv(file_paths["quantities"])
    for ingredient, quantity in quantities.items():
        clean_name = clean_ing_name(ingredient)
        for column in qt_data.columns:
            if clean_name in qt_data[column].values:
                # Adjust the quantity by adding the new input, negative means subtract from total
                current_quantity = qt_data.loc[qt_data[column] == clean_name, 'qt'].values[0]
                new_quantity = current_quantity + quantity
                if new_quantity < 0:
                    strl.warning(f"Cannot set a negative total quantity for {ingredient}. Adjusted to 0.")
                    new_quantity = 0  # Prevent negative total quantities and default to 0
                qt_data.loc[qt_data[column] == clean_name, 'qt'] = new_quantity

    # Save the updated data back to the CSV file
    qt_data.to_csv(file_paths["quantities"], index=False)

def load_available_ingredients():
    # Load the updated quantity data from before
    qt_data = pd.read_csv(file_paths["quantities"])
    # Merge to show category and name
    available_ingredients = qt_data.merge(
        ingredients_list.melt(var_name="Category", value_name="Ingredient").dropna(),
        on="Ingredient",
        how="inner"
    )
    # Filter (show only qt.>0 ingredients) and sort
    available_ingredients = available_ingredients[available_ingredients['qt'] > 0]
    available_ingredients = available_ingredients.sort_values(by=["Category", "Ingredient"])
    return available_ingredients

def clean_recipe_ingredients(recipes_exp):
    recipes_exp_copy = recipes_exp.copy()
    recipes_exp_copy.iloc[:, 1:] = recipes_exp.iloc[:, 1:].apply(
        lambda x: x.map(lambda y: y.split(' [')[0].strip().lower() if isinstance(y, str) else None)
    )
    return recipes_exp_copy

def find_dishes_missing_one(available_ingredients, recipes_exp):
    recommendations = []
    for index, row in recipes_exp.iterrows():
        dish_name = row['Dish Name'].strip()
        ingredients = row[1:].dropna().tolist()
        missing_ingredients = [ingredient for ingredient in ingredients if ingredient not in available_ingredients]
        not_missing_ingredients = [ingredient for ingredient in ingredients if ingredient in available_ingredients]
        if len(missing_ingredients) == 1:
            recommendations.append((dish_name, missing_ingredients[0], not_missing_ingredients))
    return recommendations

# Custom CSS for the fridge picture
strl.markdown(
    f"""
    <style>
    .corner-image {{
        position: absolute;
        top: 5%;
        left: -30%;
        transform: translate(-30%, 5%);
        width: 200px;
        height: auto;
        z-index: 1000;
    }}
    </style>
    <img src="https://i.imgur.com/3r9VTW0.png" class="corner-image">
    """,
    unsafe_allow_html=True
)

# Streamlit UI begins here
strl.title("Inventory")

with strl.sidebar:
    # Sidebar: Show currently available ingredients
    strl.header("Available Ingredients")
    
    # Refresh button to see updated quantities
    if strl.button("Refresh"):
        available_ingredients = load_available_ingredients()
    else:
        # Show a message if the sidebar hasn't been refreshed since new "instance" (I gave up trying to make it refresh automatically so this is the compromise)
        strl.info("Click 'Refresh' to reload the available ingredients.")
        # If you have nothing then this is what it shows, nothing.
        available_ingredients = None

    # Display available ingredients grouped by category
    if available_ingredients is not None and not available_ingredients.empty:
        for category, group in available_ingredients.groupby("Category"):
            strl.subheader(category)
            for _, row in group.iterrows():
                ingredient_display = f"{row['Ingredient']}:"
                quantity_display = f"**{row['qt']} {row['unit'] if 'unit' in row else ''}**"
                strl.markdown(f"- {ingredient_display} <span style='color: orange;'>{quantity_display}</span>", unsafe_allow_html=True)
    elif available_ingredients is not None:
        strl.write("No ingredients available.")

# Main content 1: Inventory update
col1, col2 = strl.columns([3, 2])  # Adjust column proportions of main content 1. col1 is select and col2 is input

with col1:
    strl.header("Select Ingredients to Update")
    ingredients_dict = {col: ingredients_list[col].dropna().tolist() for col in ingredients_list.columns}

    # Define dictionary of categories and corresponding emojis
    category_emojis = {
        "Dairy": "\U0001F9C0",              # 🧀
        "Protein": "\U0001F969",            # 🥩
        "Sea Protein": "\U0001F41F",        # 🐟
        "Vegetable": "\U0001F966",          # 🥦
        "Sauce": "\U0001F372",              # 🍲
        "Basic Condiments": "\U0001F9C2",   # 🧂
        "Other": "\U0001F954"               # 🥔
    }

    # Display categories AND emojis
    selected_ingredients = []
    for category, items in ingredients_dict.items():
        emoji = category_emojis.get(category, "")
        with strl.expander(f"{emoji} Category: {category}", expanded=False):
            selected_items = strl.multiselect(f"Select items from {category}:", items, key=f"multiselect_{category}")
            selected_ingredients.extend(selected_items)

with col2:
    strl.header("Input Quantities added(+)/used(-)")
    if selected_ingredients:
        quantities = {}
        for ingredient in selected_ingredients:
            clean_name = clean_ing_name(ingredient)
            unit_row = pd.read_csv(file_paths["quantities"])[pd.read_csv(file_paths["quantities"])['Ingredient'] == clean_name]
            unit = unit_row['unit'].values[0] if not unit_row.empty else None
            unit_display = f" ({unit})" if unit else "" # units for eggs are empty for example, that's why ""
            quantity_input = strl.text_input(f"{ingredient}{unit_display}:", value="0", key=f"quantity_{ingredient}")

            # Validate input and convert to number (float)
            try:
                quantity = float(quantity_input)
                quantities[ingredient] = quantity
            except ValueError:
                strl.error(f"Invalid quantity for {ingredient}. Please enter a valid number.")

        if strl.button("Save Quantities"):
            save_quantities(selected_ingredients, quantities)
            strl.success("Quantities saved. Use the 'Refresh' button (on the sidebar) to see updates.")

# Main content 2: what pastas can I make with what I have
if strl.markdown('<div style="font-size:120px; font-weight:bold;">What pasta/s can I make?</div>', unsafe_allow_html=True) and strl.button("CALCULATE"):
    # This is stuff from my original script

    # Extract available ingredients
    def get_available_ingredients(ingredients_inv):
        return ingredients_inv[ingredients_inv['qt'] > 0]['Ingredient'].str.lower().tolist()

    # Find preparable dishes
    def find_preparable_dishes(available_ingredients, recipes_exp):
        preparable_dishes = []
        for index, row in recipes_exp.iterrows():
            dish_name = row['Dish Name'].strip().lower()
            ingredients = row[1:].dropna().tolist()
            if all(ingredient in available_ingredients for ingredient in ingredients):
                preparable_dishes.append(dish_name)
        return preparable_dishes

    # Get detailed information for preparable dishes
    def get_dish_details(preparable_dishes, recipes_details):
        recipes_details['Dish Name'] = recipes_details['Dish Name'].str.strip().str.lower()
        detailed_dishes = recipes_details[recipes_details['Dish Name'].isin(preparable_dishes)]
        return detailed_dishes

    # Get alternative pasta bases
    def get_alternative_pastas(base, pasta_base_grouped):
        base_cleaned = base.split(' [')[0].strip().lower()
        for column in pasta_base_grouped.columns:
            column_values = pasta_base_grouped[column].dropna().str.strip().str.lower().tolist()
            if base_cleaned in column_values:
                alternatives = [pasta.title() for pasta in column_values if pasta != base_cleaned]
                return alternatives
        return []

    # Load data files
    def load_data():
        ingredients_inv = pd.read_csv(file_paths["ingredients"])
        recipes_exp = pd.read_csv(file_paths["recipes"])
        recipes_details = pd.read_csv(file_paths["recipes_details"])
        pasta_base_grouped = pd.read_csv(file_paths["pasta_base_grouped"])
        return ingredients_inv, recipes_exp, recipes_details, pasta_base_grouped

    ingredients_inv, recipes_exp, recipes_details, pasta_base_grouped = load_data()

    # Find and display preparable dishes with everything
    available_ingredients = get_available_ingredients(ingredients_inv)
    recipes_exp_cleaned = clean_recipe_ingredients(recipes_exp)
    preparable_dishes = find_preparable_dishes(available_ingredients, recipes_exp_cleaned)

    if preparable_dishes:
        strl.header("Preparable Dishes")
        strl.markdown('<p style="color: grey; font-size: 0.9em; font-style: italic;">(check manually if you have enough of each available ingredient)</p>', unsafe_allow_html=True)
        detailed_dishes = get_dish_details(preparable_dishes, recipes_details)

        # Display dishes in a condensed layout (less scrolling)
        num_columns = 3  # Number of columns in the layout
        rows = len(detailed_dishes) // num_columns + (len(detailed_dishes) % num_columns > 0)

        dish_list = detailed_dishes.to_dict(orient="records")

        for row in range(rows):
            cols = strl.columns(num_columns)
            for col_idx, col in enumerate(cols):
                # This WHOLE MESS is ALL FOR IN CASE YOU CANT MAKE ANYTHING. I did NOT figure this out by myself. Thank you GPT.
                dish_index = row * num_columns + col_idx
                # THIS MEANS YOU CAN MAKE AT LEAST 1
                if dish_index < len(dish_list):
                    dish = dish_list[dish_index]
                    with col:
                        strl.subheader(dish['Dish Name'].title())

                        # Google Image Search link for the dish
                        google_search_link = f"https://www.google.com/search?tbm=isch&q={'+'.join(dish['Dish Name'].split())}"
                        strl.markdown(f"[Search for images of {dish['Dish Name'].title()} on Google]({google_search_link})")

                        strl.markdown(f"**Base:** {dish['Base']}")
                        strl.markdown(f"**Cooking Time:** {dish['Cooking Time']}")
                        strl.markdown(f"**Calories per Serving:** {dish['Calories per Serving']}")
                        strl.markdown(f"**Ingredients & Quantity:** {dish['Ingredients & Quantity']}")
                        strl.markdown(f"**Level of Cost:** {dish['Level of Cost']}")
                        strl.markdown(f"**Dosage Size:** {dish['Dosage Size']}")

                        alternatives = get_alternative_pastas(dish['Base'], pasta_base_grouped)
                        if alternatives:
                            strl.markdown(f"**Alternative Pastas:** {', '.join(alternatives)}")
                        else:
                            strl.markdown("**Alternative Pastas:** None")
    else:
        strl.error("No dishes can be prepared with the current ingredients.")

# Main content 3: Find dishes missing only 1 ingredient
if strl.markdown('<div style="font-size:50px; font-weight:bold; color:red">If only you had...</div>', unsafe_allow_html=True) and strl.button("CALCULATE 2"):

    recipes_exp = pd.read_csv(file_paths["recipes"])
    available_ingredients = load_available_ingredients()['Ingredient'].str.lower().tolist()
    recipes_exp_cleaned = clean_recipe_ingredients(recipes_exp)
    missing_one_recommendations = find_dishes_missing_one(available_ingredients, recipes_exp_cleaned)

    if missing_one_recommendations:
        strl.header("Dishes Missing Only 1 Ingredient")
        strl.markdown('<p style="color: grey; font-size: 0.9em; font-style: italic;">(mind you basic condiments such as salt do not count)</p>', unsafe_allow_html=True)

        for dish_name, missing_ingredient, not_missing_ingredients in missing_one_recommendations:
            strl.subheader(dish_name)

            google_search_link = f"https://www.google.com/search?tbm=isch&q={'+'.join(dish_name.split())}"
            strl.markdown(f"[Search for images of {dish_name.title()} on Google]({google_search_link})")

            strl.markdown(f"**Missing Ingredient:** {missing_ingredient.title()}")
            strl.markdown(f"**Available Ingredients:** {', '.join(not_missing_ingredients).title()}")
    else:
        strl.info("No dishes are missing just one ingredient.")
