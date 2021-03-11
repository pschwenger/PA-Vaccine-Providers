import csv
import pickle
import re
import os.path

from config import GOOGLE_SHEET_ID_UPDATE, GOOGLE_SHEET_ID_PRIMARY, PROVIDER_SHEET_NAME, FORM_SHEET_NAME, LAST_UPDATE_SHEET_NAME, GOOGLE_SHEET_ID_LAST_UPDATE
from util import get_worksheet, get_columns, get_service_account, is_integer, is_float

FORM_CLINIC_ID_KEY = "Enter your Clinic ID (without leading zeroes)"
FORM_CLINIC_NAME_KEY = "Clinic Name"
FORM_APPROVED_KEY = "Admin Approval"
FORM_APPOINTMENTS_AVAILABLE_KEY = "Vaccine Appointments Available"
FORM_WALKIN_KEY = "Walk-ins Accepted"
FORM_ADDRESS_KEY = "Street Address"
FORM_CITY_KEY = "City"
FORM_STATE_KEY = "State"
FORM_ZIP_KEY = "Zip Code"
FORM_WEBSITE_KEY = "Clinic Website"
FORM_REVIEW_KEY = "Approval Review Completed"
FORM_PROCESSED_KEY = "Script Processed"
FORM_NOTES_KEY = "Notes"

CLINIC_ID_KEY = "Clinic ID"
CLINIC_NAME_KEY = "Clinic Name"
CLINIC_APPOINTMENTS_AVAILABLE_KEY = "Vaccine Appointments Available"
CLINIC_WALKIN_KEY = "Walk-ins Accepted"
CLINIC_ADDRESS_KEY = "Street Address"
CLINIC_CITY_KEY = "City"
CLINIC_STATE_KEY = "State"
CLINIC_ZIP_KEY = "ZIP Code"
CLINIC_WEBSITE_KEY = "Clinic Website"
CLINIC_LAST_UPDATED_KEY = "Last Updated"

UPDATE_COUNT = 0


def translate_update_to_clinic(update):
    """Returns a clinic object from all fields"""
    return {
        CLINIC_ID_KEY: update[FORM_CLINIC_ID_KEY],
        CLINIC_NAME_KEY: update[FORM_CLINIC_NAME_KEY],
        CLINIC_APPOINTMENTS_AVAILABLE_KEY: update[FORM_APPOINTMENTS_AVAILABLE_KEY],
        CLINIC_WALKIN_KEY: update[FORM_WALKIN_KEY],
        CLINIC_ADDRESS_KEY: update[FORM_ADDRESS_KEY],
        CLINIC_CITY_KEY: update[FORM_CITY_KEY],
        CLINIC_STATE_KEY: update[FORM_STATE_KEY],
        CLINIC_ZIP_KEY: update[FORM_ZIP_KEY],
        CLINIC_WEBSITE_KEY: update[FORM_WEBSITE_KEY],
        FORM_APPROVED_KEY: update[FORM_APPROVED_KEY],
        FORM_REVIEW_KEY: update[FORM_REVIEW_KEY],
        FORM_PROCESSED_KEY: update[FORM_PROCESSED_KEY],
        FORM_NOTES_KEY: update[FORM_NOTES_KEY],
    }


def get_clinic_updates():
    """Downloads the update data from Google Sheets"""
    worksheet = get_worksheet(GOOGLE_SHEET_ID_UPDATE, FORM_SHEET_NAME)
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

    for idx, c in enumerate(clinics):
        if c[CLINIC_ID_KEY] == clinic_id and c[CLINIC_NAME_KEY] == clinic_name:
            return (idx, c)
    return False


