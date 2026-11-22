from common import *
from sklearn.metrics import roc_auc_score, silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.feature_selection import mutual_info_classif
ov = pd.read_pickle("orders_valid_hist.pkl"); o, L = load_orders(); Lv = L[~L.canceled_ship].copy()
OV = ov.late.mean() * 100; NV = len(ov); y = ov.late.values
base = f"Unit: **order** (n = {NV:,} valid orders); overall late rate = **{OV:.2f}%**."
ov["noon"] = np.where(ov.hour >= 12, "12:00-23:59", "00:00-11:59"); ov["qgrp"] = pd.cut(ov.qty, [0, 2, 5, 10, 999], labels=["1-2", "3-5", "6-10", "11+"]); ov["vgrp"] = pd.qcut(ov.value, 4, labels=["Q1 low", "Q2", "Q3", "Q4 high"])
dv = ov.groupby("date").size().rename("day_vol"); ov = ov.join(dv, on="date"); ov["volgrp"] = pd.qcut(ov.day_vol, 3, labels=["Low-volume day", "Mid", "High-volume day"])
KEY = {}

# =============== PATTERN 14 ===============
D = folder("patterns", "correlation"); R = Report(D, "Pattern 14: Feature-correlation patterns")
ov["avg_price"] = ov.gross / ov.qty
num = ["sched", "qty", "items", "value", "gross", "discount", "disc_rate", "avg_price", "n_cat", "lat", "lon", "hour", "wd_n", "month"]
lab = {"sched": "scheduled_days", "qty": "total_qty", "items": "items", "value": "order_value", "gross": "gross_sales", "discount": "discount_amt", "disc_rate": "avg_discount_rate", "avg_price": "avg_unit_price", "n_cat": "n_categories", "lat": "cust_lat", "lon": "cust_lon", "hour": "hour", "wd_n": "weekday_no", "month": "month"}
X = ov[num].rename(columns=lab); pear = X.corr(); spear = X.corr(method="spearman")
cp = pd.Series({c: stats.pearsonr(X[c], y)[0] for c in X}); cs = pd.Series({c: stats.spearmanr(X[c], y)[0] for c in X})
pp = pd.Series({c: stats.pearsonr(X[c], y)[1] for c in X}); mi = mutual_info_classif(X.values, y, discrete_features=[c in ("scheduled_days", "items", "n_categories", "hour", "weekday_no", "month", "total_qty") for c in X], random_state=0)
CT = pd.DataFrame({"feature": X.columns, "Pearson vs late": cp.values, "Spearman vs late": cs.values, "p (Pearson)": pp.values, "Mutual information (nats)": mi}).sort_values("Mutual information (nats)", ascending=False)
CT["p_BH"] = bh(CT["p (Pearson)"].values)
R.sec("Definitions and data used", base + "\n\nInputs only (order-level): numeric order-creation fields. **Target-derived fields are excluded** (`Days for shipping (real)`, delay, `Delivery Status`, `Late_delivery_risk`). Profit fields excluded (post-sale). Customer latitude/longitude are customer residence. Correlation is not predictive importance or causation.")
R.sec("Correlation with the late flag (Pearson, Spearman, mutual information)", "Mutual information captures non-linear dependence (estimated with sklearn; random_state=0).\n"); R.table(CT, "target_correlations.csv", floatfmt=".4f")
hp = []
for i, a in enumerate(pear.columns):
    for b in pear.columns[i + 1:]:
        if abs(pear.loc[a, b]) >= .7 or abs(spear.loc[a, b]) >= .7: hp.append({"feature A": a, "feature B": b, "Pearson": pear.loc[a, b], "Spearman": spear.loc[a, b]})
