"""
This script creates a stock management application using Streamlit.
"""

# Import the libraries
import os
import pandas as pd
import streamlit as st

from io import StringIO
from typing import Tuple

# ==================================================
# Define the constants


DB_FILENAME = "db.csv"
DB_COLS = ["code_article", "designation", "dlc", "quantite"]


# ==================================================
# Define the functions


def check_db(db: pd.DataFrame):
    """
    Check if the database is correctly formatted.

    Parameters
    ----------
    db : pd.DataFrame
        The database to check.

    Returns
    -------
    str
        An error message if the database is not correctly formatted, or an empty string otherwise.
    """
    if set(DB_COLS) != set(db.columns):
        return "Erreur: La base de données ne contient pas les colonnes attendues."

    return ""


def load_db(filename: str) -> Tuple[pd.DataFrame, str]:
    """
    Load the database from the specified file.

    Parameters
    ----------
    filename : str
        The name of the file to load the database from.

    Returns
    -------
    Tuple[pd.DataFrame, str]
        A tuple containing the loaded database and an error message if an error occurred.
    """
    # If the file exists, load the database from it
    if os.path.exists(filename):
        db = pd.read_csv(filename)

    # If the file doesn't exist, create an empty database
    else:
        db = pd.DataFrame(columns=DB_COLS)
        db.to_csv(filename, index=False)

    # Convert the columns to the correct data types
    db = db.astype({"code_article": str, "designation": str, "quantite": int})
    db["dlc"] = pd.to_datetime(db["dlc"])

    return db, check_db(db)


def search_product(db: pd.DataFrame, item_code: str, item_name: str, expiry_date: pd.Timestamp) -> pd.DataFrame:
    """
    Search for products in the database based on the specified criteria.

    Parameters
    ----------
    db : pd.DataFrame
        The database to search in.

    code_article : str
        The code of the article to search for.

    designation : str
        The designation of the article to search for.

    dlc : pd.Timestamp
        The expiration date to search for.

    Returns
    -------
    pd.DataFrame
        The filtered database containing the products that match the search criteria
    """
    filtered_db = db.copy()

    # Filtering based on the 'code_article'
    filter_code = filtered_db["code_article"].str.lower().str.contains(item_code.lower())
    filtered_db = filtered_db[filter_code]

    # Filtering based on the 'designation'
    filter_name = filtered_db["designation"].str.lower().str.contains(item_name.lower())
    filtered_db = filtered_db[filter_name]

    # Filtering based on the 'dlc'
    data_date = filtered_db["dlc"].dt
    filter_dlc_day = data_date.day >= expiry_date.day
    filter_dlc_date = (data_date.month == expiry_date.month) & (data_date.year == expiry_date.year)
    filtered_db = filtered_db[filter_dlc_day & filter_dlc_date]

    # Sort the filtered database based on the 'dlc' column
    filtered_db = filtered_db.sort_values("dlc")

    return filtered_db


def get_month_start() -> pd.Timestamp:
    """
    Get the first day of the current month.

    Returns
    -------
    pd.Timestamp
        The first day of the current month.
    """
    return pd.Timestamp.today().replace(day=1)


def update_db(db: pd.DataFrame, new_data: pd.DataFrame, filename: str) -> Tuple[pd.DataFrame, str]:
    """
    Update the database with the new data.

    Parameters
    ----------
    db : pd.DataFrame
        The current database.

    new_data : pd.DataFrame
        The new data to update the database with.

    filename : str
        The name of the file to save the updated database to.

    Returns
    -------
    Tuple[pd.DataFrame, str]
        A tuple containing the updated database and an error message if an error occurred.
    """
    error_message = check_db(new_data)

    if error_message:
        return db, error_message

    # Update the database with the new data
    else:
        db = db.copy()
        db.update(new_data)
        db.to_csv(filename, index=False)

        return db, error_message