def merge_clinics(clinics, updates):
    delete_rows = []

    for update_index, update in enumerate(updates):
        keep_update_row = False
        update_as_clinic = translate_update_to_clinic(update)

        row = find_valid_clinic(clinics, update_as_clinic)
        if row:
            print(
                "Updating name={}, id={}".format(
                    update_as_clinic[CLINIC_NAME_KEY],
                    update_as_clinic[CLINIC_ID_KEY],
                )
            )
            row_index, clinic = row
            # add two to the row_index to account for the 1-base and the header
            row_keep, row_modified = update_clinic(
                row_index + 2, clinic, update_as_clinic
            )
            
        else:
            print(
                "Failed to update name={}, id={} mismatch".format(
                    update_as_clinic[CLINIC_NAME_KEY],
                    update_as_clinic[CLINIC_ID_KEY],
                )
            )
        # if we should not keep the row, mark it for deletion
        if not row_keep:
            delete_rows.insert(0, update_index)
        # if we should keep the row, but it's modified, mark completed
        elif row_modified:
            mark_completed(update_index)
    print(delete_rows)
    # delete from the back to the front
    for row in delete_rows:
        delete_form_submit(row)
        

def mark_completed(update_index):
    worksheet = get_worksheet(GOOGLE_SHEET_ID_UPDATE, FORM_SHEET_NAME)
    column_headers = get_columns(worksheet)
    # finding the right column index from our headers
    col = column_headers.index(FORM_PROCESSED_KEY) + 1

    # translating a list index (0-based) into a spreadsheet index (1-based + header)
    row = update_index + 2 
    worksheet.update_cell(row, col, "Yes")

    
def clinic_to_row(keys, clinic):
    """Transforms a clinic object into an array with the proper ordering"""
    row = []
    for key in keys:
        val = ""
        if key in clinic:
            if is_integer(clinic[key]):
                val = int(clinic[key])
            elif is_float(clinic[key]):
                val = float(clinic[key])
            else:
                val = clinic[key]

        row.append(val)
    return row


def delete_form_submit(idx):
    worksheet = get_worksheet(GOOGLE_SHEET_ID_UPDATE, FORM_SHEET_NAME)

    # delete the index + 2 to account for the header and one-indexed row
    worksheet.delete_rows(idx + 2)


def update_clinic(row, clinic, clinic_update):
    """Update in gsheets, this uses the earlier list of clinics to avoid many duplicate calls"""
    worksheet = get_worksheet(GOOGLE_SHEET_ID_PRIMARY, PROVIDER_SHEET_NAME)

    APPROVAL_REQUIRED_LIST = [FORM_NOTES_KEY, CLINIC_ADDRESS_KEY, CLINIC_CITY_KEY, CLINIC_ZIP_KEY]

    keys = get_columns(worksheet)
    modified = False
    keep_update_row = False

    # 4 cases: (approval req / not, script processed / not)
    #   - approval, processed:        process approved list fields, delete the row
    #   - no approval, processed      wait to process approve list fields, keep the row
    #   - approval, not processed     process all fields, delete the row
    #   - no approval, not processed  process generic fields, keep the row
    print(clinic_update)
    for (key, val) in clinic_update.items():
        # if there isn't a matching field or it's empty, continue
        if val == "" or key not in keys:
            continue

        # approval required, but not given, keep the row
        if key in APPROVAL_REQUIRED_LIST and clinic_update[FORM_REVIEW_KEY] == "No":
            keep_update_row = True
            continue

        # we've already processed these updates, so just continue
        if (
            key not in APPROVAL_REQUIRED_LIST
            and clinic_update[FORM_PROCESSED_KEY] == "Yes"
        ):
            continue

        # update some value
        if clinic[key] != clinic_update[key]:
            clinic[key] = clinic_update[key]
            modified = True

    # if the data has been modified, we update the provider entries
    if modified:
        worksheet.update("A{}".format(row), [clinic_to_row(keys, clinic)])

    # return whether to keep the update row, and whether we've modified the provider entires
    return keep_update_row, modified
    

def get_clinics():
    """Downloads the merged data from Google Sheets"""
    worksheet = get_worksheet(GOOGLE_SHEET_ID_PRIMARY, PROVIDER_SHEET_NAME)
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

    print("Found: {} clinics to update".format(len(clinic_updates)))

    merge_clinics(clinics, clinic_updates)

    # # hide any approved hidden value within two weeks
    # print("Hiding approved hidden values...")
    # supply_updates = get_unavailable_clinic_info()
    # remove_unavailable_clinics(clinics, supply_updates)