HP = pd.DataFrame(hp).sort_values("Pearson", key=abs, ascending=False); R.sec("Redundant pairs (|r| >= 0.7)", ""); R.table(HP, "redundant_pairs.csv", floatfmt=".3f")
inv = np.linalg.inv(pear.values); vif = pd.Series(np.diag(inv), index=pear.columns).sort_values(ascending=False).rename("VIF").reset_index().rename(columns={"index": "feature"})
R.sec("Multicollinearity (VIF; values >10 indicate serious collinearity)", ""); R.table(vif, floatfmt=".2f")
R.sec("Categorical redundancy checks (exact)", "- `Order Customer Id` = `Customer Id` (100% of rows). `Category Id` = `Product Category Id`; `Order Item Cardprod Id` = `Product Card Id`; `Product Price` = `Order Item Product Price` (100%).\n- `Sales per customer` = `Order Item Total` (100%); `Benefit per order` = `Order Profit Per Order` (100%).\n- `Days for shipment (scheduled)` is a function of `Shipping Mode` (1 value per mode): keep one of the two.\n- `Department Id/Name` and `Category Id/Name` are 1:1 with their names.")
fig, ax = plt.subplots(figsize=(9, 7.5)); sns.heatmap(pear, annot=True, fmt=".2f", cmap="RdBu_r", center=0, vmin=-1, vmax=1, ax=ax, annot_kws={"size": 7}, cbar_kws={"label": "Pearson r"}); ax.set_title(f"Pearson correlation of order-level numeric inputs (n={NV:,})"); save(fig, D, "01_pearson_heatmap.png")
fig, ax = plt.subplots(figsize=(9, 7.5)); sns.heatmap(spear, annot=True, fmt=".2f", cmap="RdBu_r", center=0, vmin=-1, vmax=1, ax=ax, annot_kws={"size": 7}, cbar_kws={"label": "Spearman rho"}); ax.set_title(f"Spearman correlation of order-level numeric inputs (n={NV:,})"); save(fig, D, "02_spearman_heatmap.png")
fig, axs = plt.subplots(1, 3, figsize=(14, 4.2)); sm = ov.sample(8000, random_state=1)
axs[0].hexbin(ov.qty, ov.value.clip(upper=ov.value.quantile(.99)), gridsize=30, cmap="Blues", mincnt=1); axs[0].set_xlabel("Total quantity"); axs[0].set_ylabel("Order value"); axs[0].set_title("Quantity vs value")
axs[1].scatter(sm.gross, sm.value, s=3, alpha=.3, color=C1); axs[1].set_xlabel("Gross sales"); axs[1].set_ylabel("Net order value"); axs[1].set_title("Gross vs net value (redundancy)")
axs[2].scatter(sm.qty + np.random.default_rng(0).uniform(-.2, .2, len(sm)), sm["items"] + np.random.default_rng(1).uniform(-.2, .2, len(sm)), s=3, alpha=.3, color=C1); axs[2].set_xlabel("Total quantity"); axs[2].set_ylabel("Items (lines)"); axs[2].set_title("Quantity vs items (8,000-order sample)"); save(fig, D, "03_selected_scatter.png")
fig, ax = plt.subplots(figsize=(8, 5)); t = CT.set_index("feature"); w = .38; xx = np.arange(len(t)); ax.barh(xx - w / 2, t["Pearson vs late"], w, color=C1, label="Pearson"); ax.barh(xx + w / 2, t["Spearman vs late"], w, color=C3, label="Spearman"); ax.set_yticks(xx); ax.set_yticklabels(t.index, fontsize=8); ax.invert_yaxis(); ax.set_xlabel("Correlation with late flag"); ax.set_title("Input-feature correlation with late delivery"); ax.legend(); save(fig, D, "04_correlation_comparison.png")
for f, c in [("01_pearson_heatmap.png", "Pearson heatmap"), ("02_spearman_heatmap.png", "Spearman heatmap"), ("03_selected_scatter.png", "Selected scatter plots"), ("04_correlation_comparison.png", "Correlation with target")]: R.fig(f, c)
top = CT.iloc[0]
R.sec("Interpretation", f"- Strongest numeric signal by mutual information: `{top['feature']}` (MI {top['Mutual information (nats)']:.4f}; Pearson {top['Pearson vs late']:.3f}). `scheduled_days` is a proxy for shipping mode; `hour` carries signal only through Same Day orders (Patterns 2 and 9).\n- Quantity, value, discount and location variables correlate with late at |r| < 0.02.\n- Redundant: value/gross/discount; quantity/items; plus the exact duplicates listed. Drop duplicates before modelling.")
R.sec("Candidate ML features", "Keep `scheduled_days` OR `Shipping Mode`; keep one of `order_value` / `gross_sales`; drop exact duplicate columns. No numeric feature other than scheduled days/hour shows signal.")
R.sec("Limitations", "Linear and rank correlations on mostly weak variables; mutual information estimates have noise around 0.")
R.save(); KEY["corr"] = CT.head(6).to_dict("records")

