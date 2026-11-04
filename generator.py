# audit-data-lab project.
# GitHub @ismailelqara / Linkedin @Ismail EL QARA
# generator.py 

import numpy as np
import pandas as pd
from faker import Faker
import config

#1 ENVIRONMENT AND CONFIGURATION SETUP

SEED = getattr(config, "SEED", 42) #Seafty Measure: Default to 42 if not set in config.py
rng = np.random.default_rng(SEED) #rng: Numpy random generator with fix SEED 
fake = Faker()
Faker.seed(SEED) #fix the seed for Faker 

#2 DATA GENERATION SETUP

NUM_SUPPLIERS = getattr(config, "NUM_SUPPLIERS", 50) 
APPROVAL_THRESHOLD = getattr(config, "APPROVAL_THRESHOLD", 10_000)  
ANOMALY_RATE = getattr(config, "ANOMALY_RATE", 0.02)
REF_DATE = pd.Timestamp(getattr(config, "REFERENCE_DATE", "2026-10-30"))  #Genrate invoice with dates up to this refernce date #Le 30/10 est le max date
NUM_INVOICES = getattr(config, "NUM_INVOICES", 1000)
APPROVERS = ["I. EL QARA", "Y. EL JAZOULI", "K. Idrissi", "M. Tazi"] #Name of approvers for the invoices

CURRENCIES = ["MAD", "EUR", "USD"]
CURRENCY_WEIGHTS = [0.85, 0.10, 0.05] #Percentage to see CURRENCIES in DATA 85% , 10% , 5%
FX_TO_MAD = {"MAD": 1.0, "EUR": 10.95, "USD": 9.77}  #Updated by Author 04/11/2026

#NV
DATA_COLS = ["Invoice_ID", "Date", "Supplier_Name", "Amount", "Currency",
             "Amount_MAD", "PO_Number", "Approver"]
KEY_COLS = ["Invoice_ID", "Anomaly_Type", "Related_Invoice_ID"]

#3 UNIQUE GENERATE COMPANY NAMES WITH Faker

def _unique_companies(k): #k: numbers of companies to generate
    names = {} #Dictionary to store compnay names as keys لا تقبل التكرار
    while len(names) < k: #While loop create unique company names until we reach k
        names[fake.company()] = None #Generate company name and store it as key in names dictionary
    return list(names) 

#4 GENERATE INVOICES

def generate_invoices():
    n = NUM_INVOICES #Stock the number of invoices to generate in n
    suppliers = _unique_companies(NUM_SUPPLIERS) #Call the function to generate unique company names and store them in suppliers list
    w = 1 / np.arange(1, NUM_SUPPLIERS + 1)
    w /= w.sum()
    days = pd.bdate_range(REF_DATE - pd.Timedelta(days=365), REF_DATE) #Business days range from REF_DATE - 365 days to REF_DATE

        # Generate Amount and Currency first, so we can check them against the threshold
    amount = np.round(rng.lognormal(7.5, 2.0, n), 2)
    currency = rng.choice(CURRENCIES, n, p=CURRENCY_WEIGHTS)

    # Push "clean" invoices out of the 90%-100% band below the threshold,
    # so only injected Below_Threshold rows live there
    fx = np.array([FX_TO_MAD[c] for c in currency])
    band = (amount * fx >= 0.9 * APPROVAL_THRESHOLD) & (amount * fx < APPROVAL_THRESHOLD)
    amount[band] = np.round(amount[band] * 1.15, 2)

    return pd.DataFrame({
        "Invoice_ID": [f"TMP-{j:05d}" for j in range(1, n + 1)],
        "Date": days[rng.integers(0, len(days), n)],
        "Supplier_Name": rng.choice(suppliers, n, p=w),
        "Amount": amount,
        "Currency": currency,
        "PO_Number": [f"PO-{x}" for x in rng.integers(10000, 99999, n)],
        "Approver": rng.choice(APPROVERS, n),
        "Related_Invoice_ID": "",
        "Anomaly_Type": "None",
    })

#5 INJECT ANOMALES

