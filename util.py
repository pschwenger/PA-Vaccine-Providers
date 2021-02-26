import gspread


def get_service_account():
    return gspread.service_account(filename="./service_account.json")