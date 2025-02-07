import pandas as pd
import streamlit as st
import io

# Functie om data in te laden
def load_data(file):
    return pd.read_excel(file)

# Functie om producten te filteren op basis van voorraad drempelwaardes
def filter_products(stock_df, website_df, threshold_dict):
    merged_df = pd.merge(website_df, stock_df, left_on='Levensnummer', right_on='Nr.', how='left')
    
    # Zorg ervoor dat de kolomnaam correct overeenkomt met die in het Excel-bestand
    if 'Beschikbare voorraad' not in merged_df.columns:
        merged_df['Beschikbare voorraad'] = stock_df['Beschikbare voorraad'].fillna(0)  # Kolom uit voorraadbestand
    
    merged_df['Beschikbare voorraad'] = merged_df['Beschikbare voorraad'].fillna(0)  # Voorkom NaN waarden

    to_remove = []
    to_add = []
    for index, row in merged_df.iterrows():
        if 'Ras omschrijving' in row and 'Nr.' in row:  # Controleer of de kolommen bestaan
            ras = row['Ras omschrijving']
            status = row['Status'] if 'Status' in row else 'Onbekend'
            for land in ['Nederland', 'Duitsland', 'België (NL)', 'België (FR)', 'Frankrijk']:
                drempel = threshold_dict.get((ras, land), 0)  # Drempel instelbaar
                
                if row['Beschikbare voorraad'] < drempel and row.get(land, 'Nee') == 'Ja' and status == 'actief':
                    to_remove.append(row)
                elif row['Beschikbare voorraad'] >= drempel and row.get(land, 'Nee') == 'Ja' and status in ['archive', 'concept']:
                    to_add.append(row)
    
    remove_df = pd.DataFrame(to_remove) if to_remove else pd.DataFrame(columns=['Nr.', 'Omschrijving', 'Beschikbare voorraad', 'Ras omschrijving', 'Status'])
    add_df = pd.DataFrame(to_add) if to_add else pd.DataFrame(columns=['Nr.', 'Omschrijving', 'Beschikbare voorraad', 'Ras omschrijving', 'Status'])
    
    return remove_df, add_df

# Streamlit UI
st.title("Voorraad en Website Status Beheer")

uploaded_stock = st.file_uploader("Upload Voorraad Rapport", type=["xlsx"])
uploaded_website = st.file_uploader("Upload Website Status Rapport", type=["xlsx"])

# Mogelijkheid om voorraad drempelwaardes in te stellen
st.sidebar.header("Voorraad Drempels Per Ras & Land")
threshold_dict = {}
land_options = ['Nederland', 'Duitsland', 'België (NL)', 'België (FR)', 'Frankrijk']

if uploaded_stock and uploaded_website:
    stock_df = load_data(uploaded_stock)
    website_df = load_data(uploaded_website)
    
    # Extract unieke rassen uit de bestanden
    stock_rassen = stock_df['Ras omschrijving'].dropna().unique().tolist()
    website_rassen = website_df['Ras omschrijving'].dropna().unique().tolist()
    ras_options = sorted(set(stock_rassen + website_rassen))
    
    for ras in ras_options:
        for land in land_options:
            key = (ras, land)
            threshold_dict[key] = st.sidebar.number_input(f"Drempel voor {ras} in {land}", min_value=0, value=10)

# Knop om opnieuw te berekenen zonder opnieuw bestanden te uploaden
if st.button("Opnieuw berekenen") and uploaded_stock and uploaded_website:
    removal_list, addition_list = filter_products(stock_df, website_df, threshold_dict)

    st.subheader("Producten die van de webshop gehaald moeten worden:")
    st.dataframe(removal_list)
    
    st.subheader("Producten die weer actief gezet moeten worden op de webshop:")
    st.dataframe(addition_list)
    
    # Downloadoptie met twee tabbladen
    if not removal_list.empty or not addition_list.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            removal_list.to_excel(writer, sheet_name="Te verwijderen", index=False)
            addition_list.to_excel(writer, sheet_name="Te activeren", index=False)
        output.seek(0)
        st.download_button(
            label="Download Lijst",
            data=output.getvalue(),
            file_name="voorraad_status_update.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Geen wijzigingen gevonden om te downloaden.")
