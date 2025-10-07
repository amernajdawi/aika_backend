"""ÖNACE (Austrian Industry Classification) categories and management."""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import json
import os

@dataclass
class OnaceCategory:
    """Represents an ÖNACE category."""
    code: str
    name_german: str
    name_english: str
    description: str = ""

class OnaceManager:
    """Manages ÖNACE categories and document filtering."""
    
    # ÖNACE categories from the Excel file
    ONACE_CATEGORIES = {
        "0": OnaceCategory("0", "Allgemein", "General", "Applies to all industries"),
        "A": OnaceCategory("A", "LAND- UND FORSTWIRTSCHAFT, FISCHEREI (01 - 03)", "AGRICULTURE, FORESTRY, AND FISHING (01 - 03)"),
        "B": OnaceCategory("B", "BERGBAU UND GEWINNUNG VON STEINEN UND ERDEN (05 - 09)", "MINING AND QUARRYING (05 - 09)"),
        "C": OnaceCategory("C", "HERSTELLUNG VON WAREN (10 - 33)", "MANUFACTURING (10 - 33)"),
        "D": OnaceCategory("D", "ENERGIEVERSORGUNG (35)", "ENERGY SUPPLY (35)"),
        "E": OnaceCategory("E", "WASSERVERSORGUNG; ABWASSER- UND ABFALLENTSORGUNG UND BESEITIGUNG VON UMWELTVERSCHMUTZUNGEN (36 - 39)", "WATER SUPPLY; SEWAGE AND WASTE DISPOSAL AND REMOVAL OF ENVIRONMENTAL POLLUTION (36 - 39)"),
        "F": OnaceCategory("F", "BAU (41 - 43)", "CONSTRUCTION (41 - 43)"),
        "G": OnaceCategory("G", "HANDEL (46 - 47)", "TRADE (46 - 47)"),
        "H": OnaceCategory("H", "VERKEHR UND LAGEREI (49 - 53)", "TRANSPORT AND STORAGE (49 - 53)"),
        "I": OnaceCategory("I", "BEHERBERGUNG UND GASTRONOMIE (55 - 56)", "ACCOMMODATION AND CATERING (55 - 56)"),
        "J": OnaceCategory("J", "VERLAGSWESEN, RUNDFUNK SOWIE ERSTELLUNG UND VERBREITUNG VON MEDIENINHALTEN (58 - 60)", "PUBLISHING, BROADCASTING AND PRODUCTION AND DISTRIBUTION OF MEDIA CONTENT (58 - 60)"),
        "K": OnaceCategory("K", "ERBRINGUNG VON FINANZ- UND VERSICHERUNGSDIENSTLEISTUNGEN (64 - 66)", "FINANCIAL AND INSURANCE SERVICES (64 - 66)"),
        "L": OnaceCategory("L", "GRUNDSTÜCKS- UND WOHNUNGSWESEN (68)", "REAL ESTATE ACTIVITIES (68)"),
        "M": OnaceCategory("M", "ERBRINGUNG VON FREIBERUFLICHEN, WISSENSCHAFTLICHEN UND TECHNISCHEN DIENSTLEISTUNGEN (69 - 75)", "PROFESSIONAL, SCIENTIFIC AND TECHNICAL ACTIVITIES (69 - 75)"),
        "N": OnaceCategory("N", "ERBRINGUNG VON SONSTIGEN WIRTSCHAFTLICHEN DIENSTLEISTUNGEN (77 - 82)", "ADMINISTRATIVE AND SUPPORT SERVICE ACTIVITIES (77 - 82)"),
        "O": OnaceCategory("O", "ÖFFENTLICHE VERWALTUNG, VERTEIDIGUNG; SOZIALVERSICHERUNG (84)", "PUBLIC ADMINISTRATION, DEFENCE; COMPULSORY SOCIAL SECURITY (84)"),
        "P": OnaceCategory("P", "ERZIEHUNG UND UNTERRICHT (85)", "EDUCATION (85)"),
        "Q": OnaceCategory("Q", "GESUNDHEITSWESEN UND SOZIALE DIENSTLEISTUNGEN (86 - 88)", "HUMAN HEALTH AND SOCIAL WORK ACTIVITIES (86 - 88)"),
        "R": OnaceCategory("R", "KUNST, UNTERHALTUNG UND ERHOLUNG (90 - 93)", "ARTS, ENTERTAINMENT AND RECREATION (90 - 93)"),
        "S": OnaceCategory("S", "ERBRINGUNG VON SONSTIGEN DIENSTLEISTUNGEN (94 - 96)", "OTHER SERVICE ACTIVITIES (94 - 96)"),
        "T": OnaceCategory("T", "PRIVATE HAUSHALTE MIT HAUSHALTSPERSONAL; ERBRINGUNG VON DIENSTLEISTUNGEN FÜR PRIVATE HAUSHALTE ALS ARBEITGEBER (97 - 98)", "ACTIVITIES OF HOUSEHOLDS AS EMPLOYERS; UNDIFFERENTIATED GOODS- AND SERVICES-PRODUCING ACTIVITIES OF HOUSEHOLDS FOR OWN USE (97 - 98)"),
        "U": OnaceCategory("U", "EXTERRITORIALE ORGANISATIONEN UND KÖRPERSCHAFTEN (99)", "ACTIVITIES OF EXTRATERRITORIAL ORGANISATIONS AND BODIES (99)")
    }
    
    @classmethod
    def get_category(cls, code: str) -> Optional[OnaceCategory]:
        """Get ÖNACE category by code."""
        return cls.ONACE_CATEGORIES.get(code)
    
    @classmethod
    def get_all_categories(cls) -> Dict[str, OnaceCategory]:
        """Get all ÖNACE categories."""
        return cls.ONACE_CATEGORIES.copy()
    
    @classmethod
    def parse_onace_codes(cls, onace_string: str) -> Set[str]:
        """Parse ÖNACE codes from string (handles multiple codes like 'A, B, C')."""
        if not onace_string or onace_string == "nan":
            return {"0"}  # Default to general
        
        # Handle different formats
        codes = set()
        
        # Split by comma and clean
        for code in str(onace_string).split(','):
            code = code.strip()
            if code and code in cls.ONACE_CATEGORIES:
                codes.add(code)
        
        # If no valid codes found, default to general
        if not codes:
            codes.add("0")
            
        return codes
    
    @classmethod
    def get_category_names(cls, codes: Set[str]) -> Dict[str, str]:
        """Get category names for given codes."""
        return {
            code: cls.ONACE_CATEGORIES[code].name_english 
            for code in codes 
            if code in cls.ONACE_CATEGORIES
        }
    
    @classmethod
    def is_document_relevant(cls, document_onace_codes: Set[str], user_onace_code: str) -> bool:
        """Check if a document is relevant for a user's ÖNACE code."""
        # General documents (code 0) are always relevant
        if "0" in document_onace_codes:
            return True
        
        # Check if user's code matches any of the document's codes
        return user_onace_code in document_onace_codes
    
    @classmethod
    def get_relevant_documents(cls, documents: List[Dict], user_onace_code: str) -> List[Dict]:
        """Filter documents based on user's ÖNACE code."""
        relevant_docs = []
        
        for doc in documents:
            doc_onace_codes = cls.parse_onace_codes(doc.get('onace_codes', '0'))
            if cls.is_document_relevant(doc_onace_codes, user_onace_code):
                relevant_docs.append(doc)
        
        return relevant_docs

