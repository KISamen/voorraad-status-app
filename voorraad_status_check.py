import pandas as pd
import streamlit as st
import io

# Functie om data in te laden
def load_data(file, sheet_name=None):
    try:
        df = pd.read_excel(file, sheet_name=sheet_name)
        if isinstance(df, dict):  # Voor meerdere sheets
            return {k: v if isinstance(v, pd.DataFrame) else None for k, v in df.items()}
        return df if isinstance(df, pd.DataFrame) else None
    except Exception as e:
        st.error(f"Fout bij het laden van het bestand: {e}")
        return None

# Functie om producten te filteren op basis van voorraad drempelwaardes
def filter_products(stock_df, website_df, threshold_dict):
    if stock_df is None or not isinstance(stock_df, pd.DataFrame):
        st.error("Fout: 'stock_df' is geen geldige DataFrame of ontbreekt.")
        return pd.DataFrame(), pd.DataFrame()
    
    if website_df is None or not isinstance(website_df, pd.DataFrame):
        st.error("Fout: 'website_df' is geen geldige DataFrame of ontbreekt.")
        return pd.DataFrame(), pd.DataFrame()
    
    stock_df = stock_df.rename(columns={'Nr.': 'Stiercode NL / KI code', 'Ras omschrijving': 'Rasomschrijving'})
    website_df = website_df.rename(columns={'Ras omschrijving': 'Rasomschrijving'})
    
    required_columns_stock = {'Stiercode NL / KI code', 'Beschikbare voorraad', 'Rasomschrijving'}
    required_columns_website = {'Stiercode NL / KI code', 'Rasomschrijving', 'Status'}
    
    if not required_columns_stock.issubset(stock_df.columns):
        st.error("Het voorraadbestand mist vereiste kolommen!")
        return pd.DataFrame(), pd.DataFrame()
    
    if not required_columns_website.issubset(website_df.columns):
        st.error("Het webshopbestand mist vereiste kolommen!")
        return pd.DataFrame(), pd.DataFrame()
    
    merged_df = pd.merge(website_df, stock_df, on='Stiercode NL / KI code', how='left')
    merged_df['Beschikbare voorraad'] = pd.to_numeric(merged_df.get('Beschikbare voorraad', 0), errors='coerce').fillna(0).astype(int)
    
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

threshold_dict = {}

if uploaded_stock and uploaded_website:
    stock_df = load_data(uploaded_stock)
    website_df_dict = load_data(uploaded_website, sheet_name=None)
    website_df = website_df_dict.get('Stieren') if isinstance(website_df_dict, dict) else None
    
    if website_df is None:
        st.error("Het tabblad 'Stieren' ontbreekt in het geüploade bestand!")
        st.stop()
    
    if stock_df is not None and website_df is not None:
        stock_rassen = stock_df.get('Rasomschrijving', pd.Series(dtype=str)).dropna().unique().tolist()
        website_rassen = website_df.get('Rasomschrijving', pd.Series(dtype=str)).dropna().unique().tolist()
        ras_options = sorted(set(stock_rassen + website_rassen))
        
        with st.sidebar.expander("Drempelwaarden instellen", expanded=False):
            for ras in ras_options:
                threshold_dict[ras] = st.sidebar.number_input(f"Drempelwaarde voor {ras}", min_value=0, value=500, key=f"{ras}")

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
