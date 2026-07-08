import pandas as pd

from config_loader import get_excel_reader_config


# =====================================================
# TRANSACTION KEYWORDS
# =====================================================

TRANSACTION_KEYWORDS = [

    "voucher",

    "debit",

    "credit",

    "amount",

    "balance",

    "transaction",

    "journal",

    "posting",

    "entry",

    "date",

    "dr",

    "cr",

    "ledger",

    "narration"
]


# =====================================================
# NON-TRANSACTION KEYWORDS
# =====================================================

NON_TRANSACTION_KEYWORDS = [

    "account type",

    "opening balance",

    "parent account",

    "group",

    "subcategory",

    "mapping",

    "foreign key",

    "lookup",

    "master",

    "chart of accounts"
]


# =====================================================
# READ EXCEL TOOL
# =====================================================

def read_excel_tool(filepath):

    print("\nREADING EXCEL FILE...\n")

    try:

        excel_config = get_excel_reader_config()

        transaction_keywords = excel_config.get(
            "transaction_keywords",
            TRANSACTION_KEYWORDS
        )

        non_transaction_keywords = excel_config.get(
            "non_transaction_keywords",
            NON_TRANSACTION_KEYWORDS
        )

        # =============================================
        # READ ALL SHEETS
        # =============================================

        excel_file = pd.ExcelFile(filepath)

        sheet_names = excel_file.sheet_names

        print("\nAVAILABLE SHEETS:\n")

        print(sheet_names)

        best_sheet = None

        best_score = -999999

        best_df = None

        # =============================================
        # CHECK EACH SHEET
        # =============================================

        for sheet in sheet_names:

            print(f"\nCHECKING SHEET: {sheet}")

            try:

                df = pd.read_excel(

                    filepath,

                    sheet_name=sheet
                )

                # =====================================
                # EMPTY SHEET CHECK
                # =====================================

                if df.empty:

                    print(
                        "\nEMPTY SHEET SKIPPED\n"
                    )

                    continue

                # =====================================
                # LOWERCASE COLUMNS
                # =====================================

                columns = [

                    str(col).lower().strip()

                    for col in df.columns
                ]

                print("\nCOLUMNS:\n")

                print(columns)

                # =====================================
                # START SCORE
                # =====================================

                score = 0

                # =====================================
                # POSITIVE SCORE
                # =====================================

                for keyword in transaction_keywords:

                    for col in columns:

                        if keyword in col:

                            score += 3

                # =====================================
                # NEGATIVE SCORE
                # =====================================

                for keyword in non_transaction_keywords:

                    for col in columns:

                        if keyword in col:

                            score -= 5

                # =====================================
                # BONUS:
                # NUMERIC COLUMNS
                # =====================================

                numeric_columns = df.select_dtypes(
                    include=["number"]
                ).columns

                score += len(numeric_columns)

                # =====================================
                # BONUS:
                # LARGE ROW COUNT
                # =====================================

                if len(df) > 20:

                    score += 10

                # =====================================
                # BONUS:
                # HAS BOTH DEBIT + CREDIT
                # =====================================

                has_debit = any(
                    "debit" in col or "dr" == col
                    for col in columns
                )

                has_credit = any(
                    "credit" in col or "cr" == col
                    for col in columns
                )

                if has_debit and has_credit:

                    score += 20

                # =====================================
                # PRINT SCORE
                # =====================================

                print(

                    f"\nSHEET SCORE: {score}"
                )

                # =====================================
                # BEST SHEET
                # =====================================

                if score > best_score:

                    best_score = score

                    best_sheet = sheet

                    best_df = df

            except Exception as e:

                print(

                    f"\nERROR READING "
                    f"SHEET {sheet}\n"
                )

                print(e)

        # =============================================
        # NO VALID SHEET
        # =============================================

        if best_df is None:

            print(

                "\nNO FINANCIAL "
                "TRANSACTION SHEET FOUND\n"
            )

            return None

        # =============================================
        # FINAL RESULT
        # =============================================

        print(

            f"\nSELECTED SHEET: "
            f"{best_sheet}"
        )

        print(

            f"\nBEST SCORE: "
            f"{best_score}"
        )

        print(

            "\nFINAL SELECTED COLUMNS:\n"
        )

        print(best_df.columns.tolist())

        print(

            f"\nTOTAL ROWS: "
            f"{len(best_df)}"
        )

        return best_df

    except Exception as e:

        print(

            "\nEXCEL READER ERROR\n"
        )

        print(e)

        return None
