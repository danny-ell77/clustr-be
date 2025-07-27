from django.conf import settings

BASE_PATH = "clustr/data_exchange/tests/test_includes/fixtures/"

CSV_WITH_HEADERS = settings.BASE_DIR / BASE_PATH / "csv_file_with_headers.csv"
CSV_WITHOUT_HEADERS = settings.BASE_DIR / BASE_PATH / "csv_file_without_headers.csv"
EXCEL_WITH_HEADERS = settings.BASE_DIR / BASE_PATH / "excel_file_with_headers.xlsx"
EXCEL_WITHOUT_HEADERS = settings.BASE_DIR / BASE_PATH / "excel_file_without_headers.xlsx"
EXCEL_LEGACY_WITH_HEADERS = settings.BASE_DIR / BASE_PATH / "excel_file_legacy_with_headers.xls"
EXCEL_LEGACY_WITHOUT_HEADERS = settings.BASE_DIR / BASE_PATH / "excel_file_legacy_without_headers.xls"
