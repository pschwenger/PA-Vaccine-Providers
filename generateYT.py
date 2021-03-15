from config import GOOGLE_SHEET_ID_PRIMARY, PROVIDER_SHEET_NAME, GOOGLE_SHEET_ID_YT
from util import get_service_account, get_worksheet
import csv

SOURCE_SHEET = GOOGLE_SHEET_ID_PRIMARY
SOURCE_SHEET_NAME = PROVIDER_SHEET_NAME
OUTPUT_SHEET = GOOGLE_SHEET_ID_YT

# replace these with the columns you'd like to generate instead
COLUMNS = ["Clinic Name", "Clinic ID", "Street Address", "City", "State", "ZIP Code", "X", "Y", "Last Updated", "Clinic Website", "Prescreen or Appointment Web Address", "Clinic Phone", "Vaccine Appointments Available", "Walk-ins Accepted", "Sunday Hours", "Monday Hours", "Tuesday Hours", "Wednesday Hours", "Thursday Hours", "Friday Hours", "Saturday Hours"]


def download_source():
    worksheet = get_worksheet(SOURCE_SHEET, SOURCE_SHEET_NAME)
    rows = worksheet.get_all_values()
    return rows


def upload(contents):
    gc = get_service_account()
    gc.import_csv(OUTPUT_SHEET, contents)


def get_write_indexes(header, columns):
    """Generates an array of True/False values depending on whether
    the index should be written or not.
    """
    write_indexes = []
    for col in header:
        write_indexes.append(col in columns)
    return write_indexes


def generate_output_row(mask, row):
    output = []
    for (mask_val, row_val) in zip(mask, row):
        if mask_val:
            output.append(row_val)
    return output


def get_csv_string(rows, columns):
    header = rows[0]
    write_index = get_write_indexes(header, columns)
    temp_file = "tmp.csv"

    with open(temp_file, "w") as f:
        writer = csv.writer(f)
        for row in rows:
            output_row = generate_output_row(write_index, row)
            writer.writerow(output_row)

    with open(temp_file, "r") as f:
        output_str = f.read()
    output_str = output_str.replace('\r\n','\n')
    output_str = output_str.replace('\n\n','\n')
    return output_str


def main():
    print("Fetching rows...")
    rows = download_source()
    print("Found {} rows".format(len(rows)))

    print("Generating CSV string...")
    contents = get_csv_string(rows, COLUMNS)

    print("Uploading to the new spreadsheet...")
    upload(contents)


if __name__ == "__main__":
    main()
