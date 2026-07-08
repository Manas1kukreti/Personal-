import pandas as pd

from config_loader import get_financial_logic_config


# =====================================================
# FINANCIAL LOGIC TOOL
# =====================================================
# PURPOSE:
# Intelligent Debit / Credit Identification using:
#
# 1. Business Rules (Highest Priority)
# 2. Account Subclass
# 3. Keyword Intelligence
# 4. Amount Sign Fallback
# ALSO HANDLES:
# - Bracket amounts:
#     (5000) → -5000
#
# - Voucher balancing logic
#
# - Real-world accounting behavior
# =====================================================



# =====================================================
# BUSINESS TRANSACTION RULES
# =====================================================
# MOST IMPORTANT LAYER
#
# THESE RULES OVERRIDE EVERYTHING
# =====================================================

BUSINESS_RULES = {

    # =============================================
    # COST OF SALES
    # =============================================

    ("cost of sales", "inventory"): "credit",

    ("cost of sales", "cost of sales"): "debit",

    # =============================================
    # CREDIT SALES
    # =============================================

    ("credit sales", "sales"): "credit",

    ("credit sales", "trade receivables"): "debit",

    ("credit sales", "receivables"): "debit",

    # =============================================
    # CASH SALES
    # =============================================

    ("cash sales", "sales"): "credit",

    ("cash sales", "cash at bank"): "debit",

    ("cash sales", "cash & cash equivalents"): "debit",

    # =============================================
    # CREDIT EXPENSES
    # =============================================

    ("credit expenses", "advertisements"): "debit",

    ("credit expenses", "accrued expenses"): "credit",

    ("credit expenses", "other payables"): "credit"
}



# =====================================================
# SUBCLASS RULE MAPPING
# =====================================================

SUBCLASS_RULE = {

    # =============================================
    # ASSETS
    # =============================================

    "assets": "asset",

    # =============================================
    # LIABILITIES
    # =============================================

    "liabilities": "liability",

    "owners equity": "liability",

    # =============================================
    # INCOME
    # =============================================

    "sales": "income",

    "interest income": "income",

    "dividend income": "income",

    "gain/loss on sales of asset": "income",

    "exchange loss/gain": "income",

    # =============================================
    # EXPENSES
    # =============================================

    "cost of sales": "expense",

    "operating expenses": "expense",

    "depreciation & amortization": "expense",

    "interest expense": "expense",

    "taxation": "expense"
}



# =====================================================
# KEYWORD RULES
# =====================================================

KEYWORD_RULES = {

    "asset": [

        "cash",
        "bank",
        "receivable",
        "inventory",
        "prepaid",
        "equipment",
        "property",
        "land",
        "furniture",
        "vehicle",
        "investment"
    ],

    "liability": [

        "payable",
        "accrued",
        "loan",
        "equity",
        "capital",
        "retained earnings"
    ],

    "income": [

        "sales",
        "sale",
        "revenue",
        "income",
        "gain"
    ],

    "expense": [

        "expense",
        "cost of sales",
        "salary",
        "rent",
        "utilities",
        "advertisement",
        "travel",
        "depreciation",
        "tax"
    ]
}



# =====================================================
# PRIORITY ORDER
# =====================================================

RULE_PRIORITY = {

    "liability": 0,

    "asset": 1,

    "income": 2,

    "expense": 3
}


def get_business_rules():

    financial_config = get_financial_logic_config()

    configured_rules = financial_config.get(
        "business_rules",
        []
    )

    if not configured_rules:

        return BUSINESS_RULES

    rules = {}

    for rule in configured_rules:

        particulars = str(
            rule.get("particulars", "")
        ).lower().strip()

        target = str(
            rule.get("account_or_subaccount", "")
        ).lower().strip()

        if particulars and target:

            rules[(particulars, target)] = rule.get(
                "rule"
            )

    return rules or BUSINESS_RULES


def get_subclass_rules():

    financial_config = get_financial_logic_config()

    return financial_config.get(
        "subclass_rules",
        SUBCLASS_RULE
    )


def get_keyword_rules():

    financial_config = get_financial_logic_config()

    return financial_config.get(
        "keyword_rules",
        KEYWORD_RULES
    )


def get_rule_priority():

    financial_config = get_financial_logic_config()

    return financial_config.get(
        "rule_priority",
        RULE_PRIORITY
    )



# =====================================================
# CLEAN AMOUNT
# =====================================================

def clean_amount(value):

    if pd.isna(value):

        return 0.0

    value = str(value).strip()

    # =============================================
    # REMOVE COMMAS
    # =============================================

    value = value.replace(",", "")

    # =============================================
    # HANDLE BRACKET VALUES
    # (5000) → -5000
    # =============================================

    if value.startswith("(") and value.endswith(")"):

        value = "-" + value[1:-1]

    try:

        return float(value)

    except:

        return 0.0



# =====================================================
# BUSINESS RULE CHECKER
# =====================================================

def rule_from_business_logic(

    particulars,
    account,
    subaccount
):

    particulars = str(particulars).lower().strip()

    account = str(account).lower().strip()

    subaccount = str(subaccount).lower().strip()

    # =============================================
    # CHECK ACCOUNT
    # =============================================

    business_rules = get_business_rules()

    rule = business_rules.get(

        (particulars, account)
    )

    if rule:

        return rule

    # =============================================
    # CHECK SUBACCOUNT
    # =============================================

    rule = business_rules.get(

        (particulars, subaccount)
    )

    return rule



# =====================================================
# RULE FROM SUBCLASS
# =====================================================