# =============== PATTERN 15 ===============
D = folder("patterns", "multivariate"); R = Report(D, "Pattern 15: Multivariate patterns")
ov["pm"] = ov["mode"].map(ov.groupby("mode").late.mean()); Lv["pm"] = Lv["Shipping Mode"].map(Lv.groupby("Shipping Mode").late.mean())
R.sec("Definitions and data used", base + f"\n\nCombinations are tested **cell by cell against the late rate expected from shipping mode alone** (observed late count vs sum of mode rates; normal approximation; Benjamini-Hochberg across all cells of a combination). Cells with n < {MIN_N_MULTI} are not reported. Priority-based combinations are **unavailable** (no priority column).")
def combo(d, keys, name, fname, row, col, title, pmcol="pm", latecol="late", unit="orders"):
    g = d.groupby(keys, observed=True).agg(n=(latecol, "size"), late=(latecol, "sum"), exp=(pmcol, "sum"), v=(pmcol, lambda p: (p * (1 - p)).sum())).reset_index()
    g = g[g.n >= MIN_N_MULTI].copy(); g["late_rate_%"] = (g.late / g.n * 100).round(1); g["expected_%"] = (g.exp / g.n * 100).round(1)
    lo, hi = wilson(g.late, g.n); g["ci95_low_%"] = (lo * 100).round(1); g["ci95_high_%"] = (hi * 100).round(1)
    g["z"] = np.where(g.v > 1e-9, (g.late - g.exp) / np.sqrt(g.v.clip(lower=1e-9)), np.nan); g["p"] = 2 * stats.norm.sf(np.abs(g.z)); ok = g.p.notna(); g.loc[ok, "p_BH"] = bh(g.loc[ok, "p"].values)
    sig = int((g.p_BH < .05).sum()); tested = int(ok.sum())
    g.drop(columns=["exp", "v"]).to_csv(f"{D}/{fname}.csv", index=False)
    R.sec(name, f"{len(g)} cells with n>={MIN_N_MULTI} ({int(g.n.sum()):,} {unit}); late-rate range {g['late_rate_%'].min():.1f}-{g['late_rate_%'].max():.1f}%. Cells testable against mode expectation: {tested}; **significantly different after BH correction: {sig}**.\n")
    R.table(g.sort_values("n", ascending=False)[keys + ["n", "late_rate_%", "ci95_low_%", "ci95_high_%", "expected_%", "p_BH"]], f"{fname}_table.csv", maxrows=12)
    hm = g.pivot(index=row, columns=col, values="late_rate_%"); hn = g.pivot(index=row, columns=col, values="n")
    fig, ax = plt.subplots(figsize=(max(6, .9 * hm.shape[1] + 3), max(3.5, .38 * hm.shape[0] + 2)))
    sns.heatmap(hm, annot=True, fmt=".0f", cmap="RdYlBu_r", vmin=0, vmax=100, ax=ax, cbar_kws={"label": "Late rate (%)"}, annot_kws={"size": 7}, linewidths=.3); ax.set_title(title + f"\n(cells n>={MIN_N_MULTI}; {sig} of {tested} deviate from mode-expected)", fontsize=10); save(fig, D, f"{fname}.png"); R.fig(f"{fname}.png", title)
    return g, sig, tested
