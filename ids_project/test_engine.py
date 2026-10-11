"""Self-check: the engine's align+classify path scores well on HELD-OUT rows
(the same 20% test split train_model.py evaluates on, never seen in training),
and column-name drift (cicflowmeter-style snake_case) still aligns.

Run: python test_engine.py
"""
import pandas as pd
from sklearn.model_selection import train_test_split

import engine
from preprocess import DATASET_PATH, DROP_COLS


def test_alignment_handles_snake_case():
    # a canonical feature renamed the way cicflowmeter would emit it must still map
    row = {"tot_fwd_pkts": 7, "SYN Flag Cnt": 3, "Dst Port": 443}
    out = engine.align(row)
    assert out["Total Fwd Packet"] == 7.0
    assert out["SYN Flag Count"] == 3.0
    assert out["Dst Port"] == 443.0


def held_out_rows():
    # mirrors preprocess.load_and_preprocess up to the split (same seed)
    df = pd.read_csv(DATASET_PATH)
    df.columns = df.columns.str.strip()
    df = df.drop(columns=[c for c in DROP_COLS if c in df.columns])
    df = df.replace([float("inf"), float("-inf")], pd.NA).dropna().drop_duplicates()
    _, test = train_test_split(df, test_size=0.2, random_state=42,
                               stratify=df["Attack Name"])
    return test


def test_classifier_on_held_out_rows():
    sample = held_out_rows().sample(n=500, random_state=1)
    correct = 0
    for _, r in sample.iterrows():
        row = r.to_dict()
        actual = row.pop("Attack Name")
        pred, _ = engine.classify(row)
        correct += pred == actual
    acc = correct / len(sample)
    print(f"engine accuracy on 500 held-out rows: {acc:.1%}")
    assert acc > 0.9, f"accuracy {acc:.1%} too low — alignment likely broken"


if __name__ == "__main__":
    test_alignment_handles_snake_case()
    test_classifier_on_held_out_rows()
    print("OK")
