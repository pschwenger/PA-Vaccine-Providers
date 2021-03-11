import gspread
import time
from gspread.exceptions import APIError
from google.oauth2.service_account import (
    Credentials as ServiceAccountCredentials,
)

WORKSHEET_CACHE = {}
WORKSHEET_COLUMN_CACHE = {}

DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# Taken from gspread source, this client will retry if it hits a
# rate limiting error
class RetryingClient(gspread.Client):
    HTTP_TOO_MANY_REQUESTS = 429
    DEFAULT_SLEEP_SECONDS = 100

    def request(self, *args, **kwargs):
        try:
            return super().request(*args, **kwargs)
        except APIError as err:
            data = err.response.json()

            if data["error"]["code"] == self.HTTP_TOO_MANY_REQUESTS:
                print("ERROR: rate limit hit... pausing...")
                time.sleep(self.DEFAULT_SLEEP_SECONDS)
                print("Resuming...")
                return self.request(*args, **kwargs)
            else:
                raise err


def get_service_account():
    creds = ServiceAccountCredentials.from_service_account_file(
        "service_account.json", scopes=DEFAULT_SCOPES
    )
    return RetryingClient(auth=creds)


def get_worksheet(sheet_id, sheet_name):
    """Returns a worksheet by ID and name from cache"""
    if (sheet_id, sheet_name) in WORKSHEET_CACHE:
        return WORKSHEET_CACHE[(sheet_id, sheet_name)]

    sheet = get_spreadsheet(sheet_id)
    worksheet = sheet.worksheet(sheet_name)

    WORKSHEET_CACHE[(sheet_id, sheet_name)] = worksheet
    return worksheet


def get_spreadsheet(sheet_id):
    """Returns a spreadsheet"""
    gc = get_service_account()
    sheet = gc.open_by_key(sheet_id)
    return sheet


def get_columns(worksheet):
    """Returns the columns from the worksheet"""
    if worksheet.id in WORKSHEET_COLUMN_CACHE:
        return list(WORKSHEET_COLUMN_CACHE[worksheet.id])

    columns = worksheet.row_values(1)
    WORKSHEET_COLUMN_CACHE[worksheet.id] = columns

    return list(columns)


def is_integer(n):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()


def is_float(n):
    try:
        float(n)
        return True
    except ValueError:
        return False