res = {}
res["A"] = combo(ov, ["region", "mode"], "A. Region + Shipping mode + Late", "A_region_mode", "region", "mode", "Late rate (%): destination region x shipping mode")
res["C"] = combo(ov, ["qgrp", "mode"], "B. Quantity group + Shipping mode + Late", "B_quantity_mode", "qgrp", "mode", "Late rate (%): order-size group x shipping mode")
res["E"] = combo(ov, ["vgrp", "mode"], "C. Order value + Shipping mode + Late (priority unavailable)", "C_value_mode", "vgrp", "mode", "Late rate (%): order-value quartile x shipping mode")
res["F"] = combo(ov, ["noon", "mode"], "D. Order time (before/after noon) + Shipping mode + Late (replaces scheduled-duration x mode, identical to mode)", "D_noon_mode", "noon", "mode", "Late rate (%): order time x shipping mode")
res["G"] = combo(ov, ["segment", "mode"], "E. Customer segment + Shipping mode + Late (priority unavailable)", "E_segment_mode", "segment", "mode", "Late rate (%): customer segment x shipping mode")
res["D"] = combo(ov, ["month", "market"], "F. Month + Market + Late", "F_month_market", "month", "market", "Late rate (%): order month x market")
res["H"] = combo(ov, ["volgrp", "market"], "G. Daily order volume + Market + Late", "G_volume_market", "volgrp", "market", "Late rate (%): same-day order volume tercile x market")
Lv["market"] = Lv["Market"]
topc = Lv["Category Name"].value_counts().head(12).index
res["B"] = combo(Lv[Lv["Category Name"].isin(topc)], ["Category Name", "market"], "H. Product category (top 12) + Market + Late (line level)", "H_category_market", "Category Name", "market", "Late rate (%): top-12 category x market", unit="order lines")
R.sec("Combinations not possible", "Priority + shipping mode; order value + priority; customer segment + priority; any combination using origin or route.")
tot_sig = sum(v[1] for v in res.values()); tot_tested = sum(v[2] for v in res.values())
R.sec("Interpretation", f"- Across all combinations, **{tot_sig} of {tot_tested} testable cells** differ from the mode-expected late rate after multiple-testing correction.\n- The only structured multivariate effect is **shipping mode x order time** (Same Day noon cutoff); every other combination is explained by shipping mode alone.\n- Group sizes are shown in the CSV/tables; no cell below n={MIN_N_MULTI} is interpreted.")
R.sec("Candidate ML features", "Interaction `mode x ordered_after_noon` (approved). No other multivariate feature is supported.")
R.sec("Limitations", "Cell-wise tests across many cells have limited power for small cells; absence of significance is not proof of no effect.")
R.save(); KEY["multi"] = {k: (v[1], v[2]) for k, v in res.items()}

# =============== ADVANCED ===============
D = folder("patterns", "advanced_analysis"); R = Report(D, "Advanced pattern analysis")
R.sec("Scope", base + "\n\nMethods run: distribution/outlier analysis, class imbalance, chi-square + Cramer's V for every categorical field (BH-corrected), Kruskal-Wallis/Mann-Whitney, a **within-mode residual-signal search**, subgroup stability, K-Means clustering and association-rule mining. Hierarchical clustering and DBSCAN were not run (no benefit expected on mostly discrete, signal-free inputs).")
# class imbalance
ni = int(ov.late.sum()); nn = NV - ni
R.sec("Class imbalance", f"Late = {ni:,} ({ni/NV*100:.2f}%), not late = {nn:,} ({nn/NV*100:.2f}%); ratio {ni/nn:.2f}:1. Moderate; no resampling is required. A majority-class baseline accuracy would be {max(ni,nn)/NV*100:.2f}%. By mode the target is highly separated: First Class 100% late, Standard Class 39.9%.")
# distribution & outliers
rows = []
for c, nm in [("qty", "order total quantity"), ("value", "order value"), ("gross", "gross sales"), ("discount", "discount amount"), ("disc_rate", "avg discount rate"), ("items", "items per order"), ("delay", "delay days")]:
    s = ov[c]; q1, q3 = s.quantile([.25, .75]); iqr = q3 - q1; lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr; mad = np.median(np.abs(s - s.median()))
    rows.append({"variable": nm, "mean": s.mean(), "median": s.median(), "P1": s.quantile(.01), "P99": s.quantile(.99), "skew": stats.skew(s), "excess kurtosis": stats.kurtosis(s), "IQR outliers": int(((s < lo) | (s > hi)).sum()), "% outliers": ((s < lo) | (s > hi)).mean() * 100, "robust z>3.5 (MAD)": int((0.6745 * np.abs(s - s.median()) / mad > 3.5).sum()) if mad > 0 else 0})