def rule_from_subclass(subclass):

    if subclass is None:

        return None

    subclass = str(subclass).lower().strip()

    subclass_rules = get_subclass_rules()

    return subclass_rules.get(subclass)



# =====================================================
# RULE FROM KEYWORDS
# =====================================================

def rule_from_keywords(

    details,
    account,
    subaccount
):

    combined = (

        str(details) + " " +
        str(account) + " " +
        str(subaccount)

    ).lower()

    keyword_rules = get_keyword_rules()

    rule_priority = get_rule_priority()

    scores = {

        "asset": 0,
        "liability": 0,
        "income": 0,
        "expense": 0
    }

    # =============================================
    # CALCULATE SCORES
    # =============================================

    for rule_type, keywords in keyword_rules.items():

        for keyword in keywords:

            if keyword in combined:

                scores[rule_type] += 1

    # =============================================
    # NO MATCH FOUND
    # =============================================

    if max(scores.values()) == 0:

        return None

    # =============================================
    # FIND BEST SCORE
    # =============================================

    best_score = max(scores.values())

    candidates = [

        rule_type
        for rule_type, score in scores.items()
        if score == best_score
    ]

    # =============================================
    # TIE BREAKER
    # =============================================

    best_rule = min(

        candidates,

        key=lambda r: rule_priority.get(
            r,
            999
        )
    )

    return best_rule



# =====================================================
# APPLY ACCOUNTING RULE
# =====================================================

def apply_rule(

    amount,
    rule_type
):

    debit = ""

    credit = ""

    amount_abs = str(abs(amount))

    # =============================================
    # EXPLICIT DEBIT
    # =============================================

    if rule_type == "debit":

        debit = amount_abs

    # =============================================
    # EXPLICIT CREDIT
    # =============================================

    elif rule_type == "credit":

        credit = amount_abs

    # =============================================
    # ASSET
    # =============================================

    elif rule_type == "asset":

        if amount >= 0:

            debit = amount_abs

        else:

            credit = amount_abs

    # =============================================
    # LIABILITY / INCOME
    # =============================================

    elif rule_type in [

        "liability",
        "income"
    ]:

        if amount >= 0:

            credit = amount_abs

        else:

            debit = amount_abs

    # =============================================
    # EXPENSE
    # =============================================

    elif rule_type == "expense":

        if amount >= 0:

            debit = amount_abs

        else:

            credit = amount_abs

    # =============================================
    # SIGN FALLBACK
    # =============================================

    else:

        if amount >= 0:

            debit = amount_abs

        else:

            credit = amount_abs

    return debit, credit



# =====================================================
# DETERMINE DEBIT / CREDIT
# =====================================================

def determine_debit_credit(

    amount,
    subclass=None,
    details=None,
    account=None,
    subaccount=None
):

    # =============================================
    # TIER 1 → BUSINESS RULE
    # =============================================

    rule = rule_from_business_logic(

        details,
        account,
        subaccount
    )

    source = "business_rule"

    # =============================================
    # TIER 2 → SUBCLASS RULE
    # =============================================

    if rule is None:

        rule = rule_from_subclass(

            subclass
        )

        source = "subclass"

    # =============================================
    # TIER 3 → KEYWORD RULE
    # =============================================

    if rule is None:

        rule = rule_from_keywords(

            details,
            account,
            subaccount
        )

        source = "keyword"

    # =============================================
    # TIER 4 → SIGN FALLBACK
    # =============================================

    if rule is None:

        source = "sign_fallback"

    debit, credit = apply_rule(

        amount,
        rule
    )

    return debit, credit, source



# =====================================================
# MAIN FINANCIAL LOGIC TOOL
# =====================================================

def financial_logic_tool(df):

    print("\nAPPLYING FINANCIAL LOGIC...\n")

    # =============================================
    # SAFETY CHECK
    # =============================================

    if "amount" not in df.columns:

        print("\nAMOUNT COLUMN NOT FOUND\n")

        return df

    # =============================================
    # CLEAN AMOUNT
    # =============================================

    df["amount"] = df["amount"].apply(

        clean_amount
    )

    # =============================================
    # FINAL STORAGE
    # =============================================

    debit_list = []

    credit_list = []

    source_list = []

    # =============================================
    # PROCESS EACH ROW
    # =============================================

    for _, row in df.iterrows():

        amount = row.get(

            "amount",
            0
        )

        subclass = row.get(

            "account_subclass",
            ""
        )

        details = row.get(

            "particulars",
            ""
        )

        account = row.get(

            "account",
            ""
        )

        subaccount = row.get(

            "subaccount",
            ""
        )

        debit, credit, source = (

            determine_debit_credit(

                amount=amount,

                subclass=subclass,

                details=details,

                account=account,

                subaccount=subaccount
            )
        )

        debit_list.append(debit)

        credit_list.append(credit)

        source_list.append(source)

    # =============================================
    # FINAL COLUMNS
    # =============================================

    df["debit_amount"] = debit_list

    df["credit_amount"] = credit_list

    df["dr_cr_source"] = source_list

    # =============================================
    # PREVIEW
    # =============================================

    print("\nFINANCIAL LOGIC COMPLETED\n")

    preview_cols = [

        "voucher_number",

        "particulars",

        "account",

        "subaccount",

        "account_subclass",

        "amount",

        "debit_amount",

        "credit_amount",

        "dr_cr_source"
    ]

    preview_cols = [

        col for col in preview_cols

        if col in df.columns
    ]

    print(

        df[preview_cols]

        .head(20)

        .to_string(index=False)
    )

    print("\nSOURCE BREAKDOWN:\n")

    print(

        df["dr_cr_source"]

        .value_counts()

        .to_string()
    )

    return df