def load_document_onace_mapping() -> Dict[str, str]:
    """Load the mapping of document names to ÖNACE codes from Excel data."""
    # Updated mapping from AiKA overview.xlsx file
    return {
        "EG_2008_1272_VerpackungundKennzeichnung": "C",
        "EG_2008_98_Abfälle": "E",
        "EU_1991_676_GewässerschutzNitrat": "A",
        "EU_1999_31_Abfalldeponien": "E",
        "EU_2000_532_KatalogAbfälle": "0",
        "EU_2000_60_OrdnungsrahmenWasserpolitik": "0",
        "EU_2003_87_EuropeanTradingSystem": "0",
        "EU_2004_109 TransparenzanforderungenWPEmittenten": "0",
        "EU_2006_118_SchutzdGrundwassers": "0",
        "EU_2006_166_Schadstofffreisetzungsregister": "A, B, C, D, E",
        "EU_2006_1907_REACH": "C",
        "EU_2006_43 AbschlussprüfungJA": "0",
        "EU_2009_1221_Umweltmanagementsystem": "0",
        "EU_2009_401_EuropUmweltagentur": "0",
        "EU_2010_75_EmissionenIndustrieuTierhaltung": "B, C, D, E",
        "EU_2011_70_EURATOMRadioaktiveAbfälle": "0",
        "EU_2013_488_Verschlusssachen": "0",
        "EU_2013_575_CapitalRequirementsRegulation(CRR)": "L",
        "EU_2014_1252_CriticalRawMaterial": "B, C, D, E",
        "EU_2014_34_ATEX": "0",
        "EU_2014_537_AbschlussprüferUöffentlIntersesse": "0",
        "EU_2015_801_EMASEinzelhandel": "G",
        "EU_2015_HandbookEUETS": "0",
        "EU_2016_1011_Benchmarkverordnung": "L",
        "EU_2016_2284_ReduktionenvEmissionen": "A, D, C, H, F",
        "EU_2016_611_EMASTourismus": "I",
        "EU_2017_1508_EMASNahrungsmittelundGetränke": "C",
        "EU_2018_1999_GovSysfKlimaschutz": "0",
        "EU_2018_2001_ErneuerbareEnergien": "0",
        "EU_2018_813_EMASLandwirtschaft": "A",
        "EU_2019_2088_OffenlegungnachhaltigerInvestitionen": "L",
        "EU_2019_61_BranchenspezUmweltmanagementpraktiken": "P",
        "EU_2019_62_EMASHerstellungKraftwagenKraftwagenteilen": "C",
        "EU_2019_63_EMASHerstellungelektronischerGeräte": "C",
        "EU_2019_640_GreenDeal": "0",
        "EU_2020_1816_ESGDisclosureBenchmarks": "L",
        "EU_2020_1818_Referenzwerte": "0",
        "EU_2020_519_EMASAbfallbewirtschaftung": "E",
        "EU_2021_2053_EMASHerstellungMetallerzeugnisse": "C",
        "EU_2021_2054_EMASLKommunikationundIT": "K",
        "EU_2021_2139_EUTaxonomietechnischeBewertungskriterien": "0",
        "EU_2022_1288_TechnischeStandardsSFDR": "L",
        "EU_2022_2464_CSRD": "0",
        "EU_2023_1115_EUDR": "0",
        "EU_2023_137_NACE": "0",
        "EU_2023_34 Jahresabschluss": "0",
        "EU_2023_3463_NutzerhandbuchEUETSEMAS": "0",
        "EU_2023_956_CBAM": "C, G",
        "EU_2024_1244_BerichterstattungUmweltdatenIndustrieanalgen": "A, B, D, C, E, F",
        "EU_2024_1760_Sorgfaltspflichten CSDDD": "0",
        "EU_2024_GuidanceEUETS": "0",
        "EU_2025_1710_VSME": "0",  # Main VSME document
        "EU_2025_85_CleanIndustrialDeal": "0",
        "EWG_86_278_KlärschlammLandwirtschaft": "A",
        "G_2004_GHGProtocolCorporateStandard": "0",
        "G_2011_GHG_CorporateValueChain": "0",
        "G_2011_GHG_ProtuctLifeCycleAccounting": "C",
        "G_2013_ToolkitStockholmConvention": "0",
        "G_2018_SBTi_Apparal&Footwear": "C",
        "G_2021_SBTi_Aviation": "H",
        "G_2022_CCACSEI": "0",
        "G_2022_SBTi_Cement": "C, F",
        "G_2022_WateremissionCalculatingMethod": "0",
        "G_2023_SBTi_FLAG": "A",
        "G_2023_SBTi_FLAGbrief": "A",
        "G_2023_SBTi_Steel": "C",
        "G_2023_SBTi_SteelTOOL": "C",
        "G_2024_SBTi_BuildingCriteria": "F",
        "G_2024_SBTi_LandTransport": "H",
        "G_2025_CDP_ConversionMWh": "0",
        "G_2025_SBTi_Automotive": "H",
        "G_2025_SBTi_Building": "F",
        "G_2025_SBTi_BuildingCriteriaFAQ": "F",
        "G_2025_SBTi_BuildingTargetExplanatory": "F",
        "G_2025_SBTi_PowerDraft": "D",
        "G_2025_Umweltbundesamt_PRTR": "0",
        "VSME-Digital-Template-1.0.1": "0",  # VSME template
    }
