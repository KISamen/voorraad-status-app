import pandas as pd
import streamlit as st
import io

# Functie om data in te laden
def load_data(file):
    return pd.read_excel(file)

# Functie om producten te filteren op basis van voorraad drempelwaardes
def filter_products(stock_df, website_df, threshold_dict):
    # Corrigeer de kolomnamen om de juiste match te krijgen
    stock_df = stock_df.rename(columns={'Nr.': 'Stiercode NL / KI code', 'Ras omschrijving': 'Rasomschrijving'})
    
    merged_df = pd.merge(website_df, stock_df, on='Stiercode NL / KI code', how='left')
    
    # Controleer of alle vereiste kolommen aanwezig zijn
    required_columns_stock = {'Stiercode NL / KI code', 'Beschikbare voorraad'}
    required_columns_website = {'Stiercode NL / KI code', 'Rasomschrijving', 'Status'}
    
    if not required_columns_stock.issubset(stock_df.columns):
        st.error("Het voorraadbestand mist vereiste kolommen! Controleer de structuur.")
        st.stop()
    if not required_columns_website.issubset(website_df.columns):
        st.error("Het webshopbestand mist vereiste kolommen! Controleer de structuur.")
        st.stop()
    
    # Zorg ervoor dat de kolomnaam correct overeenkomt met die in het Excel-bestand
    if 'Beschikbare voorraad' not in merged_df.columns:
        merged_df['Beschikbare voorraad'] = stock_df['Beschikbare voorraad'].fillna(0)
    
    # Zorg ervoor dat de waarden correct worden gelezen als numeriek
    merged_df['Beschikbare voorraad'] = pd.to_numeric(merged_df['Beschikbare voorraad'], errors='coerce').fillna(0).astype(int)
    
    to_remove = []
    to_add = []
    for index, row in merged_df.iterrows():
        if 'Rasomschrijving' in row and 'Stiercode NL / KI code' in row:
            ras = row['Rasomschrijving']
            status = row['Status'].strip().lower() if 'Status' in row else 'onbekend'
            for land in ['Nederland', 'Duitsland', 'België (NL)', 'België (FR)', 'Frankrijk']:
                drempel = threshold_dict.get((ras, land), 0)
                
                if row['Beschikbare voorraad'] < drempel and status == 'active':
                    to_remove.append(row)
                elif row['Beschikbare voorraad'] >= drempel and status in ['archive', 'concept']:
                    to_add.append(row)
    
    remove_df = pd.DataFrame(to_remove) if to_remove else pd.DataFrame(columns=['Stiercode NL / KI code', 'Naam stier', 'Beschikbare voorraad', 'Rasomschrijving', 'Status'])
    add_df = pd.DataFrame(to_add) if to_add else pd.DataFrame(columns=['Stiercode NL / KI code', 'Naam stier', 'Beschikbare voorraad', 'Rasomschrijving', 'Status'])
    
    return remove_df, add_df

# Streamlit UI
st.title("Voorraad en Website Status Beheer")

uploaded_stock = st.file_uploader("Upload Voorraad Rapport", type=["xlsx"])
uploaded_website = st.file_uploader("Upload Website Status Rapport", type=["xlsx"])

# Mogelijkheid om voorraad drempelwaardes in te stellen
st.sidebar.header("Voorraad Drempels Per Ras & Land")
theshold_dict = {}
land_options = ['Nederland', 'Duitsland', 'België (NL)', 'België (FR)', 'Frankrijk']

if uploaded_stock and uploaded_website:
    stock_df = load_data(uploaded_stock)
    website_df = load_data(uploaded_website)
    
    # Extract unieke rassen uit de bestanden
    stock_rassen = stock_df['Rasomschrijving'].dropna().unique().tolist()
    website_rassen = website_df['Rasomschrijving'].dropna().unique().tolist()
    ras_options = sorted(set(stock_rassen + website_rassen))
    
    if not ras_options:
        st.sidebar.warning("Geen rassen gevonden. Controleer of de juiste bestanden zijn geüpload.")
    else:
        with st.sidebar.expander("Drempelwaarden instellen", expanded=False):
            for ras in ras_options:
                with st.expander(f"{ras}"):
                    for land in land_options:
                        key = (ras, land)
                        threshold_dict[key] = st.number_input(f"Drempel voor {land}", min_value=0, value=10, key=f"{ras}_{land}")

# Knop om opnieuw te berekenen zonder opnieuw bestanden te uploaden
if st.button("Opnieuw berekenen") and uploaded_stock and uploaded_website:
    removal_list, addition_list = filter_products(stock_df, website_df, threshold_dict)
    
    if removal_list.empty:
        st.info("Geen producten hoeven van de webshop gehaald te worden.")
    else:
        st.subheader("Producten die van de webshop gehaald moeten worden:")
        st.dataframe(removal_list)
    
    if addition_list.empty:
        st.info("Geen producten hoeven geactiveerd te worden op de webshop.")
    else:
        st.subheader("Producten die weer actief gezet moeten worden op de webshop:")
        st.dataframe(addition_list)
    
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

# Debugging: Controleer of stock_df bestaat voordat we debuggen
if 'stock_df' in locals() and "Stiercode NL / KI code" in stock_df.columns:
    debug_stier = "782891-S"
    debug_info = stock_df[stock_df["Stiercode NL / KI code"] == debug_stier]
    print("Debug informatie voor", debug_stier)
    print(debug_info)
else:
    print("FOUT: stock_df is niet gedefinieerd of bevat niet de juiste kolommen.")
