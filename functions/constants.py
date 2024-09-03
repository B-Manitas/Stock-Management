"""
This module contains constants used in the application.
"""

# The database schema
DB_SCHEMA = {
    "code": (object, "chaîne de caractères"),
    "designation": (object, "chaîne de caractères"),
    "dlc": ("datetime64[ns]", "date"),
    "quantite": (int, "entier"),
}

# Format for the date
DATE_FORMAT = "DD/MM/YYYY"

# Format for the date in pandas
DATE_FORMAT_PD = "%d/%m/%Y"
