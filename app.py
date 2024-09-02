"""
This script creates a stock management application using Streamlit and MongoDB.
"""

# Import the libraries
import pandas as pd
import pymongo
import streamlit as st

from io import StringIO
from typing import Tuple, Union

# ==================================================
# Define the constants

DB_COLS = {
    "code": (object, "chaîne de caractères"),
    "designation": (object, "chaîne de caractères"),
    "dlc": ("datetime64[ns]", "date"),
    "quantite": (int, "entier"),
}

# ==================================================
# Define the functions


@st.cache_resource
def connect_mongo() -> Tuple[pymongo.MongoClient, pymongo.database.Database, pymongo.collection.Collection, str]:
    """
    Connect to the MongoDB database.

    Parameters
    ----------
    config_path : str
        The path to the configuration file. Default is 'config.ini'.

    Returns
    -------
    Tuple[pymongo.MongoClient, pymongo.database.Database, pymongo.collection.Collection, str]
        A tuple containing the MongoDB client, database, collection, and an error message if
        an error occurred.
    """
    try:
        # Connect to the MongoDB database
        config = st.secrets["mongo"]
        client = pymongo.MongoClient(config["host"])
        db = client[config["database"]]
        collection = db[config["collection_dev"]]

        return client, db, collection, ""

    except Exception:
        return None, None, None, "Erreur: Impossible de se connecter à la base de données."


def init_state():
    """
    Initialize the session state variables.
    """
    if "db_products" not in st.session_state:
        st.session_state["db_products"] = pd.DataFrame(columns=DB_COLS.keys())

    if "toggle_edit" not in st.session_state:
        st.session_state["toggle_edit"] = False


def is_valid_data(df_data: pd.DataFrame) -> str:
    """
    Check if the data is valid.

    The data must meet the following criteria:
        - The data must have the following columns: code, designation, dlc, quantite.
        - The data types must match the expected types.
        - The quantities must be positive.
        - The article codes must be unique.
        - The data must not contain missing values.

    Parameters
    ----------
    df_data : pd.DataFrame
        The data to check.

    Returns
    -------
    str
        An error message if the data is not valid.
    """
    # Check for valid columns
    if set(df_data.columns) != set(DB_COLS.keys()):
        return """Erreur: Les colonnes ne sont pas valides.
        Veuillez vérifier les colonnes suivantes: code, designation, dlc, quantite."""

    # Check for valid data types
    for k, (t, s) in DB_COLS.items():
        if df_data[k].dtype != t:
            return f"Erreur: La colonne {k} doit être de type {s}."

    # Check for positive quantities
    if not (df_data["quantite"] >= 0).all():
        return "Erreur: La colonne 'quantite' doit être supérieure ou égale à zéro."

    # Check for unique article codes
    if not df_data["code"].is_unique:
        return "Erreur: Les codes d'articles doivent être uniques."

    # Check for missing values
    if df_data.isnull().values.any():
        return "Erreur: Les données ne doivent pas contenir de valeurs manquantes."

    return ""


def typecast_data(df_data: pd.DataFrame) -> pd.DataFrame:
    """
    Typecast the data to the expected types.

    Parameters
    ----------
    df_data : pd.DataFrame
        The data to typecast.

    Returns
    -------
    pd.DataFrame
        The typecasted data.
    """
    for k, (t, _) in DB_COLS.items():
        df_data[k] = df_data[k].astype(t)

    return df_data


