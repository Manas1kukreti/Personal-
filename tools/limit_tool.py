def limit_rows_tool(df, limit=14):

    print(f"\nLIMITING DATA TO FIRST {limit} ROWS...\n")

    limited_df = df.head(limit)

    print("ROWS AFTER LIMIT:", len(limited_df))

    return limited_df