R.sec("Distribution and outlier analysis (orders)", "Outliers are flagged, **not removed**.\n"); R.table(pd.DataFrame(rows), "distribution_outliers.csv", floatfmt=".2f")
# association ranking
cats = {"Shipping Mode": "mode", "Order country": "country", "Order region": "region", "Market": "market", "Order state": "state", "Customer segment": "segment", "Payment type": "pay_type", "Order-size group": "qgrp", "Value quartile": "vgrp", "Items per order": "items", "Order month": "month", "Weekday": "weekday", "Quarter": "quarter", "Year": "year", "Order hour": "hour", "Ordered after noon": "noon", "First category": "cat_first", "First department": "dept_first", "Customer country": "cust_country", "Daily volume tercile": "volgrp"}
ar = []
for nm, c in cats.items():
    d_ = ov
    if c in ("country", "state"): sz = ov[c].value_counts(); d_ = ov[ov[c].isin(sz[sz >= MIN_N].index)]
    chi, p, dof, v = chi2_v(d_, c); ar.append({"variable": nm, "orders": len(d_), "groups": d_[c].nunique(), "chi2": chi, "dof": dof, "p": p, "Cramer V": v, "strength": v_label(v)})
AR = pd.DataFrame(ar); AR["p_BH"] = bh(AR.p.values); AR = AR.sort_values("Cramer V", ascending=False)
R.sec("Chi-square and Cramer's V: every categorical variable vs late (overall)", "Country and state restricted to groups with n>=100. Cramer's V is biased upward for variables with many groups and few observations.\n"); R.table(AR, "association_ranking.csv", floatfmt=".4g")
# residual search within mode (Second+Standard)
sub = ov[ov["mode"].isin(["Second Class", "Standard Class"])]
rr = []
for nm, c in cats.items():
    if c in ("mode", "noon"): continue
    tc, td, tn = 0, 0, 0
    for m, g in sub.groupby("mode"):
        d_ = g
        if c in ("country", "state"): sz = g[c].value_counts(); d_ = g[g[c].isin(sz[sz >= 50].index)]
        ct = pd.crosstab(d_[c], d_.late); ct = ct[ct.sum(axis=1) > 0]
        if ct.shape[0] < 2 or ct.shape[1] < 2: continue
        chi, p, dof, _ = stats.chi2_contingency(ct); tc += chi; td += dof; tn += ct.values.sum()
    rr.append({"variable": nm, "orders (2 modes)": len(sub), "pooled chi2": tc, "pooled dof": td, "p": stats.chi2.sf(tc, td), "pooled Cramer V (approx.)": np.sqrt(tc / len(sub))})
for c, nm in [("qty", "total quantity"), ("value", "order value"), ("disc_rate", "avg discount rate"), ("items", "items per order"), ("lat", "customer latitude"), ("lon", "customer longitude"), ("avg_price", "avg unit price"), ("h_customer_rate", "customer prior late rate"), ("h_category_rate", "category prior late rate"), ("h_region_rate", "region prior late rate")]:
    aucs, ps = [], []
    for m, g in sub.groupby("mode"):
        g = g.dropna(subset=[c]); a = g[g.late == 1][c]; b = g[g.late == 0][c]
        if len(a) > 30 and len(b) > 30: U, p = stats.mannwhitneyu(a, b); aucs.append(U / (len(a) * len(b))); ps.append(p)
    rr.append({"variable": nm + " (numeric, Mann-Whitney)", "orders (2 modes)": len(sub), "pooled chi2": (-2 * np.sum(np.log(ps))), "pooled dof": 2 * len(ps), "p": stats.chi2.sf(-2 * np.sum(np.log(ps)), 2 * len(ps)), "pooled Cramer V": np.nan, "mean within-mode AUC": np.mean(aucs)})
