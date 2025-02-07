import pandas as pd
import streamlit as st
import io

# Functie om data in te laden
def load_data(file, sheet_name=None):
    try:
        df = pd.read_excel(file, sheet_name=sheet_name)
        if isinstance(df, dict):
            return df  # Voor meerdere sheets
        elif isinstance(df, pd.DataFrame):
            return df  # Enkel blad wordt ingelezen als DataFrame
        else:
            st.error("Fout: Ingelezen bestand is geen geldige DataFrame.")
            return None
    except Exception as e:
        st.error(f"Fout bij het laden van het bestand: {e}")
        return None

# Functie om producten te filteren op basis van voorraad drempelwaardes
def filter_products(stock_df, website_df, threshold_dict):
    if stock_df is None or website_df is None:
        st.error("Fout: Een of beide dataframes ontbreken.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    # Kolomnamen corrigeren
    stock_df = stock_df.rename(columns={'Nr.': 'Stiercode NL / KI code', 'Ras omschrijving': 'Rasomschrijving'})
    website_df = website_df.rename(columns={'Ras omschrijving': 'Rasomschrijving'})
    
    # Controleer of de verwachte kolommen aanwezig zijn
    required_columns_stock = {'Stiercode NL / KI code', 'Beschikbare voorraad', 'Rasomschrijving'}
    required_columns_website = {'Stiercode NL / KI code', 'Rasomschrijving', 'Status'}

    if not required_columns_stock.issubset(stock_df.columns) or not required_columns_website.issubset(website_df.columns):
        st.error("Fout: Vereiste kolommen ontbreken in de bestanden!")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    # Merge de dataframes
    merged_df = pd.merge(website_df, stock_df, on='Stiercode NL / KI code', how='left')
    merged_df['Beschikbare voorraad'] = pd.to_numeric(merged_df.get('Beschikbare voorraad', 0), errors='coerce').fillna(0).astype(int)
    
    to_remove, to_add, ignored = [], [], []

    for _, row in merged_df.iterrows():
        ras = row.get('Rasomschrijving', 'Onbekend')
        status = str(row.get('Status', 'onbekend')).strip().lower()
        voorraad = row.get('Beschikbare voorraad', 0)
        drempel = threshold_dict.get(ras, 0)

        if voorraad < drempel and status == 'active':
            to_remove.append(row)
        elif voorraad >= drempel and status == 'archive':
            to_add.append(row)
        else:
            ignored.append(row)

    return pd.DataFrame(to_remove), pd.DataFrame(to_add), pd.DataFrame(ignored)

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
    
    if stock_df is not None and isinstance(stock_df, pd.DataFrame) and website_df is not None:
        stock_rassen = stock_df.get('Rasomschrijving', pd.Series()).dropna().unique().tolist()
        website_rassen = website_df.get('Rasomschrijving', pd.Series()).dropna().unique().tolist()
        ras_options = sorted(set(stock_rassen + website_rassen))
        
        with st.sidebar.expander("Drempelwaarden instellen", expanded=True):
            for ras in ras_options:
                threshold_dict[ras] = st.sidebar.number_input(f"Drempelwaarde voor {ras}", min_value=0, value=10, key=f"{ras}")

if st.button("Opnieuw berekenen") and uploaded_stock and uploaded_website:
    removal_list, addition_list, ignored_list = filter_products(stock_df, website_df, threshold_dict)
    
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
    
    if not ignored_list.empty:
        st.subheader("Producten die niet gewijzigd hoeven te worden:")
        st.dataframe(ignored_list)
    
    if not removal_list.empty or not addition_list.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            removal_list.to_excel(writer, sheet_name="Te verwijderen", index=False)
            addition_list.to_excel(writer, sheet_name="Te activeren", index=False)
            ignored_list.to_excel(writer, sheet_name="Geen wijziging", index=False)
        output.seek(0)
        st.download_button(
            label="Download Lijst",
            data=output.getvalue(),
            file_name="voorraad_status_update.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