def search_product(
    _collection: pymongo.collection.Collection,
    item_code: str,
    item_name: str,
    dlc: pd.Timestamp,
) -> pd.DataFrame:
    """
    Search for products in the database based on the specified criteria.

    Parameters
    ----------
    collection : pymongo.collection.Collection
        The collection to search in.

    item_code : str, optional
        The code of the article to search for.

    item_name : str, optional
        The designation of the article to search for.

    dlc : pd.Timestamp, optional
        The expiration date to search for.

    Returns
    -------
    pd.DataFrame
        The filtered database containing the products that match the search criteria
    """
    # Create the filter dictionary
    filter_dict = {
        "code": {"$regex": item_code, "$options": "i"},
        "designation": {"$regex": item_name, "$options": "i"},
        "dlc": {
            "$gte": pd.to_datetime(dlc),
            "$lte": get_month_end(dlc),
        },
    }

    # Perform the search query
    projection = {"_id": 0, "code": 1, "designation": 1, "dlc": 1, "quantite": 1}
    documents = _collection.find(filter_dict, projection)
    filtered_db = pd.DataFrame(list(documents), dtype=str)

    # Convert 'dlc' column to datetime
    if not filtered_db.empty:
        filtered_db["dlc"] = pd.to_datetime(filtered_db["dlc"])
        filtered_db["quantite"] = filtered_db["quantite"].astype(int)

        # Sort the filtered database based on the 'dlc' column
        filtered_db = filtered_db.sort_values("dlc")

    else:
        filtered_db = pd.DataFrame(columns=DB_COLS.keys())

    return filtered_db


def get_month_start(dlc: Union[None, pd.Timestamp] = None) -> pd.Timestamp:
    """
    Get the first day of the current month.

    Parameters
    ----------
    dlc : pd.Timestamp
        The date to get the first day of the month for. Default is the current date

    Returns
    -------
    pd.Timestamp
        The first day of the current month.
    """
    if dlc is None:
        dlc = pd.Timestamp.today()

    return dlc.replace(day=1)


def get_month_end(dlc: Union[None, pd.Timestamp] = None) -> pd.Timestamp:
    """
    Get the last day of the current month.

    Parameters
    ----------
    dlc : pd.Timestamp
        The date to get the last day of the month for. Default is the current date

    Returns
    -------
    pd.Timestamp
        The last day of the current month.
    """
    if dlc is None:
        dlc = pd.Timestamp.today()

    return dlc + pd.offsets.MonthEnd(1)


def update_db(
    collection: pymongo.collection.Collection,
    modified_rows: pd.DataFrame,
    deleted_rows: pd.DataFrame,
) -> str:
    """
    Update the database with the new data.

    Parameters
    ----------
    collection : pymongo.collection.Collection
        The collection to update.

    new_data : pd.DataFrame
        The new data to update the database with.

    filename : str
        The name of the file to save the updated database to.

    Returns
    -------
    Tuple[pd.DataFrame, str]
        A tuple containing the updated database and an error message if an error occurred.
    """
    try:
        # Check if the data is valid
        error_message = is_valid_data(modified_rows)
        if error_message:
            return error_message

        # Convert the modified data to a dictionary
        modified_dict = modified_rows.to_dict(orient="records")

        # Update the database with the modified data
        for row in modified_dict:
            collection.update_one({"code": row["code"]}, {"$set": row})

        # Delete the rows that were removed
        for code in deleted_rows["code"]:
            collection.delete_one({"code": code})

        return ""

    except Exception:
        return "Erreur: Impossible de mettre à jour la base de données."


def add_articles(collection: pymongo.collection.Collection, articles: str) -> Tuple[pd.DataFrame, str]:
    """
    Add new articles to the database.

    Parameters
    ----------
    collection : pymongo.collection.Collection
        The collection to add the new articles to.

    new_articles : str
        The text containing the new articles to add.

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame, str]
        A tuple containing the new data and an error message if an error occurred.
    """
    if not articles.strip():
        return None, "Veuillez saisir au moins un article à ajouter."

    try:
        # Convert the text to a DataFrame
        new_articles = pd.read_csv(StringIO(articles), header=None, names=DB_COLS, dtype=str)
        new_articles = typecast_data(new_articles)

        # Check if the data is valid
        error_message = is_valid_data(new_articles)
        if error_message:
            raise Exception(error_message)

        # Insert the new data into the database
        collection.insert_many(new_articles.to_dict(orient="records"))

        return new_articles, ""

    except Exception:
        error_message = """
        Les données saisies ne sont pas valides. Veuillez vérifier les points suivants:

        - Les données doivent être séparées par des virgules et inclure les colonnes suivantes:
        code, designation, dlc, quantite.\n

        - Les dates doivent être valides et au format 'YYYY-MM-DD'.\n

        - Les quantités doivent être des entiers positifs.\n

        - Les codes d'articles doivent être uniques.\n

        - Les données ne doivent pas contenir de valeurs manquantes.\n

        - Exemple:
            - 001,Article 1,2022-12-31,10
            - 002,Article 2,2023-01-15,20
            - 003,Article 3,2023-02-28,30

        """
        return None, error_message


