import os, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, seaborn as sns
from scipy import stats

RAW = "/mnt/user-data/uploads/DataCoSupplyChainDataset.csv"
ROOT = "/home/claude/work/reports"
sns.set_theme(style="whitegrid", context="notebook")
plt.rcParams.update({"figure.dpi": 100, "savefig.dpi": 200, "axes.titleweight": "bold",
                     "axes.titlesize": 12, "axes.labelsize": 10})
C1, C2, C3 = "#1f4e79", "#c0392b", "#7f8c8d"
MIN_N = 100          # minimum orders (or lines) to rank a group
MIN_N_MULTI = 50     # minimum for multi-dimensional cells


def folder(*parts):
    p = os.path.join(ROOT, *parts); os.makedirs(p, exist_ok=True); return p


def save(fig, d, name):
    fig.tight_layout(); fig.savefig(os.path.join(d, name), bbox_inches="tight"); plt.close(fig)


def wilson(k, n, z=1.96):
    k = np.asarray(k, float); n = np.asarray(n, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = k / n; den = 1 + z**2 / n
        c = (p + z**2 / (2 * n)) / den
        h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return c - h, c + h


def rate_table(d, by, min_n=1, target="late"):
    """late rate per group with Wilson 95% CI (d is one row per analysis unit)."""
    g = d.groupby(by, observed=True)[target].agg(n="size", late="sum").reset_index()
    g["late_rate_%"] = (g["late"] / g["n"] * 100).round(2)
    lo, hi = wilson(g["late"], g["n"])
    g["ci95_low_%"] = (lo * 100).round(2); g["ci95_high_%"] = (hi * 100).round(2)
    g["n_sufficient"] = g["n"] >= min_n
    return g


def chi2_v(d, col, target="late"):
    ct = pd.crosstab(d[col], d[target])
    ct = ct[ct.sum(axis=1) > 0]
    if ct.shape[0] < 2 or ct.shape[1] < 2: return np.nan, np.nan, np.nan, np.nan
    chi, p, dof, _ = stats.chi2_contingency(ct)
    n = ct.values.sum(); k = min(ct.shape) - 1
    v = np.sqrt(chi / (n * k)) if k > 0 else np.nan
    return chi, p, dof, v


def v_label(v):
    if np.isnan(v): return "n/a"
    return "negligible" if v < .05 else "weak" if v < .10 else "moderate" if v < .30 else "strong"


def bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p); r = np.empty(n)
    q = p[o] * n / (np.arange(n) + 1); q = np.minimum.accumulate(q[::-1])[::-1]
    r[o] = np.minimum(q, 1); return r


def md(df, floatfmt=".2f", index=False):
    return df.to_markdown(index=index, floatfmt=floatfmt)


class Report:
    def __init__(self, d, title):
        self.d = d; self.parts = [f"# {title}\n"]
    def sec(self, h, body): self.parts.append(f"\n## {h}\n\n{body}\n")
    def fig(self, name, cap=""): self.parts.append(f"\n![{cap}]({name})\n*{cap}*\n")
    def table(self, df, csv=None, floatfmt=".2f", maxrows=25):
        if csv: df.to_csv(os.path.join(self.d, csv), index=False)
        self.parts.append("\n" + md(df.head(maxrows), floatfmt) + (f"\n\n*(showing {maxrows} of {len(df)} rows; full table in `{csv}`)*\n" if csv and len(df) > maxrows else "\n"))
    def save(self, fname="report.md"):
        open(os.path.join(self.d, fname), "w", encoding="utf-8").write("\n".join(self.parts))


def load_orders():
    return pd.read_pickle("/home/claude/work/orders.pkl"), pd.read_pickle("/home/claude/work/lines.pkl")