RR = pd.DataFrame(rr); RR["p_BH"] = bh(RR.p.values); RR = RR.sort_values("p")
R.sec("Residual-signal search: does anything predict lateness *within* Second Class and Standard Class?", f"Because shipping mode explains most variation (Pattern 2) and Same Day / First Class are deterministic, the remaining question is whether any other variable carries signal **inside** the two probabilistic modes (n = {len(sub):,} orders). Categorical variables: chi-square computed within each mode and pooled (sum of chi2 and dof); numeric: Mann-Whitney AUC per mode, Fisher-combined p-values. BH correction across all variables.\n"); R.table(RR, "residual_signal_search.csv", floatfmt=".4g")
nsig = int((RR.p_BH < .05).sum())
R.parts.append(f"\n**Variables significant after BH correction: {nsig} of {len(RR)}.**\n")
# Kruskal
kr = []
for nm, c in [("Shipping Mode", "mode"), ("Market", "market"), ("Customer segment", "segment"), ("Order-size group", "qgrp"), ("Value quartile", "vgrp"), ("Weekday", "weekday"), ("Month", "month")]:
    H_, p = stats.kruskal(*[g.delay.values for _, g in ov.groupby(c, observed=True)]); kr.append({"grouping": nm, "groups": ov[c].nunique(), "Kruskal H": H_, "p": p, "eta^2_H": (H_ - ov[c].nunique() + 1) / (NV - ov[c].nunique())})
R.sec("Kruskal-Wallis: delay days across groups", "eta^2_H is the effect size (0.01 small, 0.06 medium, 0.14 large).\n"); R.table(pd.DataFrame(kr), floatfmt=".4g")
# subgroup stability
ys = ov.pivot_table(index="mode", columns="year", values="late", aggfunc="mean").mul(100).round(1); yn = ov.pivot_table(index="mode", columns="year", values="late", aggfunc="size")
R.sec("Subgroup stability: late rate (%) by mode and year", f"A stable subgroup keeps the same late rate across years. (Cells: n = {int(yn.min().min()):,} to {int(yn.max().max()):,}.)\n"); R.table(ys.reset_index())
sdm = ov[ov["mode"] == "Same Day"]; st_ = sdm.groupby("year").apply(lambda g: ((g.hour >= 12).astype(int) == g.late).mean() * 100).round(1)
R.parts.append("\nSame Day noon-cutoff rule agreement by year: " + ", ".join(f"{k}: {v}%" for k, v in st_.items()) + ".\n")
# clustering
cf = ["qty", "items", "value", "disc_rate", "avg_price"]; Z = StandardScaler().fit_transform(ov[cf]); samp = np.random.default_rng(0).choice(NV, 10000, replace=False); sil = {}
for k in range(2, 8): sil[k] = silhouette_score(Z[samp], KMeans(k, n_init=5, random_state=0).fit_predict(Z[samp]))
kb = max(sil, key=sil.get); km = KMeans(kb, n_init=10, random_state=0).fit(Z); ov["cl"] = km.labels_
cp_ = ov.groupby("cl").agg(n=("late", "size"), qty=("qty", "mean"), items=("items", "mean"), value=("value", "mean"), disc_rate=("disc_rate", "mean"), avg_price=("avg_price", "mean"), late=("late", "sum")).reset_index(); cp_["late_rate_%"] = (cp_.late / cp_.n * 100).round(2); lo, hi = wilson(cp_.late, cp_.n); cp_["ci95_low_%"] = (lo * 100).round(2); cp_["ci95_high_%"] = (hi * 100).round(2)
chi, p, dof, v = chi2_v(ov, "cl")
R.sec("Clustering (K-Means)", f"Inputs (standardised; **no target-derived columns**): total quantity, items, order value, average discount rate, average unit price (n = {NV:,}). k chosen by silhouette on a 10,000-order sample: " + ", ".join(f"k={k}: {s:.3f}" for k, s in sil.items()) + f" -> **k = {kb}**. Cluster-late-rate association: chi2 p = {p:.3g}, Cramer's V = {v:.3f}.\n"); R.table(cp_.drop(columns="late"), "kmeans_clusters.csv")
R.parts.append(f"\nInterpretation: clusters describe order *size/value profiles* (largest differences in quantity/value columns). {'Their late rates do not differ meaningfully, so the clusters are descriptive only and have no predictive use.' if v<.05 else 'Late rates differ; validate before use.'} Silhouette values are low-to-moderate, so cluster boundaries are not sharp.\n")
fig, ax = plt.subplots(figsize=(7, 4)); ax.bar(cp_.cl.astype(str), cp_["late_rate_%"], yerr=[cp_["late_rate_%"] - cp_["ci95_low_%"], cp_["ci95_high_%"] - cp_["late_rate_%"]], color=C1, capsize=4); [ax.text(i, 2, f"n={n:,}", ha="center", color="white", fontsize=8) for i, n in enumerate(cp_.n)]; ax.axhline(OV, color=C2, ls="--"); ax.set_ylim(0, 100); ax.set_xlabel("Cluster"); ax.set_ylabel("Late rate (%)"); ax.set_title("Late rate by K-Means cluster (95% CI)"); save(fig, D, "01_cluster_late_rate.png"); R.fig("01_cluster_late_rate.png", "Cluster late rate")
# association rules
items = {"mode": "Mode", "market": "Market", "qgrp": "Qty", "vgrp": "Value", "segment": "Segment", "noon": "Time", "pay_type": "Pay"}
cols = {}
for c, lb in items.items():
    for v_ in ov[c].astype(str).unique(): cols[f"{lb}={v_}"] = (ov[c].astype(str) == v_).values
