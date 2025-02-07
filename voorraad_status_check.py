import pandas as pd
import streamlit as st
import io

# Functie om data in te laden
def load_data(file):
    return pd.read_excel(file)

# Functie om producten te filteren op basis van voorraad drempelwaardes
def filter_products(stock_df, website_df, threshold_dict):
    merged_df = pd.merge(website_df, stock_df, left_on='Nummer', right_on='Nr.', how='left')
    merged_df['Beschikbare voorraad'] = merged_df['Beschikbare voorraad'].fillna(0)  # Voorkom NaN waarden

    to_remove = []
    for index, row in merged_df.iterrows():
        if 'Ras omschrijving' in row and 'Nr.' in row:  # Controleer of de kolommen bestaan
            ras = row['Ras omschrijving']
            for land in ['Nederland', 'Duitsland', 'België (NL)', 'België (FR)', 'Frankrijk']:
                drempel = threshold_dict.get((ras, land), 0)  # Drempel instelbaar
                if row['Beschikbare voorraad'] < drempel and row.get(land, 'Nee') == 'Ja':
                    to_remove.append(row)
    
    return pd.DataFrame(to_remove) if to_remove else pd.DataFrame(columns=['Nr.', 'Omschrijving', 'Beschikbare voorraad', 'Ras omschrijving'])

# Functie om producten te filteren die wel op voorraad zijn maar niet op de webshop
def filter_missing_products(stock_df, website_df):
    merged_df = pd.merge(website_df, stock_df, left_on='Nummer', right_on='Nr.', how='right', indicator=True)
    missing_products = merged_df[merged_df['_merge'] == 'right_only']
    return missing_products[['Nr.', 'Omschrijving', 'Beschikbare voorraad', 'Ras omschrijving']]

# Streamlit UI
st.title("Voorraad en Website Status Beheer")

uploaded_stock = st.file_uploader("Upload Voorraad Rapport", type=["xlsx"])
uploaded_website = st.file_uploader("Upload Website Status Rapport", type=["xlsx"])

# Mogelijkheid om voorraad drempelwaardes in te stellen
st.sidebar.header("Voorraad Drempels Per Ras & Land")
threshold_dict = {}
ras_options = ['Belgisch Witblauw', 'Holstein zwartbont']  # Uitbreiden met daadwerkelijke rassen
land_options = ['Nederland', 'Duitsland', 'België (NL)', 'België (FR)', 'Frankrijk']

for ras in ras_options:
    for land in land_options:
        key = (ras, land)
        threshold_dict[key] = st.sidebar.number_input(f"Drempel voor {ras} in {land}", min_value=0, value=10)

if uploaded_stock and uploaded_website:
    stock_df = load_data(uploaded_stock)
    website_df = load_data(uploaded_website)
    
    removal_list = filter_products(stock_df, website_df, threshold_dict)

    # Zorg ervoor dat removal_list altijd een DataFrame is
    if removal_list is None or not isinstance(removal_list, pd.DataFrame):
        removal_list = pd.DataFrame(columns=['Nr.', 'Omschrijving', 'Beschikbare voorraad', 'Ras omschrijving'])
    
    st.subheader("Producten die van de webshop gehaald moeten worden:")
    st.dataframe(removal_list)
    
    # Downloadoptie voor het resultaat
    if not removal_list.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            removal_list.to_excel(writer, index=False)
        output.seek(0)
        st.download_button(
            label="Download Lijst",
            data=output.getvalue(),
            file_name="products_to_remove.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Geen producten gevonden om te downloaden.")
    
    # Extra filter: Producten die op voorraad zijn maar niet op de website staan
    missing_products = filter_missing_products(stock_df, website_df)
    st.subheader("Producten die wel op voorraad zijn, maar niet op de webshop staan:")
    st.dataframe(missing_products)
    
    if not missing_products.empty:
        output_missing = io.BytesIO()
        with pd.ExcelWriter(output_missing, engine='openpyxl') as writer:
            missing_products.to_excel(writer, index=False)
        output_missing.seek(0)
        st.download_button(
            label="Download Lijst",
            data=output_missing.getvalue(),
            file_name="products_to_add.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
