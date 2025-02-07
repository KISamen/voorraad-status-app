import pandas as pd
import streamlit as st

# Functie om data in te laden
def load_data(file):
    return pd.read_excel(file)

# Functie om producten te filteren op basis van voorraad drempelwaardes
def filter_products(stock_df, website_df, threshold_dict):
    merged_df = pd.merge(website_df, stock_df, left_on='Nummer', right_on='Nr.', how='left')
    merged_df['Beschikbare voorraad'] = merged_df['Beschikbare voorraad'].fillna(0)  # Voorkom NaN waarden
    
    to_remove = []
    for index, row in merged_df.iterrows():
        ras = row['Ras omschrijving']
        for land in ['Nederland', 'Duitsland', 'België (NL)', 'België (FR)', 'Frankrijk']:
            drempel = threshold_dict.get((ras, land), 0)  # Drempel instelbaar
            
            if row['Beschikbare voorraad'] < drempel and row[land] == 'Ja':
                to_remove.append(row)
    
    return pd.DataFrame(to_remove)

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
    
    st.subheader("Producten die van de webshop gehaald moeten worden:")
    st.dataframe(removal_list)
    
    # Downloadoptie voor het resultaat
    output = removal_list.to_excel("products_to_remove.xlsx", index=False)
    st.download_button(label="Download Lijst", data=output, file_name="products_to_remove.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    # Extra filter: Producten die op voorraad zijn maar niet op de website staan
    missing_products = filter_missing_products(stock_df, website_df)
    st.subheader("Producten die wel op voorraad zijn, maar niet op de webshop staan:")
    st.dataframe(missing_products)
    
    output_missing = missing_products.to_excel("products_to_add.xlsx", index=False)
    st.download_button(label="Download Lijst", data=output_missing, file_name="products_to_add.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
