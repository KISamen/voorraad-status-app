import pandas as pd
import streamlit as st
import io

# Functie om data in te laden
def load_data(file, sheet_name=None):
    try:
        return pd.read_excel(file, sheet_name=sheet_name)
    except Exception as e:
        st.error(f"Fout bij het laden van het bestand: {e}")
        return None

# Functie om producten te filteren op basis van voorraad drempelwaardes
def filter_products(stock_df, website_df, threshold_dict):
    if stock_df is None or website_df is None:
        st.error("Één van de datasets kon niet correct worden geladen.")
        return pd.DataFrame(), pd.DataFrame()
    
    stock_df = stock_df.rename(columns={'Nr.': 'Stiercode NL / KI code', 'Ras omschrijving': 'Rasomschrijving'})
    website_df = website_df.rename(columns={'Ras omschrijving': 'Rasomschrijving'})
    
    if isinstance(website_df, dict) and 'Stieren' in website_df:
        website_df = website_df['Stieren']
    
    if 'Stiercode NL / KI code' not in stock_df.columns or 'Stiercode NL / KI code' not in website_df.columns:
        st.error("Kolommen ontbreken in de geüploade bestanden.")
        return pd.DataFrame(), pd.DataFrame()
    
    merged_df = pd.merge(website_df, stock_df, on='Stiercode NL / KI code', how='left')
    
    if 'Beschikbare voorraad' not in merged_df.columns:
        merged_df['Beschikbare voorraad'] = 0
    
    merged_df['Beschikbare voorraad'] = pd.to_numeric(merged_df['Beschikbare voorraad'], errors='coerce').fillna(0).astype(int)
    
    to_remove, to_add = [], []
    for _, row in merged_df.iterrows():
        ras = row.get('Rasomschrijving', 'Onbekend')
        status = str(row.get('Status', 'onbekend')).strip().lower()
        voorraad = row.get('Beschikbare voorraad', 0)
        drempel = threshold_dict.get(ras, 0)
        
        if voorraad < drempel and status == 'active':
            to_remove.append(row)
        elif voorraad >= drempel and status == 'archive':
            to_add.append(row)
    
    return pd.DataFrame(to_remove), pd.DataFrame(to_add)

# Streamlit UI
st.title("Voorraad en Website Status Beheer")

uploaded_stock = st.file_uploader("Upload Voorraad Rapport", type=["xlsx"])
uploaded_website = st.file_uploader("Upload Website Status Rapport", type=["xlsx"])

st.sidebar.header("Voorraad Drempels Per Ras")
threshold_dict = {}

if uploaded_stock and uploaded_website:
    stock_df = load_data(uploaded_stock)
    website_df_dict = load_data(uploaded_website, sheet_name=None)
    website_df = website_df_dict.get('Stieren') if isinstance(website_df_dict, dict) else None
    
    if website_df is None:
        st.error("Het tabblad 'Stieren' ontbreekt in het geüploade bestand!")
        st.stop()
    
    if stock_df is not None and website_df is not None:
        stock_rassen = stock_df.get('Rasomschrijving', pd.Series()).dropna().unique().tolist()
        website_rassen = website_df.get('Rasomschrijving', pd.Series()).dropna().unique().tolist()
        ras_options = sorted(set(stock_rassen + website_rassen))
        
        with st.sidebar.expander("Drempelwaarden instellen", expanded=False):
            for ras in ras_options:
                threshold_dict[ras] = st.sidebar.number_input(f"Drempelwaarde voor {ras}", min_value=0, value=10, key=f"{ras}")

if st.button("Opnieuw berekenen") and uploaded_stock and uploaded_website:
    removal_list, addition_list = filter_products(stock_df, website_df, threshold_dict)
    
    if not removal_list.empty:
        st.subheader("Producten die van de webshop gehaald moeten worden:")
        st.dataframe(removal_list)
    else:
        st.info("Geen producten hoeven van de webshop gehaald te worden.")
    
    if not addition_list.empty:
        st.subheader("Producten die weer actief gezet moeten worden op de webshop:")
        st.dataframe(addition_list)
    else:
        st.info("Geen producten hoeven geactiveerd te worden op de webshop.")
    
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
