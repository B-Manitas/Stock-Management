"""
This module contains functions to interact with a MongoDB database.
"""

# Import libraries
import pandas as pd
import pymongo
import streamlit as st

from io import StringIO

from functions.utils import get_month_end, is_valid_data, is_valid_date, typecast_data
from functions.constants import DB_SCHEMA, DATE_FORMAT, DATE_FORMAT_PD


@st.cache_resource
def connect_db(
    host: str, database_name: str, collection_name: str
) -> tuple[pymongo.MongoClient, pymongo.database.Database, pymongo.collection.Collection, str]:
    """
    Connect to the MongoDB database.

    Parameters
    ----------
    host : str
        The hostname of the MongoDB server.

    database : str
        The name of the database to connect to.

    collection : str
        The name of the collection to connect to.

    Returns
    -------
    Tuple[pymongo.MongoClient, pymongo.database.Database, pymongo.collection.Collection, str]
        A tuple containing the MongoDB client, database, collection, and an error message if
        an error occurred.
    """
    try:
        client = pymongo.MongoClient(host)
        db = client[database_name]
        collection = db[collection_name]

        return client, db, collection, ""

    except Exception:
        return None, None, None, "Erreur: Impossible de se connecter à la base de données."


def search_products(
    collection: pymongo.collection.Collection,
    filter_code: str,
    filter_name: str,
    filter_dlc: str,
) -> pd.DataFrame:
    """
    Search for products in the database based on the specified criteria.

    Parameters
    ----------
    collection : pymongo.collection.Collection
        The collection to search in.

    filter_code : str
        The code of the article to search for.

    filter_name : str
        The designation of the article to search for.

    filter_dlc : str
        The expiration date to search for. Keep only the articles that expire in the same month.

    Returns
    -------
    pd.DataFrame
        The filtered database containing the products that match the search criteria
    """
    # Create the filter dictionary
    filter_dict = {
        "code": {"$regex": filter_code, "$options": "i"},
        "designation": {"$regex": filter_name, "$options": "i"},
    }

    # Add the expiration date filter if specified
    if filter_dlc and is_valid_date(filter_dlc):
        filter_dlc = pd.to_datetime(filter_dlc, format=DATE_FORMAT_PD)

        filter_dict["dlc"] = {
            "$gte": filter_dlc,
            "$lte": get_month_end(filter_dlc),
        }

    # Perform the search query
    projection = {"_id": 0, "code": 1, "designation": 1, "dlc": 1, "quantite": 1}
    documents = collection.find(filter_dict, projection)
    filtered_db = pd.DataFrame(list(documents), dtype=str)

    # Convert 'dlc' column to datetime
    if not filtered_db.empty:
        filtered_db["dlc"] = pd.to_datetime(filtered_db["dlc"])
        filtered_db["quantite"] = filtered_db["quantite"].astype(int)

        # Sort the filtered database based on the 'dlc' column
        filtered_db = filtered_db.sort_values("dlc")

    else:
        filtered_db = pd.DataFrame(columns=DB_SCHEMA.keys())

    return filtered_db


def add_products(
    collection: pymongo.collection.Collection, articles: str
) -> tuple[pd.DataFrame, str]:
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
        new_articles = pd.read_csv(StringIO(articles), header=None, names=DB_SCHEMA, dtype=str)
        new_articles = typecast_data(new_articles)

        # Check if the data is valid
        error_message = is_valid_data(new_articles)
        if error_message:
            raise Exception(error_message)

        # Insert the new data into the database
        collection.insert_many(new_articles.to_dict(orient="records"))

        return new_articles, ""

    except Exception:
        error_message = f"""
        Les données saisies ne sont pas valides. Veuillez vérifier les points suivants:

        - Les données doivent être séparées par des virgules et inclure les colonnes suivantes:
        code, designation, dlc, quantite.\n

        - Les dates doivent être valides et au format '{DATE_FORMAT}'.\n

        - Les quantités doivent être des entiers positifs.\n

        - Les codes d'articles doivent être uniques.\n

        - Les données ne doivent pas contenir de valeurs manquantes.\n

        - Exemple:
            - 001,Article 1,31/12/2022,10
            - 002,Article 2,15/01/2023,20
            - 003,Article 3,26/02/2023,30

        """
        return None, error_message


def update_products(
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
    str
        An error message if an error occurred.
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
