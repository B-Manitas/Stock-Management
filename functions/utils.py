"""
This module contains utility functions for the application.
"""

# Import libraries
import pandas as pd
import smtplib

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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


def send_email(products: pd.DataFrame, sender: str, receiver: str, tokens: str) -> str:
    """
    Send an email with the list of products that are about to expire.

    Parameters
    ----------
    products : pd.DataFrame
        The products that are about to expire.

    sender : str
        The email address of the sender.

    receiver : str
        The email address of the receiver.

    tokens : str
        The email password.

    Returns
    -------
    str
        If an error occurred, an error message is returned.
    """
    try:
        date = pd.Timestamp.today().strftime("%d/%m/%Y")

        # Create the email message
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = receiver
        msg["Subject"] = f"Produits a expiration prochaine - {date}"

        # Create the email body
        body = f"""
        <p>Bonjour,</p>
        <p>Voici la liste des produits qui vont bientôt expirer:</p>

        {products.to_html(index=False)}

        <p>Cordialement,</p>
        <p>Gestion de stock</p>

        <hr>
        <p>Cette email a été envoyé automatiquement. Merci de ne pas y répondre.</p>
        """

        msg.attach(MIMEText(body, "html"))

        # Create the attachment
        filename = f"products_{date}.csv"
        attachment = MIMEBase("application", "octet-stream")
        attachment.set_payload(products.to_csv(index=False))
        encoders.encode_base64(attachment)
        attachment.add_header("Content-Disposition", f"attachment; filename= {filename}")
        msg.attach(attachment)

        # Send the email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, tokens)
        server.send_message(msg)

        server.quit()

        return ""

    except Exception:
        return "Erreur: Impossible d'envoyer l'email."
