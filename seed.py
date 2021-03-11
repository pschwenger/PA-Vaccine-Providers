import requests
import csv

from util import get_service_account


from config import GOOGLE_SHEET_ID

# Replace these with your own seed data URLs and Google Sheet API

DATA_URL = "https://services1.arcgis.com/Nifc7wlHaBPig3Q3/ArcGIS/rest/services/Crosswalk_GISFields_SIIS_S123/FeatureServer/0/query?where=0%3D0&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&resultType=none&distance=100000&units=esriSRUnit_Meter&returnGeodetic=false&outFields=*&returnGeometry=true&featureEncoding=esriDefault&multipatchOption=xyFootprint&maxAllowableOffset=&geometryPrecision=&outSR=&datumTransformation=&applyVCSProjection=false&returnIdsOnly=false&returnUniqueIdsOnly=false&returnCountOnly=false&returnExtentOnly=false&returnQueryGeometry=false&returnDistinctValues=false&cacheHint=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&having=&resultOffset=&resultRecordCount=&returnZ=false&returnM=false&returnExceededLimitFeatures=true&quantizationParameters=&sqlFormat=none&f=pjson&token="


def download_source_data():
    json = requests.get(DATA_URL).json()
    clinic_sites = [clinic["attributes"] for clinic in json["features"]]
    return clinic_sites


def clean_clinic_data(clinic):
    return {
        "clinic_id": clinic["clinic_id"],
        "clinic_name": clinic["clinic_name"],
        "clinic_address": clinic["Match_addr"],
        "clinic_lat": clinic["Y"],
        "clinic_lon": clinic["X"],
        "clinic_phone": clinic["clinic_poc_phone"],
        "clinic_website": clinic["clinic_poc_websitelink"],
        "volume_ordered": clinic["Total_Moderna_Volume_Ordered"]
        + clinic["Total_Pfizer_Volume_Ordered"],
        "volume_current": clinic["Total_Moderna_Current_Volume"]
        + clinic["Total_Pfizer_Current_Volume"],
        "volume_administered": clinic["Total_Moderna_Administered_Vol"]
        + clinic["Total_Pfizer_Administered_Volum"],
        "appointments_available": "Yes",
        "walkins_accepted": "Yes",
        "clinic_prescreen_address": "",
        "clinic_hours": "",
        "show_on_map": "Yes",
    }


def write_csv(filename, clinics):
    with open(filename, "w") as f:
        fields = clinics[0].keys()

        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(clinics)


def create_google_sheet(csv_file):
    gc = get_service_account()

    with open(csv_file, "r") as f:
        content = f.read()
        gc.import_csv(GOOGLE_SHEET_ID, content)


if __name__ == "__main__":
    print("Downloading clinic data from ArcGIS...")
    clinics = [clean_clinic_data(clinic) for clinic in download_source_data()]

    print("Generating output csv...")
    write_csv("seed-data.csv", clinics)

    print("Uploading to GSheet")
    create_google_sheet("seed-data.csv")