def on_change_toggle_edit():
    """
    On change event for the toggle edit checkbox. Inverts the value of the toggle edit checkbox.
    """
    st.session_state["toggle_edit"] = not st.session_state["toggle_edit"]


# ==================================================


if __name__ == "__main__":
    # Set up the application parameters
    init_state()
    st.set_page_config(layout="wide", page_title="Stock Management", page_icon="📦")
    st.title("Gestion de stock")

    # Load the database
    client, db, collection, error_message = connect_mongo()

    if error_message:
        st.error(error_message)
        st.stop()

    # Define the tabs for the application
    tabs_list = ["Rechercher des articles", "Ajouter des articles"]
    tab_search, tab_add = st.tabs(tabs_list)

    # Manage the tab for searching articles in the database and editing them
    with tab_search:
        # Create columns for filter input
        column_code, column_name, column_date = st.columns(3)

        # Input fields for filtering articles
        filter_code = column_code.text_input("Code d'article", placeholder="001")
        filter_name = column_name.text_input("Designation", placeholder="Article")
        filter_date = column_date.date_input(
            "Date limite de consommation", value=get_month_start().date(), format="YYYY-MM-DD"
        )

        # Create columns for action inputs
        column_edit, _, column_search = st.columns(3)

        # Button to search for articles
        st.session_state["db_products"] = search_product(collection, filter_code, filter_name, filter_date)

        # Toggle to allow editing of the table
        toggle_edit = column_edit.checkbox(
            "Autoriser la modification de la table",
            value=st.session_state["toggle_edit"],
            on_change=on_change_toggle_edit,
        )

        st.divider()

        # Display the number of results found
        column_number, _, _ = st.columns(3)
        column_number.write(f"Nombre d'articles trouvés: {len(st.session_state['db_products'])}")

        # Display the filtered results
        db_edited = st.data_editor(
            st.session_state["db_products"],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic" if toggle_edit else "fixed",
            disabled={"code": True},
        )

        # Button to save changes if any modifications are made
        if st.button("Sauvegarder les modifications", disabled=not toggle_edit):
            db_filtered = st.session_state["db_products"]

            # Get the deleted rows
            deleted_rows = db_filtered[~db_filtered["code"].isin(db_edited["code"])]

            # Get the modified rows
            common_ids = db_filtered["code"].isin(db_edited["code"])
            A_common = db_filtered[common_ids].set_index("code")
            B_common = db_edited.set_index("code")
            modified_rows = B_common[~B_common.eq(A_common).all(axis=1)].reset_index()

            # Update the database with the modified data
            error_message = update_db(collection, modified_rows, deleted_rows)

            # Display feedback to the user
            if error_message:
                st.error(error_message)

            else:
                st.session_state.toggle_edit = False
                st.rerun()

    # Manage the tab for adding new articles to the database
    with tab_add:
        # Text area for entering articles
        text = st.text_area(
            "Saissisez les informations des articles à ajouter",
            placeholder="code,designation,dlc,quantite",
            height=200,
        )

        if st.button("Enregistrer les articles"):
            # Call the function to add articles
            new_data, error_message = add_articles(collection, text)

            # Display feedback to the user
            if error_message:
                st.error(error_message)

            else:
                st.success("Articles ajoutés avec succès.")
                st.table(new_data)
