import streamlit as st
import pandas as pd
from io import BytesIO

def load_data(uploaded_voorraden, uploaded_webshop):
    if uploaded_voorraden is not None and uploaded_webshop is not None:
        xls_voorraden = pd.ExcelFile(uploaded_voorraden)
        xls_webshop = pd.ExcelFile(uploaded_webshop)
        
        df_voorraden = pd.read_excel(xls_voorraden, sheet_name="Blad1")
        df_stieren = pd.read_excel(xls_webshop, sheet_name="Stieren")
        df_artikelvariaties = pd.read_excel(xls_webshop, sheet_name="Artikelvariaties")
        
        return df_voorraden, df_stieren, df_artikelvariaties
    return None, None, None

def determine_stock_status(df_voorraden, df_stieren, df_artikelvariaties, drempelwaarden):
    beperkt_conventioneel = []
    voldoende_conventioneel = []
    toevoegen_conventioneel = []
    
    beperkt_gesekst = []
    voldoende_gesekst = []
    toevoegen_gesekst = []
    
    for _, row in df_voorraden.iterrows():
        stiercode = str(row['Nr.'])
        voorraad = row['Beschikbare voorraad']
        ras = row['Rasomschrijving']
        naam_stier = row['Omschrijving']
        drempel = drempelwaarden.get(ras, 10)
        
        is_gesekst = "-S" in stiercode or "-M" in stiercode
        
        if not is_gesekst:
            # Conventioneel
            status_row = df_stieren[df_stieren['Stiercode NL / KI code'].astype(str) == stiercode]
            if not status_row.empty:
                status = status_row.iloc[0]['Status']
                if voorraad < drempel and status == "ACTIVE":
                    beperkt_conventioneel.append([stiercode, naam_stier, ras, voorraad, status])
                elif voorraad > drempel and status == "ARCHIVE":
                    voldoende_conventioneel.append([stiercode, naam_stier, ras, voorraad, status])
            else:
                toevoegen_conventioneel.append([stiercode, naam_stier, ras, voorraad, "Niet in webshop"])
        else:
            # Gesekst
            artikel_row = df_artikelvariaties[df_artikelvariaties['Nummer'].astype(str) == stiercode]
            if not artikel_row.empty:
                nederland_status = artikel_row.iloc[0]['Nederland']
                if voorraad < drempel and nederland_status == "Ja":
                    beperkt_gesekst.append([stiercode, naam_stier, ras, voorraad, nederland_status])
                elif voorraad > drempel and nederland_status == "Nee":
                    voldoende_gesekst.append([stiercode, naam_stier, ras, voorraad, nederland_status])
            else:
                if voorraad > drempel:
                    toevoegen_gesekst.append([stiercode, naam_stier, ras, voorraad, "Niet in webshop"])
    
    return beperkt_conventioneel, voldoende_conventioneel, toevoegen_conventioneel, beperkt_gesekst, voldoende_gesekst, toevoegen_gesekst

def save_to_excel(data):
    output = BytesIO()
    df = pd.DataFrame(data, columns=["Stiercode", "Naam Stier", "Ras", "Voorraad", "Status"])
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    output.seek(0)
    return output

def display_and_download(title, data, filename):
    df = pd.DataFrame(data, columns=["Stiercode", "Naam Stier", "Ras", "Voorraad", "Status"])
    st.write(f"## {title}")
    st.dataframe(df)
    st.download_button(f"Download {title}", save_to_excel(data), filename)

def main():
    st.title("Voorraad Checker")
    
    uploaded_voorraden = st.file_uploader("Upload 'Beschikbare voorraad lablocaties.xlsx'", type=["xlsx"])
    uploaded_webshop = st.file_uploader("Upload 'Status Webshop.xlsx'", type=["xlsx"])
    
    if uploaded_voorraden and uploaded_webshop:
        drempelwaarden = {
            "Holstein zwartbont": 50,
            "Red Holstein": 50,
            "Belgisch Witblauw": 50,
            "Jersey": 50
        }
        
        st.sidebar.header("Drempelwaarden per ras")
        for ras in ["Holstein zwartbont", "Red Holstein", "Belgisch Witblauw", "Jersey"]:
            drempelwaarden[ras] = st.sidebar.number_input(f"Drempel voor {ras}", min_value=1, value=50)
        overige_drempel = st.sidebar.number_input("Drempel voor overige rassen", min_value=1, value=10)
        
        df_voorraden, df_stieren, df_artikelvariaties = load_data(uploaded_voorraden, uploaded_webshop)
        
        unieke_rassen = df_voorraden['Rasomschrijving'].unique()
        for ras in unieke_rassen:
            if ras not in drempelwaarden:
                drempelwaarden[ras] = overige_drempel
        
        (beperkt_con, voldoende_con, toevoegen_con, 
        beperkt_ges, voldoende_ges, toevoegen_ges) = determine_stock_status(df_voorraden, df_stieren, df_artikelvariaties, drempelwaarden)
        
        display_and_download("Beperkte voorraad Conventioneel", beperkt_con, "Beperkte_Voorraad_Conventioneel.xlsx")
        display_and_download("Voldoende voorraad Conventioneel", voldoende_con, "Voldoende_Voorraad_Conventioneel.xlsx")
        display_and_download("Toevoegen website Conventioneel", toevoegen_con, "Toevoegen_Website_Conventioneel.xlsx")
        display_and_download("Beperkte voorraad Gesekst", beperkt_ges, "Beperkte_Voorraad_Gesekst.xlsx")
        display_and_download("Voldoende voorraad Gesekst", voldoende_ges, "Voldoende_Voorraad_Gesekst.xlsx")
        display_and_download("Toevoegen website Gesekst", toevoegen_ges, "Toevoegen_Website_Gesekst.xlsx")
    
if __name__ == "__main__":
    main()