def add_articles(db: str, articles: str, filename: str) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """
    Add new articles to the database.

    Parameters
    ----------
    db : pd.DataFrame
        The current database.

    new_articles : str
        The text containing the new articles to add.

    filename : str
        The name of the file to save the updated database to.

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame, str]
        A tuple containing the updated database, the new data added, and an error message if an
        error occurred.
    """
    if not articles.strip():
        return None, "Veuillez saisir au moins un article à ajouter."

    try:
        # Use StringIO to read the text as if it were a CSV file
        new_data = pd.read_csv(StringIO(articles), header=None, names=DB_COLS, dtype=str)
        new_data["dlc"] = pd.to_datetime(new_data["dlc"])

        # Append the new data to the existing DataFrame
        db = pd.concat([db, new_data], ignore_index=True)

        # Save the updated DataFrame to the CSV file
        db.to_csv(filename, index=False)
        return db, new_data, None

    except Exception:
        error_message = """
        Les données saisies ne sont pas valides. Veuillez vérifier les points suivants:

        - Les données doivent être séparées par des virgules et inclure les colonnes suivantes:
        code_article, designation, dlc, quantite.\n

        - Les dates doivent être au format 'YYYY-MM-DD'.

        - Exemple:
            - 001,Article 1,2022-12-31,10
            - 002,Article 2,2023-01-15,20
            - 003,Article 3,2023-02-28,30

        """
        return None, None, error_message


# ==================================================


if __name__ == "__main__":
    # Load the database from the specified file
    db, error_message = load_db(DB_FILENAME)

    if error_message:
        st.error(error_message)
        st.stop()

    # Set up the application parameters
    st.set_page_config(layout="wide", page_title="Stock Management", page_icon="📦")
    st.title("Gestion de stock")

    # Define the tabs for the application
    tabs_list = ["Rechercher des articles", "Ajouter des articles"]
    tab_search, tab_add = st.tabs(tabs_list)

    # Manage the tab for searching articles in the database and editing them
    with tab_search:
        # Create columns for filter input
        column_code, column_name, column_date = st.columns(3)

        # Input fields for filtering articles
        filter_code = column_code.text_input("Code d'article", placeholder="001")
        filter_name = column_name.text_input("Designation", placeholder="...")
        filter_date = column_date.date_input(
            "Date limite de consommation", value=get_month_start(), format="YYYY-MM-DD"
        )

        # Filter the database based on input criteria
        db_filtered = search_product(db, filter_code, filter_name, filter_date)

        # Toggle to allow editing of the table
        _, _, column_edit = st.columns(3)

        st.divider()

        # Display the number of results found
        column_number, _, _ = st.columns(3)
        column_number.write(f"Nombre d'articles trouvés: {len(db_filtered)}")

        # Checkbox to allow editing of the table
        toggle_edit = column_edit.checkbox("Autoriser la modification de la table", value=False)

        # Display the filtered results
        db_edited = st.data_editor(
            db_filtered,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic" if toggle_edit else "fixed",
            disabled={"code_article": True},
        )

        # Button to save changes if any modifications are made
        if st.button("Sauvegarder les modifications", disabled=not toggle_edit):
            db, error_message = update_db(db, db_edited, DB_FILENAME)

            # Display feedback to the user
            if error_message:
                st.error(error_message)

            else:
                st.success("Modifications enregistrées avec succès.")

    # Manage the tab for adding new articles to the database
    with tab_add:
        # Text area for entering articles
        text = st.text_area(
            "Saissisez les informations des articles à ajouter",
            placeholder="code_article,designation,dlc,quantite",
            height=200,
        )

        if st.button("Enregistrer les articles"):
            # Call the function to add articles
            db, new_data, error_message = add_articles(db, text, DB_FILENAME)

            # Display feedback to the user
            if error_message:
                st.error(error_message)

            else:
                st.success("Articles ajoutés avec succès.")
                st.table(new_data)
