import pandas as pd
import streamlit as st

# Streamlit app configureren
st.title("Stieren Voorraadbeheer")

# Drempelwaarden per ras beheren
st.sidebar.header("Instellingen")
drempelwaarden = {}
default_drempel = 500

# Upload bestanden
st.sidebar.subheader("Upload Bestanden")
webshop_file = st.sidebar.file_uploader("Upload Status Webshop (Excel)", type=["xlsx"])
voorraad_file = st.sidebar.file_uploader("Upload Beschikbare Voorraad Lablocaties (Excel)", type=["xlsx"])

if webshop_file and voorraad_file:
    # Inladen van de bestanden
    webshop_xls = pd.ExcelFile(webshop_file)
    voorraad_df = pd.read_excel(voorraad_file, sheet_name=0)  # Eerste sheet
    webshop_df = pd.read_excel(webshop_xls, sheet_name="Stieren")
    
    # Strip kolomnamen om spaties te verwijderen en naar kleine letters converteren
    voorraad_df.columns = voorraad_df.columns.str.strip().str.lower()
    webshop_df.columns = webshop_df.columns.str.strip().str.lower()
    
    # Debugging: Toon de werkelijke kolomnamen
    st.write("Kolomnamen voorraad_df:", voorraad_df.columns.tolist())
    st.write("Kolomnamen webshop_df:", webshop_df.columns.tolist())
    
    # Kolomnamen mappen inclusief varianten
    voorraad_df.rename(columns={"nr.": "Stiercode", "beschikbare voorraad": "Voorraad", "rasomschrijving": "Ras"}, inplace=True)
    webshop_df.rename(columns={"stiercode nl / ki code": "Stiercode", "rasomschrijving": "Ras", "status": "Status"}, inplace=True)
    
    # Debugging: Toon kolomnamen na hernoemen
    st.write("Kolomnamen na hernoemen - voorraad_df:", voorraad_df.columns.tolist())
    st.write("Kolomnamen na hernoemen - webshop_df:", webshop_df.columns.tolist())
    
    # Samenvoegen op Stiercode
    merged_df = pd.merge(voorraad_df, webshop_df, on="Stiercode", how="outer")
    st.write("Kolomnamen merged_df:", merged_df.columns.tolist())
    
    # Unieke rassen ophalen
    if "Ras" in merged_df.columns:
        unieke_rassen = merged_df["Ras"].dropna().unique()
    else:
        st.error("Fout: 'Ras' kolom niet gevonden in merged_df. Controleer of de juiste kolommen correct zijn ingelezen.")
        unieke_rassen = []
    
    # Drempelwaarden per ras instellen
    for ras in unieke_rassen:
        drempelwaarden[ras] = st.sidebar.number_input(f"Drempelwaarde voor {ras}", min_value=0, value=default_drempel)
    
    # Functie om te bepalen in welke lijst een stier hoort
    def bepaal_status(row):
        voorraad = row.get("Voorraad", None)
        status = row.get("Status", None)
        ras = row.get("Ras", None)
        drempel = drempelwaarden.get(ras, default_drempel)
        
        if pd.isna(voorraad) or pd.isna(status):
            return "Toevoegen aan Webshop" if voorraad and voorraad > drempel else None
        
        if voorraad < drempel and status == "Active":
            return "Stieren met beperkte voorraad (op archief zetten)"
        elif voorraad > drempel and status == "Archive":
            return "Controle: Mag weer online (op actief zetten)"
        
        return None
    
    # Status bepalen
    merged_df["Resultaat"] = merged_df.apply(bepaal_status, axis=1)
    
    # Resultaten tonen
    for categorie, titel in zip(["Stieren met beperkte voorraad (op archief zetten)",
                                 "Controle: Mag weer online (op actief zetten)",
                                 "Toevoegen aan Webshop"],
                                ["Stieren met beperkte voorraad (op archief zetten)",
                                 "Controlelijst: Mag weer online", "Toevoegen aan webshop"]):
        subset = merged_df[merged_df["Resultaat"] == categorie]
        if not subset.empty:
            st.subheader(titel)
            st.dataframe(subset[["Stiercode", "Ras", "Voorraad", "Status"]])
