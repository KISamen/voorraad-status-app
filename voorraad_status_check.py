import streamlit as st
import pandas as pd

def load_data():
    file_voorraden = "Beschikbare voorraad lablocaties.xlsx"
    file_webshop = "Status Webshop.xlsx"
    
    xls_voorraden = pd.ExcelFile(file_voorraden)
    xls_webshop = pd.ExcelFile(file_webshop)
    
    df_voorraden = pd.read_excel(xls_voorraden, sheet_name="Blad1")
    df_stieren = pd.read_excel(xls_webshop, sheet_name="Stieren")
    df_artikelvariaties = pd.read_excel(xls_webshop, sheet_name="Artikelvariaties")
    
    return df_voorraden, df_stieren, df_artikelvariaties

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
        drempel = drempelwaarden.get(ras, 10)
        
        is_gesekst = "-S" in stiercode or "-M" in stiercode
        
        if not is_gesekst:
            # Conventioneel
            status_row = df_stieren[df_stieren['Stiercode NL / KI code'].astype(str) == stiercode]
            if not status_row.empty:
                status = status_row.iloc[0]['Status']
                if voorraad < drempel and status == "ACTIVE":
                    beperkt_conventioneel.append(stiercode)
                elif voorraad > drempel and status == "ARCHIVE":
                    voldoende_conventioneel.append(stiercode)
            else:
                toevoegen_conventioneel.append(stiercode)
        else:
            # Gesekst
            artikel_row = df_artikelvariaties[df_artikelvariaties['Nummer'].astype(str) == stiercode]
            if not artikel_row.empty:
                nederland_status = artikel_row.iloc[0]['Nederland']
                if voorraad < drempel and nederland_status == "Ja":
                    beperkt_gesekst.append(stiercode)
                elif voorraad > drempel and nederland_status == "Nee":
                    voldoende_gesekst.append(stiercode)
            else:
                toevoegen_gesekst.append(stiercode)
    
    return beperkt_conventioneel, voldoende_conventioneel, toevoegen_conventioneel, beperkt_gesekst, voldoende_gesekst, toevoegen_gesekst

def save_to_excel(data, filename):
    df = pd.DataFrame(data, columns=["Stiercode"])
    df.to_excel(filename, index=False)
    return filename

def main():
    st.title("Voorraad Checker")
    
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
    
    df_voorraden, df_stieren, df_artikelvariaties = load_data()
    
    unieke_rassen = df_voorraden['Rasomschrijving'].unique()
    for ras in unieke_rassen:
        if ras not in drempelwaarden:
            drempelwaarden[ras] = overige_drempel
    
    if st.button("Check voorraad"):
        (beperkt_con, voldoende_con, toevoegen_con, 
         beperkt_ges, voldoende_ges, toevoegen_ges) = determine_stock_status(df_voorraden, df_stieren, df_artikelvariaties, drempelwaarden)
        
        st.write("## Beperkte voorraad Conventioneel")
        st.write(beperkt_con)
        st.download_button("Download", save_to_excel(beperkt_con, "Beperkte_Voorraad_Conventioneel.xlsx"))
        
        st.write("## Voldoende voorraad Conventioneel")
        st.write(voldoende_con)
        st.download_button("Download", save_to_excel(voldoende_con, "Voldoende_Voorraad_Conventioneel.xlsx"))
        
        st.write("## Toevoegen website Conventioneel")
        st.write(toevoegen_con)
        st.download_button("Download", save_to_excel(toevoegen_con, "Toevoegen_Website_Conventioneel.xlsx"))
        
        st.write("## Beperkte voorraad Gesekst")
        st.write(beperkt_ges)
        st.download_button("Download", save_to_excel(beperkt_ges, "Beperkte_Voorraad_Gesekst.xlsx"))
        
        st.write("## Voldoende voorraad Gesekst")
        st.write(voldoende_ges)
        st.download_button("Download", save_to_excel(voldoende_ges, "Voldoende_Voorraad_Gesekst.xlsx"))
        
        st.write("## Toevoegen website Gesekst")
        st.write(toevoegen_ges)
        st.download_button("Download", save_to_excel(toevoegen_ges, "Toevoegen_Website_Gesekst.xlsx"))
    
if __name__ == "__main__":
    main()