B = pd.DataFrame(cols); late_v = ov.late.values == 1; pl = late_v.mean(); rows = []
names = list(B.columns); arr = B.values
def add_rule(idx):
    m = arr[:, idx].all(axis=1); n_ = m.sum()
    if n_ < max(MIN_N, .01 * NV): return
    for tgt, tv in [("LATE", late_v), ("NOT LATE", ~late_v)]:
        conf = (m & tv).sum() / n_; rows.append({"antecedent": " & ".join(names[i] for i in idx), "consequent": tgt, "support": (m & tv).sum() / NV, "antecedent support": n_ / NV, "confidence": conf, "lift": conf / (tv.mean()), "orders in antecedent": int(n_)})
import itertools
fam = [c.split("=")[0] for c in names]
for i in range(len(names)): add_rule([i])
for i, j in itertools.combinations(range(len(names)), 2):
    if fam[i] != fam[j]: add_rule([i, j])
AR2 = pd.DataFrame(rows); AR2["has mode"] = AR2.antecedent.str.contains("Mode=")
tops = AR2[AR2.consequent == "LATE"].sort_values("lift", ascending=False)
nm_ = tops[~tops["has mode"]].head(10)
R.sec("Association rules (support, confidence, lift)", f"Transactions = orders (n = {NV:,}); items = mode, market, order-size group, value quartile, segment, order time (before/after noon), payment type; antecedents of 1-2 items with support >= 1%; consequent LATE (base rate {pl*100:.1f}%) or NOT LATE. Rules show co-occurrence, **not causation**. Implemented directly (no mlxtend).\n\n**Top LATE rules (any antecedent):**\n")
R.table(tops.head(10).drop(columns="has mode"), "association_rules_top.csv", floatfmt=".3f")
R.parts.append("\n**Top LATE rules without shipping mode in the antecedent** (shows whether anything else matters):\n"); R.table(nm_.drop(columns="has mode"), floatfmt=".3f")
R.parts.append(f"\nBest lift without mode = {nm_.lift.max():.3f} (a lift near 1.0 means no association). Rules including mode simply restate Pattern 2 (e.g. First Class => LATE with confidence 1.0).\n")
R.sec("Interpretation", f"- Only shipping mode (and the Same Day noon cutoff) shows strong structure. After mode is controlled, {nsig} of {len(RR)} tested variables are significant.\n- Clusters and association rules without mode have no predictive structure.\n- Statistical significance with ~63k orders can flag tiny effects; effect sizes (V, AUC) are reported next to p-values.")
R.sec("Candidate ML features", "Per the residual search, only features that remain significant *and* meaningful within mode should be added beyond mode and order time.")
R.sec("Limitations", "Rule mining restricted to 7 categorical items; DBSCAN/hierarchical not run.")
R.save(); KEY["adv"] = dict(AR=AR[["variable", "Cramer V", "p_BH"]].head(8).values.tolist(), RR=RR[["variable", "p", "p_BH"]].head(8).values.tolist(), nsig=nsig, k=kb, sil=sil, cl_v=v, best_lift_no_mode=nm_.lift.max())
pd.to_pickle(KEY, "key_c.pkl")
print(CT.to_string()); print(HP.to_string()); print(vif.to_string()); print(KEY["multi"]); print(AR.to_string()); print(RR.to_string()); print(pd.DataFrame(kr).to_string()); print(ys); print(cp_.to_string()); print(sil, kb); print(nm_.head(5).to_string())
