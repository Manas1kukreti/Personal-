import pandas as pd

from config_loader import get_relation_mapping_config


# =====================================================
# RELATION CONFIG
# =====================================================

RELATION_CONFIG = {

    "account_key": {

        "sheet": "Chart of Accounts",

        "lookup_column": "account_key",

        "fields": [

            "account",
            "subaccount",
            "class",
            "subclass"
        ]
    },

    "territory_key": {

        "sheet": "Territory",

        "lookup_column": "territory_key",

        "fields": [

            "country",
            "region"
        ]
    }
}


# =====================================================
# RELATION MAPPER TOOL
# =====================================================

def relation_mapper_tool(df, filepath):

    print("\nSTARTING RELATIONAL MAPPING...\n")

    try:

        relation_config = (
            get_relation_mapping_config()
            or RELATION_CONFIG
        )

        for foreign_key, config in relation_config.items():

            print(f"\nPROCESSING: {foreign_key}")

            if foreign_key not in df.columns:

                print(f"{foreign_key} NOT FOUND")

                continue

            lookup_df = pd.read_excel(

                filepath,

                sheet_name=config["sheet"]
            )

            lookup_df.columns = [

                str(col).strip().lower()

                for col in lookup_df.columns
            ]

            lookup_column = config["lookup_column"]

            fields = config.get(
                "fields",
                []
            )

            if isinstance(fields, dict):

                field_items = fields.items()

            else:

                field_items = [

                    (field, field)
                    for field in fields
                ]

            for field, final_field in field_items:

                if field not in lookup_df.columns:

                    continue

                print(f"MAPPING FIELD: {field}")

                field_map = dict(

                    zip(

                        lookup_df[lookup_column],

                        lookup_df[field]
                    )
                )

                df[final_field] = (

                    df[foreign_key]
                    .map(field_map)
                )

        print("\nRELATIONAL MAPPING COMPLETED\n")

        print(df.columns.tolist())

        return df

    except Exception as e:

        print("\nRELATION MAPPER ERROR\n")

        print(e)

        return df
