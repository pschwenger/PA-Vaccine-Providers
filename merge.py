import csv
import pickle
import re
import os.path
import gspread

from config import FORM_SHEET_NAME, PROVIDER_SHEET_NAME, GOOGLE_SHEET_ID
from util import get_service_account

FORM_CLINIC_ID_KEY = "Clinic ID"
FORM_CLINIC_NAME_KEY = "Clinic name"
FORM_APPROVED_KEY = "Admin: Approved"
FORM_APPOINTMENTS_AVAILABLE_KEY = "Appointments available?"
FORM_WALKIN_KEY = "Walk-ins accepted?"
FORM_ADDRESS_KEY = "Clinic Address"

CLINIC_ID_KEY = "clinic_id"
CLINIC_NAME_KEY = "clinic_name"
CLINIC_APPOINTMENTS_AVAILABLE_KEY = "appointments_available"
CLINIC_WALKIN_KEY = "walkins_accepted"
CLINIC_ADDRESS_KEY = "clinic_address"


def translate_update_to_clinic(update):
    """Returns a clinic object from all fields"""
    return {
        CLINIC_ID_KEY: update[FORM_CLINIC_ID_KEY],
        CLINIC_NAME_KEY: update[FORM_CLINIC_NAME_KEY],
        CLINIC_APPOINTMENTS_AVAILABLE_KEY: update[FORM_APPOINTMENTS_AVAILABLE_KEY],
        CLINIC_WALKIN_KEY: update[FORM_WALKIN_KEY],
        CLINIC_ADDRESS_KEY: update[FORM_ADDRESS_KEY],
        FORM_APPROVED_KEY: update[FORM_APPROVED_KEY],
    }


def get_clinic_updates():
    """Downloads the update data from Google Sheets"""
    gc = gspread.service_account()

    sheet = gc.open_by_key(GOOGLE_SHEET_ID)

    worksheet = sheet.worksheet(FORM_SHEET_NAME)
    vals = worksheet.get_all_values()
    keys = []
    updates = []

    for (i, val) in enumerate(vals):
        if i == 0:
            keys = val
        else:
            updates.append(dict(zip(keys, val)))

    return updates


def find_valid_clinic(clinics, clinic):
    """Tells us whether a given clinic is valid"""
    clinic_id = clinic[CLINIC_ID_KEY]
    clinic_name = clinic[CLINIC_NAME_KEY]

    for c in clinics:
        if c[CLINIC_ID_KEY] == clinic_id and c[CLINIC_NAME_KEY] == clinic_name:
            return c
    return False


def merge_clinics(clinics, updates):
    for update in updates:
        update_as_clinic = translate_update_to_clinic(update)

        clinic = find_valid_clinic(clinics, update_as_clinic)
        if clinic:
            print("Updating:", update_as_clinic)
            update_clinic(update_as_clinic)
        else:
            print("Failed to update:", update_as_clinic)


def update_clinic(clinic_update):
    """Update in gsheets"""
    gc = get_service_account()

    sheet = gc.open_by_key(GOOGLE_SHEET_ID)
    worksheet = sheet.worksheet(PROVIDER_SHEET_NAME)

    DENY_LIST = [CLINIC_APPOINTMENTS_AVAILABLE_KEY, CLINIC_WALKIN_KEY]

    update_re = re.compile("^" + clinic_update[CLINIC_NAME_KEY] + "$")
    cell = worksheet.find(update_re)

    keys = worksheet.row_values(1)
    update_row = worksheet.row_values(cell.row)

    for (key, val) in clinic_update.items():
        if val == "" or key not in keys:
            continue

        if key in DENY_LIST and clinic_update[FORM_APPROVED_KEY] != "Yes":
            continue

        idx = keys.index(key)
        worksheet.update_cell(cell.row, idx + 1, val)


def get_clinics():
    """Downloads the merged data from Google Sheets"""
    gc = gspread.service_account()

    sheet = gc.open_by_key(GOOGLE_SHEET_ID)
    worksheet = sheet.worksheet(PROVIDER_SHEET_NAME)

    vals = worksheet.get_all_values()
    keys = []
    clinics = []

    for (i, val) in enumerate(vals):
        if i == 0:
            keys = val
        else:
            clinics.append(dict(zip(keys, val)))

    return clinics


if __name__ == "__main__":
    print("Fetching clinics...")
    clinics = get_clinics()

    # update with more recent information
    print("Combining with updated information...")
    clinic_updates = get_clinic_updates()

    merge_clinics(clinics, clinic_updates)

    # # hide any approved hidden value within two weeks
    # print("Hiding approved hidden values...")
    # supply_updates = get_unavailable_clinic_info()
    # remove_unavailable_clinics(clinics, supply_updates)
