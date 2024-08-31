import streamlit as st
import pandas as pd

from io import StringIO

COLS = ['code_article', 'designation', 'dlc', 'quantite']

if __name__ == '__main__':
    dtypes = {'code_article': str, 'designation': str, 'quantite': int}
    db = pd.read_csv('db.csv', dtype=dtypes)
    db['dlc'] = pd.to_datetime(db['dlc'])

    st.set_page_config(layout="wide", page_title="Gestion de stock", page_icon="📦")
    st.title('Gestion de stock')
    
    tabs_list = ['Rechercher des articles', 'Ajouter des articles']
    tab1, tab2 = st.tabs(tabs_list)

    with tab1:
        col1, col2, col_month, col_year, col5 = st.columns(5)
        result = db.copy()

        # Filtre sur le code article
        article_code = col1.text_input('Code article', key='tab1ca', placeholder='001').lower()
        if article_code:
            result = result[result['code_article'].str.lower().str.contains(article_code)]

        # Filtre sur la designation
        article_desc = col2.text_input('Designation', key='tab1de', placeholder='...').lower()
        if article_desc:
            result = result[result['designation'].str.lower().str.contains(article_desc)]

        # Filtre sur le mois de la date limite de consommation
        date_today = pd.Timestamp.now()
        month = col_month.number_input('DLC Mois', value=date_today.month, min_value=1, max_value=12)
        result = result[result['dlc'].dt.month == month]

        # Filtre sur l'année de la date limite de consommation
        year = col_year.number_input('DLC Année', value=date_today.year, min_value=2021, max_value=2025)
        result = result[result['dlc'].dt.year == year]

        # Filtre le nombre de résultats
        n = col5.number_input('Nombre de résultats à afficher', value=10, min_value=1, max_value=100)
        result = result.head(n)


        edited_result = st.data_editor(result, use_container_width=True, key='data_editor', disabled={'code_article': True}, hide_index=True)
        save = st.button('Sauvegarder les modifications', disabled=edited_result.equals(result))

        if not edited_result.equals(result):
            db.update(edited_result)
            db.to_csv('db.csv', index=False)

    with tab2:
        # Zone de texte pour saisir les articles
        text = st.text_area('Ajouter des articles', placeholder='code_article, designation, dlc, quantite')

        if st.button('Ajouter'):
            # Vérifier si le texte n'est pas vide
            if text.strip():
                # Utiliser StringIO pour lire la chaîne de texte comme un CSV
                try:
                    new_data = pd.read_csv(StringIO(text), header=None, names=COLS, dtype=str)
                    new_data['dlc'] = pd.to_datetime(new_data['dlc'])

                    # Ajouter les nouvelles données au DataFrame existant
                    db = pd.concat([db, new_data], ignore_index=True)
                    
                    # Sauvegarder les données dans le CSV
                    db.to_csv('db.csv', index=False)
                    st.success('Les articles ont été ajoutés avec succès !')

                    # Mettre à jour l'affichage du DataFrame
                    st.write("Articles mis à jour dans la base de données :")
                    st.table(new_data)

                except Exception as e:
                    st.error(f"Erreur lors de la lecture du texte: {e}")
            else:
                st.warning("Veuillez entrer au moins un article à ajouter.")