def inject_anomalies(df):
    n, T = len(df), APPROVAL_THRESHOLD #Call the number of invoices and the approval T=10000
    k = max(1, int(n * ANOMALY_RATE)) #2%
    if 6 * k > n: #Six type of anomalies
        raise ValueError("ANOMALY_RATE too high for the number of invoices generated. Reduce ANOMALY_RATE or increase NUM_INVOICES.")

    idx = rng.permutation(n) #Mix the index of the invoices to inject anomalies randomly
    part = lambda j: idx[j * k:(j + 1) * k]

    # 1) Bellow threshold: Amount < T, Currency = MAD (9el mn 10000 b MAD)
    i0 = part(0)
    df.loc[i0, "Currency"] = "MAD"
    df.loc[i0, "Amount"] = np.round(T - rng.uniform(1, max(2, 0.02 * T), k), 2)
    df.loc[i0, "Anomaly_Type"] = "Below_Threshold"

    # 2) Round amount (rj3ha des nbr reel)
    i1 = part(1)
    # Round to ONE significant digit (1,800 -> 2,000 | 43,500 -> 40,000)
    # Round to ONE significant digit (1,800 -> 2,000 | 43,500 -> 40,000)
    x = df.loc[i1, "Amount"].clip(lower=1000).to_numpy()
    mag = 10 ** np.floor(np.log10(x))
    df.loc[i1, "Amount"] = np.round(np.round(x / mag) * mag, 2)
    df.loc[i1, "Anomaly_Type"] = "Round_Amount"

    # 3) Weekend (ykunu des factures f weekend)
    i2 = part(2)
    back = df.loc[i2, "Date"].dt.weekday.to_numpy() + 1 + rng.integers(0, 2, k)
    df.loc[i2, "Date"] = df.loc[i2, "Date"] - pd.to_timedelta(back, unit="D")
    df.loc[i2, "Anomaly_Type"] = "Weekend"

    # 4)  No OP (Dok les commandes w les achats li ma3ndhumch une facture legal)
    i3 = part(3)
    df.loc[i3, "PO_Number"] = ""
    df.loc[i3, "Anomaly_Type"] = "No_PO"

    # 5) Split (Related IDs li endhom plus 2 factures f systeme)
    i4 = part(4)
    df.loc[i4, "Currency"] = "MAD"
    df.loc[i4, "Amount"] = np.round(rng.uniform(0.55, 0.95, k) * T, 2)
    df.loc[i4, "Anomaly_Type"] = "Split"
    twin = df.loc[i4].copy()
    twin["Invoice_ID"] = [f"TMP-S{j:05d}" for j in range(k)]       
    twin["Amount"] = np.round(rng.uniform(0.55, 0.95, k) * T, 2)
    twin["Related_Invoice_ID"] = df.loc[i4, "Invoice_ID"].values   

    # 6) Duplicate (Related IDs li endhom plus 2 factures f systeme)
    i5 = part(5)
    dup = df.loc[i5].copy()
    dup["Invoice_ID"] = [f"TMP-D{j:05d}" for j in range(k)]
    dup["Related_Invoice_ID"] = df.loc[i5, "Invoice_ID"].values
    d = np.busday_offset(dup["Date"].values.astype("datetime64[D]"),
                         rng.integers(1, 4, k), roll="forward")
    d = np.minimum(d, REF_DATE.to_datetime64().astype("datetime64[D]"))
    dup["Date"] = pd.to_datetime(d)
    dup["Anomaly_Type"] = "Duplicate"

    out = pd.concat([df, twin, dup], ignore_index=True)
    # Random tie-break so duplicates are not always placed right after their originals
    out["_tie"] = rng.random(len(out))
    out = out.sort_values(["Date", "_tie"]).drop(columns="_tie").reset_index(drop=True)

    # Reassign Invoice_IDs to ensure uniqueness and maintain the correct mapping for Related_Invoice_IDs
    new_ids = [f"INV-{j:05d}" for j in range(1, len(out) + 1)]
    mapping = dict(zip(out["Invoice_ID"], new_ids))
    out["Related_Invoice_ID"] = out["Related_Invoice_ID"].map(mapping).fillna("")
    out["Invoice_ID"] = new_ids

    # Add a new column for Amount in MAD (Moroccan Dirham) based on the currency and FX rates
    out["Amount_MAD"] = np.round(out["Amount"] * out["Currency"].map(FX_TO_MAD), 2)
    return out

#6 SANITY CHECKS

def sanity_checks(df): #Control the generated data
    assert df["Invoice_ID"].is_unique, "Duplicate invoice IDs found" #Everything is unique in Invoice_ID column
    rel = df.loc[df["Related_Invoice_ID"] != "", "Related_Invoice_ID"] #Save in rel the where invoices have RII not empty
    assert rel.isin(df["Invoice_ID"]).all(), "Invalid related invoice IDs found"
    assert (df["Date"] <= REF_DATE).all(), "Invoices with future dates found"
    bt = df[df["Anomaly_Type"] == "Below_Threshold"]
    assert (bt["Amount_MAD"] < APPROVAL_THRESHOLD).all(), "Error: Below_Threshold invoices with Amount exceeds limit"

#7 FUNCTION USED BY THE INTERACTIVE APP (Streamlit)

def build_dataset(n=1000, n_suppliers=50, threshold=10_000, anomaly_rate=0.02,
                  seed=42, currency_weights=(0.85, 0.10, 0.05)):
    global rng, fake, NUM_INVOICES, NUM_SUPPLIERS, APPROVAL_THRESHOLD
    global ANOMALY_RATE, CURRENCY_WEIGHTS

    NUM_INVOICES = n
    NUM_SUPPLIERS = n_suppliers
    APPROVAL_THRESHOLD = threshold
    ANOMALY_RATE = anomaly_rate
    cw = np.array(currency_weights, dtype=float)
    CURRENCY_WEIGHTS = list(cw / cw.sum())

    rng = np.random.default_rng(seed)
    Faker.seed(seed)
    fake = Faker()

    df = inject_anomalies(generate_invoices())
    sanity_checks(df)
    return df[DATA_COLS].copy(), df[KEY_COLS].copy()

#8 MAIN EXECUTION

if __name__ == "__main__":
    df = inject_anomalies(generate_invoices())
    sanity_checks(df)

    df[DATA_COLS].to_csv("invoices.csv", index=False)
    df[KEY_COLS].to_csv("answer_key.csv", index=False)

    print(df[DATA_COLS].head(10))
    print("\n--- Anomaly Type Distribution ---")
    print(df["Anomaly_Type"].value_counts())
    print(f"\n INVOICES GENERATED: {len(df)} : invoices.csv + answer_key.csv")

