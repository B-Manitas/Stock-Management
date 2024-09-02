"""
This module contains utility functions for the application.
"""

# Import libraries
import pandas as pd

from functions.constants import DB_SCHEMA


def get_month_start(dlc: None | pd.Timestamp = None) -> pd.Timestamp:
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


def get_month_end(dlc: None | pd.Timestamp = None) -> pd.Timestamp:
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
    if set(df_data.columns) != set(DB_SCHEMA.keys()):
        return """Erreur: Les colonnes ne sont pas valides.
        Veuillez vérifier les colonnes suivantes: code, designation, dlc, quantite."""

    # Check for valid data types
    for k, (t, s) in DB_SCHEMA.items():
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
    for k, (t, _) in DB_SCHEMA.items():
        df_data[k] = df_data[k].astype(t)

    return df_data
