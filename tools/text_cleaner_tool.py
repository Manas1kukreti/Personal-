def clean_dataframe_tool(df):

    print("\nCLEANING DATAFRAME...\n")

    # remove extra spaces
    df.columns = [

        str(col).strip()

        for col in df.columns
    ]

    # replace NaN with empty string
    df = df.fillna("")

    print("DATA CLEANING COMPLETED")

    return df