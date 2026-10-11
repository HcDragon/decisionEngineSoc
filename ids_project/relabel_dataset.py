"""Rebuild the training dataset from the raw per-attack CSVs with corrected labels.

Why: each raw capture file labels EVERY flow recorded during an attack window
with that attack's name, including ordinary background traffic from other
devices. Only flows that have the attacking machine as an endpoint are the
attack; the rest are benign and are relabelled as such here.

Four classes are dropped (DoS DNS/ICMP/UDP Flood, Recon Host Discovery): the
raw files are TCP-only, so those captures contain no attack flows at all, only
background traffic. Their rows are kept as Benign Traffic.

Recon OS Scan and Recon Ping Sweep are merged into "Recon Scan": as TCP flows
both are the same single-SYN nmap probes and cannot be told apart (52% when
tried), except by the fixed source port nmap happened to use in each capture.

Raw files (with Src IP / Dst IP) are in the parent repo's history:
  git show "15cb674:ids_project/dataset/<name>.csv"

Run: python relabel_dataset.py <raw_dir>
"""
import glob
import os
import sys

import pandas as pd

OUT_PATH = "dataset/relabeled_ids_dataset.csv"
BENIGN = "Benign Traffic"
LAN = "192.168.1."
ID_COLS = ["Flow ID", "Src IP", "Dst IP", "Timestamp"]

RENAME = {"Recon OS Scan": "Recon Scan", "Recon Ping Sweep": "Recon Scan"}

# attack -> (attacker IPs, victim must be on the LAN)
ATTACKS = {
    "Dictionary Brute Force": ({"192.168.1.45"}, True),
    "Recon OS Scan": ({"192.168.1.45"}, True),
    "Recon Ping Sweep": ({"192.168.1.45"}, True),
    # flood packets carry random (spoofed) remote addresses, so no LAN filter
    "DoS SYN Flood": ({"192.168.1.133", "192.168.1.21", "192.168.1.25"}, False),
    # the MITM host re-originates intercepted sessions to internet servers
    "MITM ARP Spoofing": ({"192.168.1.45"}, False),
}


def relabel(df, attack):
    if attack not in ATTACKS:
        return pd.Series(BENIGN, index=df.index)
    attackers, lan_only = ATTACKS[attack]
    src_att = df["Src IP"].isin(attackers)
    dst_att = df["Dst IP"].isin(attackers)
    is_attack = src_att | dst_att
    if lan_only:
        peer = df["Dst IP"].where(src_att, df["Src IP"])
        is_attack &= peer.str.startswith(LAN)
    return pd.Series(BENIGN, index=df.index).where(~is_attack, RENAME.get(attack, attack))


def main(raw_dir):
    frames = []
    for path in sorted(glob.glob(os.path.join(raw_dir, "*.csv"))):
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()
        original = df["Attack Name"].iloc[0]
        df["Attack Name"] = relabel(df, original)
        kept = int((df["Attack Name"] != BENIGN).sum())
        print(f"{original:<24} {len(df):>6} rows -> {kept:>6} attack, "
              f"{len(df) - kept:>6} benign")
        frames.append(df.drop(columns=ID_COLS))

    out = pd.concat(frames, ignore_index=True)
    out["Label"] = (out["Attack Name"] != BENIGN).astype(int)
    out.to_csv(OUT_PATH, index=False)
    print(f"\nWrote {len(out):,} rows to {OUT_PATH}")
    print(out["Attack Name"].value_counts().to_string())


if __name__ == "__main__":
    main(sys.argv[1])
