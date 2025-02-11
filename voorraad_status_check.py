import pandas as pd
import streamlit as st
from io import BytesIO

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
    
    # Kolomnamen mappen inclusief varianten
    voorraad_df.rename(columns={"nr.": "Stiercode", "beschikbare voorraad": "Voorraad", "rasomschrijving": "Ras", "naam stier": "naam stier"}, inplace=True)
    webshop_df.rename(columns={"stiercode nl / ki code": "Stiercode", "rasomschrijving": "Ras", "status": "Status", "naam stier": "naam stier"}, inplace=True)
    
    # Samenvoegen op Stiercode
    merged_df = pd.merge(voorraad_df, webshop_df, on="Stiercode", how="outer")
    
    # Corrigeren van de Ras-kolom (Ras_x en Ras_y samenvoegen)
    if "Ras_y" in merged_df.columns:
        merged_df["Ras"] = merged_df["Ras_y"].combine_first(merged_df["Ras_x"])
    elif "Ras_x" in merged_df.columns:
        merged_df.rename(columns={"Ras_x": "Ras"}, inplace=True)
    
    # Corrigeren van de Naam Stier-kolom (Correct toevoegen vóór verwijdering)
    merged_df["Naam Stier"] = merged_df.get("naam stier_y", "").combine_first(merged_df.get("naam stier_x", ""))
    
    # Drop overbodige kolommen
    merged_df.drop(columns=[col for col in ["Ras_x", "Ras_y", "naam stier_x", "naam stier_y"] if col in merged_df.columns], inplace=True)
    
    # Status en Voorraad normaliseren
    merged_df["Status"] = merged_df["Status"].astype(str).str.strip().str.upper()
    merged_df["Voorraad"] = merged_df["Voorraad"].fillna(0)
    
    # Stiercode als string weergeven zonder komma's
    merged_df["Stiercode"] = merged_df["Stiercode"].astype(str).str.strip()
    
    # Unieke rassen ophalen en sorteren
    unieke_rassen = sorted(merged_df["Ras"].dropna().unique())
    
    # Drempelwaarden per ras instellen
    for ras in unieke_rassen:
        drempelwaarden[ras] = st.sidebar.number_input(f"Drempelwaarde voor {ras}", min_value=0, value=default_drempel)
    
    # Functie om te bepalen in welke lijst een stier hoort
    def bepaal_status(row):
        voorraad = row.get("Voorraad", 0)  # Alleen correcte voorraadkolom gebruiken
        status = row.get("Status", "").strip().upper()
        ras = row.get("Ras", None)
        drempel = drempelwaarden.get(ras, default_drempel)
        
        if status == "CONCEPT":
            return "Concept: Toevoegen aan Webshop" if voorraad > drempel else "Concept: Lage voorraad"
        
        if status not in ["ACTIVE", "ARCHIVE"]:
            return "Toevoegen aan Webshop" if voorraad > drempel else None
        
        if voorraad < drempel and status == "ACTIVE":
            return "Stieren met beperkte voorraad (op archief zetten)"
        elif voorraad > drempel and status == "ARCHIVE":
            return "Voorraad weer voldoende (op actief zetten)"
        
        return None
    
    # Status bepalen
    merged_df["Resultaat"] = merged_df.apply(bepaal_status, axis=1)
    
    # Opslaan van resultaten
    resultaten = {}
    for categorie, titel in zip(["Stieren met beperkte voorraad (op archief zetten)",
                                 "Voorraad weer voldoende (op actief zetten)",
                                 "Toevoegen aan Webshop",
                                 "Concept: Toevoegen aan Webshop",
                                 "Concept: Lage voorraad"],
                                ["Stieren met beperkte voorraad (op archief zetten)",
                                 "Controlelijst: Mag weer online", "Toevoegen aan webshop",
                                 "Conceptstatus: Toevoegen aan webshop", "Conceptstatus: Lage voorraad"]):
        subset = merged_df[merged_df["Resultaat"] == categorie].sort_values(by=["Ras"])
        if not subset.empty:
            st.subheader(titel)
            st.dataframe(subset[["Stiercode", "Naam Stier", "Ras", "Voorraad", "Status"]])
            resultaten[titel] = subset[["Stiercode", "Naam Stier", "Ras", "Voorraad", "Status"]]
    
    # Excel-downloadknop
    if resultaten:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for sheet_name, df in resultaten.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        output.seek(0)
        st.download_button(label="Download Excel-bestand", data=output, file_name="Stieren_Voorraad_Resultaten.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
