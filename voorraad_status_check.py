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
    
    # Strip kolomnamen om spaties te verwijderen
    voorraad_df.columns = voorraad_df.columns.str.strip()
    webshop_df.columns = webshop_df.columns.str.strip()
    
    # Debugging: Toon de werkelijke kolomnamen
    st.write("Kolomnamen voorraad_df:", voorraad_df.columns.tolist())
    st.write("Kolomnamen webshop_df:", webshop_df.columns.tolist())
    
    # Data voorbereiden
    voorraad_df = voorraad_df.rename(columns={"Nr": "Stiercode", "X": "Ras", "F": "Voorraad"})
    webshop_df = webshop_df.rename(columns={"F": "Stiercode", "C": "Ras", "G": "Status"})
    
    # Samenvoegen op Stiercode
    merged_df = pd.merge(voorraad_df, webshop_df, on="Stiercode", how="outer")
    
    # Unieke rassen ophalen
    unieke_rassen = merged_df["Ras"].dropna().unique()
    
    # Drempelwaarden per ras instellen
    for ras in unieke_rassen:
        drempelwaarden[ras] = st.sidebar.number_input(f"Drempelwaarde voor {ras}", min_value=0, value=default_drempel)
    
    # Functie om te bepalen in welke lijst een stier hoort
    def bepaal_status(row):
        voorraad = row["Voorraad"]
        status = row["Status"]
        ras = row["Ras"]
        drempel = drempelwaarden.get(ras, default_drempel)
        
        if pd.isna(voorraad) or pd.isna(status):
            return "Toevoegen aan Webshop" if voorraad > drempel else None
        
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
