"""
This script creates a stock management application using Streamlit and MongoDB.
"""

# Import the libraries
import pandas as pd
import streamlit as st

from functions.mongo_api import add_products, connect_db, search_products, update_products
from functions.utils import get_month_start, send_email
from functions.constants import DB_SCHEMA

# ==================================================
# Define the streamlit functions


def init_state() -> None:
    """
    Initialize the session state variables.
    """
    if "products" not in st.session_state:
        st.session_state["products"] = pd.DataFrame(columns=DB_SCHEMA.keys())

    if "toggle_edit" not in st.session_state:
        st.session_state["toggle_edit"] = False


def on_change_toggle_edit() -> None:
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

    # Input field to select the environment
    _, _, column_env = st.columns(3)
    env = column_env.selectbox("Environnement", ["collection_dev", "collection_prod"])

    # Load the database
    config = st.secrets["mongo"]
    host, db_name, collection_name = config["host"], config["database"], config[env]
    client, db, collection, error_message = connect_db(host, db_name, collection_name)

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
        st.session_state["products"] = search_products(
            collection, filter_code, filter_name, filter_date
        )

        # Toggle to allow editing of the table
        toggle_edit = column_edit.checkbox(
            "Autoriser la modification de la table",
            value=st.session_state["toggle_edit"],
            on_change=on_change_toggle_edit,
        )

        st.divider()

        # Display the number of results found
        column_number, _, _ = st.columns(3)
        column_number.write(f"Nombre d'articles trouvés: {len(st.session_state['products'])}")

        # Display the filtered results
        db_edited = st.data_editor(
            st.session_state["products"],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic" if toggle_edit else "fixed",
            disabled={"code": True},
        )

        # Column to display the bottom action buttons
        column_save, _, column_mail = st.columns(3)

        # Button to save changes if any modifications are made
        if column_save.button(
            "Sauvegarder les modifications", disabled=not toggle_edit, use_container_width=True
        ):
            db_filtered = st.session_state["products"]

            # Get the deleted rows
            deleted_rows = db_filtered[~db_filtered["code"].isin(db_edited["code"])]

            # Get the modified rows
            common_ids = db_filtered["code"].isin(db_edited["code"])
            A_common = db_filtered[common_ids].set_index("code")
            B_common = db_edited.set_index("code")
            modified_rows = B_common[~B_common.eq(A_common).all(axis=1)].reset_index()

            # Update the database with the modified data
            error_message = update_products(collection, modified_rows, deleted_rows)

            # Display feedback to the user
            if error_message:
                st.error(error_message)

            else:
                st.session_state["toggle_edit"] = False
                st.rerun()

        # Button to send the table by email
        if column_mail.button("Envoyer la table par email", use_container_width=True):
            config = st.secrets["mail"]
            sender, receiver, tokens = config["sender"], config["receiver"], config["tokens"]
            products = st.session_state["products"]
            error_message = send_email(products, sender, receiver, tokens)

            # Display feedback to the user
            if error_message:
                st.error(error_message)

            else:
                st.success("Email envoyé avec succès.")

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
            new_data, error_message = add_products(collection, text)

            # Display feedback to the user
            if error_message:
                st.error(error_message)

            else:
                st.success("Articles ajoutés avec succès.")
                st.table(new_data)
