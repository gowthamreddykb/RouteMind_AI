from common import *
from sklearn.metrics import roc_auc_score
o, L = load_orders()
ov = o[~o.canceled_ship].copy(); Lv = L[~L.canceled_ship].copy()
OV = ov.late.mean() * 100; NV = len(ov)
SEV = ["Early (<0)", "On time (0)", "Late 1 day", "Late 2 days", "Late 3+ days"]
def sev(d): return pd.cut(d, [-99, -1, 0, 1, 2, 99], labels=SEV)
ov["sev"] = sev(ov.delay)
base = f"Unit: **order** (n = {NV:,} orders excluding {int(o.canceled_ship.sum()):,} 'Shipping canceled'); overall late rate = **{OV:.2f}%**."
KEY = {}

def rate_bar(d, t, lab, title, fn, horizontal=True, top=None, figsize=(8, 5), xlabel="Late-delivery rate (%)"):
    t = t.copy()
    if top: t = t.head(top)
    fig, ax = plt.subplots(figsize=figsize)
    y = np.arange(len(t)); err = [t["late_rate_%"] - t["ci95_low_%"], t["ci95_high_%"] - t["late_rate_%"]]
    ax.barh(y, t["late_rate_%"], xerr=err, color=C1, alpha=.85, ecolor="#555", capsize=2)
    ax.set_yticks(y); ax.set_yticklabels([f"{a} (n={n:,})" for a, n in zip(t[lab].astype(str), t["n"])], fontsize=8)
    ax.invert_yaxis(); ax.axvline(OV, color=C2, ls="--", lw=1.2, label=f"Overall {OV:.1f}%")
    ax.set_xlabel(xlabel); ax.set_title(title); ax.legend(loc="lower right"); fn(fig)

def assoc_line(d, col, label):
    chi, p, dof, v = chi2_v(d, col)
    return f"Chi-square test of `{label}` vs late: chi2 = {chi:,.1f}, dof = {dof}, p = {p:.3g}, Cramer's V = {v:.3f} ({v_label(v)})."

# =============== PATTERN 1 ===============
D = folder("patterns", "late_delivery"); R = Report(D, "Pattern 1: Late-delivery patterns")
tot = o.status.value_counts().rename_axis("Delivery Status").reset_index(name="orders")
tot["% of all orders"] = (tot.orders / len(o) * 100).round(2)
cnt = ov.sev.value_counts().reindex(SEV).rename_axis("Outcome").reset_index(name="orders"); cnt["% of valid orders"] = (cnt.orders / NV * 100).round(2)
late_n = int((ov.delay > 0).sum()); ont = int((ov.delay == 0).sum()); early = int((ov.delay < 0).sum())
lo, hi = wilson(late_n, NV)
d_late = ov[ov.delay > 0].delay
cons = pd.crosstab(L.groupby("Order Id").first()["Delivery Status"], [np.sign(o.set_index("Order Id").delay).rename("sign(real-sched)"), o.set_index("Order Id").late.rename("Late_delivery_risk")])
cons = pd.crosstab(o.status, [np.sign(o.delay).rename("sign(real-sched)"), o.late.rename("Late_flag")])
cons.columns = [f"sign {a}, flag {b}" for a, b in cons.columns]; cons = cons.reset_index()
R.sec("Definitions and data used", base + "\n\nDelay Days = Actual days - Scheduled days (`Days for shipping (real)` - `Days for shipment (scheduled)`). Positive = late, 0 = on time, negative = early.")
R.sec("Target validity check", "Cross-tab (orders, **all** 65,752 incl. canceled) of Delivery Status against the sign of calculated delay and `Late_delivery_risk`:\n")
R.table(cons)
R.parts.append(f"\n**Result:** for the 3 delivery statuses other than 'Shipping canceled', calculated lateness agrees with `Delivery Status` and `Late_delivery_risk` in 100% of orders. For 'Shipping canceled' ({int(o.canceled_ship.sum()):,} orders) the flag is always 0 although the timing fields exist, so those orders are excluded.\n")
R.sec("Late vs on-time vs early", f"Late: **{late_n:,} ({late_n/NV*100:.2f}%)**, 95% CI {lo*100:.2f}-{hi*100:.2f}%. On time: {ont:,} ({ont/NV*100:.2f}%). Early: {early:,} ({early/NV*100:.2f}%). The binary target (`late`) therefore groups early and on-time as 'not late'.\n")
R.table(cnt)
R.sec("Delay magnitude", f"""- All valid orders (n={NV:,}): mean delay {ov.delay.mean():.2f} days, median {ov.delay.median():.0f}, min {ov.delay.min()}, max {ov.delay.max()}.
- Late orders only (n={late_n:,}): mean {d_late.mean():.2f}, median {d_late.median():.0f}, max {d_late.max()}.
- Actual shipping days: mean {ov.real.mean():.2f}, median {ov.real.median():.0f}; scheduled days: mean {ov.sched.mean():.2f}, median {ov.sched.median():.0f}.
- Skewness of delay = {stats.skew(ov.delay):.2f}, excess kurtosis = {stats.kurtosis(ov.delay):.2f}.""")
R.sec("Delivery status (all orders)", ""); R.table(tot)
# repeated lateness
cl = ov.groupby("cust").late.agg(["size", "sum"])
rep = int((cl["sum"] >= 2).sum()); R.sec("Repeated late deliveries", f"{rep:,} of {len(cl):,} customers ({rep/len(cl)*100:.1f}%) had >= 2 late orders; {int((cl['sum']>=1).sum()):,} had >= 1. Whether this exceeds chance is tested in Pattern 8.")
# graphs
fig, ax = plt.subplots(figsize=(5.5, 5)); ax.pie([late_n, NV - late_n], labels=[f"Late\n{late_n:,}", f"Not late (on time/early)\n{NV-late_n:,}"], colors=[C2, C1], autopct="%1.1f%%", startangle=90, wedgeprops=dict(width=.4)); ax.set_title(f"Late vs not-late orders (n={NV:,})"); save(fig, D, "01_late_donut.png")
fig, ax = plt.subplots(figsize=(7, 4)); t = tot.set_index("Delivery Status").orders.sort_values(); ax.barh(t.index, t.values, color=C1); [ax.text(v, i, f" {v:,} ({v/len(o)*100:.1f}%)", va="center", fontsize=8) for i, v in enumerate(t.values)]; ax.set_xlabel("Orders"); ax.set_title(f"Delivery status distribution (all {len(o):,} orders)"); ax.set_xlim(0, t.max() * 1.25); save(fig, D, "02_status_bar.png")
fig, ax = plt.subplots(figsize=(7, 4)); ax.bar(cnt.Outcome, cnt.orders, color=[C3, C1, "#e59866", C2, "#7b241c"]); [ax.text(i, v, f"{v:,}\n{p:.1f}%", ha="center", va="bottom", fontsize=8) for i, (v, p) in enumerate(zip(cnt.orders, cnt["% of valid orders"]))]; ax.set_ylabel("Orders"); ax.set_title(f"Delay severity (n={NV:,})"); ax.set_ylim(0, cnt.orders.max() * 1.18); plt.setp(ax.get_xticklabels(), fontsize=8); save(fig, D, "03_severity_bar.png")
fig, ax = plt.subplots(figsize=(7, 4)); vc = ov.delay.value_counts().sort_index(); ax.bar(vc.index, vc.values, color=[C2 if i > 0 else C1 for i in vc.index]); ax.set_xlabel("Delay days (actual - scheduled)"); ax.set_ylabel("Orders"); ax.set_title(f"Delay-days distribution (n={NV:,})"); ax.set_xticks(vc.index); save(fig, D, "04_delay_hist.png")
mo = rate_table(ov, "ym"); mo["ym"] = mo.ym.astype(str)
fig, ax = plt.subplots(figsize=(11, 4)); x = np.arange(len(mo)); ax.plot(x, mo["late_rate_%"], color=C2, marker="o", ms=3); ax.fill_between(x, mo["ci95_low_%"], mo["ci95_high_%"], color=C2, alpha=.15); ax.set_xticks(x[::3]); ax.set_xticklabels(mo.ym[::3], rotation=45, ha="right"); ax.axhline(OV, color=C3, ls="--"); ax.set_ylabel("Late rate (%)"); ax.set_title("Monthly late-delivery rate with 95% CI"); save(fig, D, "05_monthly_late.png")
fig, ax = plt.subplots(figsize=(7, 4)); w = .38; a = ov.real.value_counts().sort_index(); s = ov.sched.value_counts().sort_index(); idx = sorted(set(a.index) | set(s.index)); ax.bar(np.array(idx) - w / 2, [s.get(i, 0) for i in idx], w, label="Scheduled", color=C3); ax.bar(np.array(idx) + w / 2, [a.get(i, 0) for i in idx], w, label="Actual", color=C1); ax.set_xlabel("Days"); ax.set_ylabel("Orders"); ax.set_title(f"Actual vs scheduled shipping days (n={NV:,})"); ax.legend(); save(fig, D, "06_actual_vs_sched.png")
fig, ax = plt.subplots(figsize=(11, 4)); mv = ov.groupby("ym").size(); ax.plot(np.arange(len(mv)), mv.values, color=C1, marker="o", ms=3); ax.set_xticks(np.arange(len(mv))[::3]); ax.set_xticklabels(mv.index.astype(str)[::3], rotation=45, ha="right"); ax.set_ylabel("Orders per month"); ax.set_title("Monthly shipment (order) volume"); save(fig, D, "07_volume_over_time.png")
for f, c in [("01_late_donut.png", "Late vs not late"), ("02_status_bar.png", "Delivery status"), ("03_severity_bar.png", "Delay severity"), ("04_delay_hist.png", "Delay days"), ("05_monthly_late.png", "Monthly late rate"), ("06_actual_vs_sched.png", "Actual vs scheduled"), ("07_volume_over_time.png", "Volume over time")]: R.fig(f, c)
R.sec("Interpretation", f"- Late delivery is the **majority outcome ({OV:.1f}%)**; the target is moderately balanced (ratio late:not-late = {late_n/(NV-late_n):.2f}:1), so no severe imbalance handling is indicated.\n- Delays are small and discrete: {int((ov.delay==1).sum()/late_n*100)}% of late orders are exactly 1 day late; the maximum is {int(d_late.max())} days.\n- Because scheduled days take only 4 values (tied to mode), 'late' largely reflects whether the real duration exceeds a fixed promise (see Pattern 2/10).")
R.sec("Candidate ML features", "Target = `late` (order-level, valid orders). Do **not** use `Late_delivery_risk`, `Delivery Status`, `Days for shipping (real)` or `shipping date` as inputs.")
R.sec("Limitations", "Real days are integers (1-day resolution). 'Shipping canceled' orders are excluded; their true lateness is undefined. Delivery completion time is not given directly (`shipping date` behaves as a completion date).")
R.save(); KEY["late_rate"] = OV; KEY["late_n"] = late_n

# =============== PATTERN 2 ===============
D = folder("patterns", "shipping_mode"); R = Report(D, "Pattern 2: Shipping-mode patterns")
mt = rate_table(ov, "mode", MIN_N).sort_values("late_rate_%", ascending=False)
ex = ov.groupby("mode").agg(mean_actual=("real", "mean"), mean_sched=("sched", "mean"), mean_delay=("delay", "mean"), median_delay=("delay", "median")).reset_index()
mt = mt.merge(ex, on="mode"); mt["share_%"] = (mt.n / NV * 100).round(2)
sevm = pd.crosstab(ov["mode"], ov.sev, normalize="index").mul(100).round(1).reset_index()
R.sec("Definitions and data used", base)
R.sec("Late rate and durations by shipping mode", ""); R.table(mt[["mode", "n", "share_%", "late", "late_rate_%", "ci95_low_%", "ci95_high_%", "mean_actual", "mean_sched", "mean_delay", "median_delay"]], "mode_summary.csv")
R.sec("Delay severity by mode (% of mode's orders)", ""); R.table(sevm, "mode_severity.csv")
R.sec("Statistical test", assoc_line(ov, "mode", "Shipping Mode"))
H, p = stats.kruskal(*[g.delay.values for _, g in ov.groupby("mode")]); R.parts.append(f"\nKruskal-Wallis on delay days across modes: H = {H:,.1f}, p = {p:.3g}.\n")
oq = pd.crosstab(ov["mode"], pd.cut(ov.qty, [0, 2, 5, 10, 999], labels=["1-2", "3-5", "6-10", "11+"]), normalize="index").mul(100).round(1).reset_index()
R.sec("Mode vs order size (% within mode)", ""); R.table(oq)
rg = pd.crosstab(ov["mode"], ov.market, normalize="index").mul(100).round(1).reset_index(); R.sec("Mode vs market (% within mode)", ""); R.table(rg)
topc = Lv["Category Name"].value_counts().head(8).index; cm = pd.crosstab(Lv[Lv["Category Name"].isin(topc)]["Category Name"], Lv["Shipping Mode"], normalize="index").mul(100).round(1).reset_index(); R.sec("Mode vs top-8 categories (% of lines)", ""); R.table(cm)
R.parts.append("\n**Order priority:** the dataset has no priority column, so mode-vs-priority cannot be analysed.\n")
fig, ax = plt.subplots(figsize=(6, 4)); t = mt.sort_values("n", ascending=False); ax.bar(t["mode"], t.n, color=C1); [ax.text(i, v, f"{v:,}\n{s:.1f}%", ha="center", va="bottom", fontsize=8) for i, (v, s) in enumerate(zip(t.n, t["share_%"]))]; ax.set_ylabel("Orders"); ax.set_title("Orders by shipping mode"); ax.set_ylim(0, t.n.max() * 1.2); save(fig, D, "01_mode_distribution.png")
rate_bar(ov, mt, "mode", "Late rate by shipping mode (95% CI)", lambda f: save(f, D, "02_mode_late_rate.png"), figsize=(7, 3.5))
fig, ax = plt.subplots(figsize=(7, 4)); t = mt.set_index("mode")[["mean_sched", "mean_actual"]]; t.plot.bar(ax=ax, color=[C3, C1]); ax.set_ylabel("Mean days"); ax.set_title("Scheduled vs actual shipping days by mode"); ax.set_xlabel(""); plt.setp(ax.get_xticklabels(), rotation=0); ax.legend(["Scheduled", "Actual"]); save(fig, D, "03_mode_actual_vs_sched.png")
fig, ax = plt.subplots(figsize=(8, 3.8)); sns.heatmap(pd.crosstab(ov["mode"], ov.sev, normalize="index").mul(100), annot=True, fmt=".1f", cmap="Blues", ax=ax, cbar_kws={"label": "% of mode's orders"}); ax.set_title("Delay severity by shipping mode (%)"); ax.set_xlabel(""); ax.set_ylabel(""); save(fig, D, "04_mode_severity_heatmap.png")
for f, c in [("01_mode_distribution.png", "Mode distribution"), ("02_mode_late_rate.png", "Late rate by mode"), ("03_mode_actual_vs_sched.png", "Actual vs scheduled"), ("04_mode_severity_heatmap.png", "Severity heatmap (substitute for priority heatmap)")]: R.fig(f, c)
hi_m, lo_m = mt.iloc[0], mt.iloc[-1]
R.sec("Interpretation", f"- Late rate ranges from **{lo_m['late_rate_%']:.1f}% ({lo_m['mode']}, n={lo_m['n']:,})** to **{hi_m['late_rate_%']:.1f}% ({hi_m['mode']}, n={hi_m['n']:,})**.\n- Scheduled days differ strongly by mode while actual days overlap, so the **promise, not the transit time, drives much of the apparent mode effect**.\n- Mode is the strongest single categorical association found in this dataset (Cramer's V above). Causation is not implied: mode is chosen by the customer/system and tied to a fixed promise.")
R.sec("Candidate ML features", "`Shipping Mode` (approved if chosen at order creation); `Days for shipment (scheduled)` is a deterministic function of mode (redundant: keep one, or keep both only for tree models).")
R.sec("Limitations", "No carrier or dispatch data. Mode may not be known at order creation in the real system: confirm with RouteMind data.")
R.save(); KEY["mode"] = mt[["mode", "n", "late_rate_%"]].values.tolist()

# =============== PATTERN 3 ===============
D = folder("patterns", "geography"); R = Report(D, "Pattern 3: Geographical patterns")
Rmode = ov.groupby("mode").late.mean()
ov["exp"] = ov["mode"].map(Rmode)
def geo(col, name):
    t = rate_table(ov, col, MIN_N); e = ov.groupby(col).agg(mean_delay=("delay", "mean"), exp=("exp", "sum")).reset_index()
    t = t.merge(e, on=col); t["expected_given_mode_%"] = (t.exp / t.n * 100).round(2); t["O/E"] = ((t.late / t.exp)).round(3)
    z = (t.late - t.exp) / np.sqrt((t.exp * (1 - t.exp / t.n)).clip(lower=1e-9))
    t["z_vs_mode_expected"] = z.round(2); t["p"] = 2 * stats.norm.sf(np.abs(z)); t["p_BH"] = bh(t.p.values); t = t.drop(columns=["exp"])
    return t
tabs = {"country": geo("country", "Order Country"), "state": geo("state", "Order State"), "city": geo("city", "Order City"), "region": geo("region", "Order Region"), "market": geo("market", "Market")}
R.sec("Definitions and data used", base + f"\n\nMinimum group size for ranking = {MIN_N} orders. `Order Country/State/City/Region/Market` describe the **delivery destination**. Because mode strongly affects lateness, each location's observed late count is also compared with the count **expected from its shipping-mode mix** (O/E); p-values are Benjamini-Hochberg adjusted within each level.")
R.parts.append("\n**Data-quality caveat:** a country can map to several 'Order Region' values (12.6% of orders), so region is not a clean aggregation of country. Country names are in Spanish.\n")
sumr = []
for lvl, col in [("Market", "market"), ("Region", "region"), ("Country", "country"), ("State", "state"), ("City", "city")]:
    t = tabs[col]; suff = t[t.n_sufficient]; d_ = ov[ov[col].isin(suff[col])]; chi, p, dof, v = chi2_v(d_, col)
    sumr.append({"Level": lvl, "Groups": len(t), "Groups n>=100": len(suff), "Orders in n>=100 groups": int(suff.n.sum()), "Min late %": suff["late_rate_%"].min(), "Max late %": suff["late_rate_%"].max(), "Chi2 p (groups n>=100)": p, "Cramer V (groups n>=100)": v, "Groups sig. vs mode-expected (BH<.05)": int(((suff.p_BH < .05)).sum())})
    R.sec(f"{lvl}-level summary (top 15 by volume)", ""); R.table(t.sort_values("n", ascending=False)[[col, "n", "late", "late_rate_%", "ci95_low_%", "ci95_high_%", "mean_delay", "expected_given_mode_%", "O/E", "p_BH"]], f"{col}_rates.csv", maxrows=15)
S = pd.DataFrame(sumr); R.sec("Geographic effect summary", "Spread of late rates across sufficiently large groups, and whether any group deviates from its shipping-mode expectation:\n"); R.table(S, floatfmt=".4g")
for f_, cc in [("country", "country"), ("region", "region")]:
    t = tabs[cc]; t = t[t.n_sufficient]
    sig = t[t.p_BH < .05].sort_values("O/E", ascending=False)
    R.sec(f"{cc.title()}s deviating from mode-expected rate (n>=100, BH p<.05)", "None." if sig.empty else "")
    if not sig.empty: R.table(sig[[cc, "n", "late_rate_%", "expected_given_mode_%", "O/E", "p_BH"]], maxrows=15)
# graphs
t = tabs["country"].sort_values("n", ascending=False).head(15); fig, ax = plt.subplots(figsize=(8, 5)); ax.barh(t.country, t.n, color=C1); ax.invert_yaxis(); ax.set_xlabel("Orders"); ax.set_title(f"Top 15 destination countries by order count (n={NV:,} orders)"); save(fig, D, "01_country_distribution.png")
t = tabs["region"].sort_values("late_rate_%", ascending=False); rate_bar(ov, t, "region", "Late rate by destination region (95% CI)", lambda f: save(f, D, "02_region_late_rate.png"), figsize=(8, 7))
for lvl, col in [("state", "state"), ("city", "city")]:
    t = tabs[col].sort_values("n", ascending=False).head(15); fig, ax = plt.subplots(figsize=(8, 5)); ax.barh(t[col], t.n, color=C1); ax.invert_yaxis(); ax.set_xlabel("Orders"); ax.set_title(f"Top 15 destination {lvl}s by order count"); save(fig, D, f"03_top_{lvl}_volume.png")
for lvl, col in [("state", "state"), ("city", "city")]:
    t = tabs[col]; t = t[t.n >= MIN_N].sort_values("late_rate_%", ascending=False).head(15); rate_bar(ov, t, col, f"Top 15 {lvl}s by late rate (n>={MIN_N}; 95% CI)", lambda f, lvl=lvl: save(f, D, f"04_top_{lvl}_late_rate.png"), figsize=(8, 5.5))
hm = ov.pivot_table(index="region", columns="mode", values="late", aggfunc="mean").mul(100); hn = ov.pivot_table(index="region", columns="mode", values="late", aggfunc="size")
hm = hm.where(hn >= MIN_N_MULTI); fig, ax = plt.subplots(figsize=(7, 8)); sns.heatmap(hm, annot=True, fmt=".0f", cmap="RdYlBu_r", ax=ax, cbar_kws={"label": "Late rate (%)"}, linewidths=.3); ax.set_title(f"Late rate (%) by region x shipping mode (cells n>={MIN_N_MULTI})"); save(fig, D, "05_region_mode_heatmap.png")
for f, c in [("01_country_distribution.png", "Country distribution"), ("02_region_late_rate.png", "Region late rate"), ("03_top_state_volume.png", "Top states by volume"), ("03_top_city_volume.png", "Top cities by volume"), ("04_top_state_late_rate.png", "Top states by late rate (n>=100)"), ("04_top_city_late_rate.png", "Top cities by late rate (n>=100)"), ("05_region_mode_heatmap.png", "Region x mode heatmap (geographic heatmap substitute)")]: R.fig(f, c)
tr = tabs["region"]; tr = tr[tr.n_sufficient]
R.sec("Interpretation", f"- Region late rates span only {tr['late_rate_%'].min():.1f}%-{tr['late_rate_%'].max():.1f}% across {len(tr)} regions with n>=100; Cramer's V for region is {S.loc[S.Level=='Region','Cramer V (groups n>=100)'].iloc[0]:.3f} ({v_label(S.loc[S.Level=='Region','Cramer V (groups n>=100)'].iloc[0])}).\n- Country/state/city extremes are mostly small-sample noise: the table above counts how many groups deviate from the mode-expected rate after multiple-testing correction.\n- A geographic ranking should be used only where n>=100 and the BH-adjusted deviation is significant.")
R.sec("Candidate ML features", "`Order Country`, `Order Region`, `Market` (conditional: weak evidence); `Order State`/`Order City` (conditional: high cardinality, needs target-encoding fitted on training data only); destination historical late rate (see Pattern 12). ZIP codes: rejected (86% missing).")
R.sec("Limitations", "No origin/warehouse and no destination coordinates (Latitude/Longitude are the customer's residence). A true map and distance features are not possible. Region labels are inconsistent with country.")
R.save()
KEY["geo"] = S.to_dict("records")

# =============== PATTERN 4 ===============
D = folder("patterns", "order_priority"); R = Report(D, "Pattern 4: Order-priority patterns")
R.sec("Status: cannot be completed", f"Searched all 53 columns for priority/urgency fields: **none exists**. Closest columns are `Shipping Mode` (analysed in Pattern 2) and `Days for shipment (scheduled)`, which are *not* priorities and are not renamed or treated as such here.\n\nNo result, graph or feature is produced for this pattern: **Insufficient data**. If RouteMind has an order-priority field, add it to the dataset and this analysis can be run with the same method as Pattern 2.")
R.sec("Impact on the project", "Priority + shipping-mode combinations in Pattern 15 are also unavailable.")
R.save()

# =============== PATTERN 5 ===============
D = folder("patterns", "order_quantity"); R = Report(D, "Pattern 5: Order-quantity patterns")
ov["qgrp"] = pd.cut(ov.qty, [0, 2, 5, 10, 999], labels=["1-2 (small)", "3-5 (medium)", "6-10 (large)", "11+ (very large)"])
qt = rate_table(ov, "qgrp", MIN_N); it = rate_table(ov.assign(items=ov["items"].astype(str)), "items", MIN_N)
rho, pr = stats.spearmanr(ov.qty, ov.delay); rho2, p2 = stats.spearmanr(ov.qty, ov.late)
mq, pq = stats.mannwhitneyu(ov[ov.late == 1].qty, ov[ov.late == 0].qty)
n1, n0 = (ov.late == 1).sum(), (ov.late == 0).sum(); rbc = 1 - 2 * mq / (n1 * n0)
R.sec("Definitions and data used", base + f"\n\nLine quantity = `Order Item Quantity` (per line, 1-5; line n={len(Lv):,}). **Order quantity = sum of line quantities within the order** (each line counted once). Groups are fixed in advance: 1-2, 3-5, 6-10, 11+ units.")
lq = Lv["Order Item Quantity"].value_counts().sort_index().rename_axis("Line quantity").reset_index(name="lines"); lq["%"] = (lq.lines / len(Lv) * 100).round(1)
R.sec("Line quantity distribution", ""); R.table(lq)
R.sec("Order-size groups: late rate", ""); R.table(qt[["qgrp", "n", "late", "late_rate_%", "ci95_low_%", "ci95_high_%"]], "qty_group_rates.csv")
R.sec("Items per order: late rate", ""); R.table(it[["items", "n", "late_rate_%", "ci95_low_%", "ci95_high_%"]])
R.sec("Statistical tests", assoc_line(ov, "qgrp", "order-size group") + f"\n\nSpearman(order quantity, delay days) = {rho:.4f} (p={pr:.3g}); Spearman(order quantity, late flag) = {rho2:.4f} (p={p2:.3g}). Mann-Whitney late vs not-late quantity: p = {pq:.3g}, rank-biserial effect = {rbc:.3f}. Median qty late = {ov[ov.late==1].qty.median():.0f}, not late = {ov[ov.late==0].qty.median():.0f}.")
mo_q = pd.crosstab(ov.qgrp, ov["mode"], normalize="index").mul(100).round(1).reset_index(); R.sec("Order-size group vs shipping mode (% within group)", ""); R.table(mo_q)
# mode-adjusted
ad = ov.groupby(["mode", "qgrp"], observed=True).late.agg(["size", "mean"]).reset_index(); R.sec("Order size within each shipping mode (late rate %, controls for mode)", ""); R.table(ad.pivot(index="mode", columns="qgrp", values="mean").mul(100).round(1).reset_index())
fig, ax = plt.subplots(figsize=(7, 4)); ax.bar(lq["Line quantity"], lq.lines, color=C1); [ax.text(a, b, f"{b:,}", ha="center", va="bottom", fontsize=8) for a, b in zip(lq["Line quantity"], lq.lines)]; ax.set_xlabel("Units per order line"); ax.set_ylabel("Order lines"); ax.set_title(f"Line quantity histogram (n={len(Lv):,} lines)"); save(fig, D, "01_quantity_hist.png")
fig, ax = plt.subplots(figsize=(8, 4)); vc = ov.qty.clip(upper=30).value_counts().sort_index(); ax.bar(vc.index, vc.values, color=C1); ax.set_xlabel("Total units per order (30 = 30 or more)"); ax.set_ylabel("Orders"); ax.set_title(f"Order total-quantity distribution (n={NV:,} orders)"); save(fig, D, "02_order_size_distribution.png")
rate_bar(ov, qt, "qgrp", "Late rate by order-size group (95% CI)", lambda f: save(f, D, "03_late_by_size.png"), figsize=(7, 3.5))
m = ov.groupby("qty").agg(d=("delay", "mean"), n=("delay", "size")).reset_index(); m = m[m.n >= 30]
fig, ax = plt.subplots(figsize=(8, 4.2)); ax.scatter(ov.qty + np.random.default_rng(0).uniform(-.25, .25, NV), ov.delay + np.random.default_rng(1).uniform(-.25, .25, NV), s=2, alpha=.08, color=C3); ax.plot(m.qty, m.d, color=C2, marker="o", label="Mean delay (groups n>=30)"); ax.set_xlabel("Order total quantity (units)"); ax.set_ylabel("Delay days"); ax.set_title(f"Quantity vs delay (n={NV:,}; jittered)"); ax.legend(); save(fig, D, "04_qty_vs_delay.png")
for f, c in [("01_quantity_hist.png", "Line quantity"), ("02_order_size_distribution.png", "Order-size distribution"), ("03_late_by_size.png", "Late rate by size"), ("04_qty_vs_delay.png", "Quantity vs delay")]: R.fig(f, c)
vq = chi2_v(ov, "qgrp")[3]
R.sec("Interpretation", f"- Late rate across order-size groups ranges {qt['late_rate_%'].min():.1f}-{qt['late_rate_%'].max():.1f}% (Cramer's V = {vq:.3f}, {v_label(vq)}). Spearman rho with delay = {rho:.3f}.\n- {'Larger orders are NOT associated with more delays in a practically meaningful way.' if abs(rho)<.05 and vq<.05 else 'There is a measurable association; see tables for direction and size.'} Significance with n={NV:,} must be judged against the effect size, not p-value alone.")
R.sec("Candidate ML features", "`order_total_quantity`, `items_per_order`, `order_size_group` (conditional candidates: available at order creation; weak evidence).")
R.sec("Limitations", "Order sizes are capped by the dataset structure (<=5 lines, <=5 units per line). No weight/volume data.")
R.save(); KEY["qty"] = (rho, vq)

# =============== PATTERN 6 ===============
D = folder("patterns", "order_value"); R = Report(D, "Pattern 6: Order-value patterns")
R.sec("Definitions and data used", base + f"\n\nMonetary fields verified: `Sales` = unit price x quantity (100% of rows); `Order Item Total` = `Sales` - `Order Item Discount` (100%); `Sales per customer` is identical to `Order Item Total`. **Order value = sum of `Order Item Total` over the order's lines** (each line once; no repeated order totals exist in the file, so there is no double counting).")
q1, q2, q3 = ov.value.quantile([.25, .5, .75])
ov["vgrp"] = pd.qcut(ov.value, 4, labels=["Q1 low", "Q2", "Q3", "Q4 high"])
p95 = ov.value.quantile(.95); ov["top5"] = np.where(ov.value >= p95, "Top 5% value", "Rest")
vt = rate_table(ov, "vgrp", MIN_N); tt = rate_table(ov, "top5", MIN_N)
bounds = ov.groupby("vgrp", observed=True).value.agg(["min", "max"]).round(2).reset_index()
R.sec("Distribution", f"- Mean order value {ov.value.mean():,.2f}, median {ov.value.median():,.2f}, SD {ov.value.std():,.2f}, min {ov.value.min():,.2f}, max {ov.value.max():,.2f}. Skewness {stats.skew(ov.value):.2f}, excess kurtosis {stats.kurtosis(ov.value):.2f}.\n- IQR outliers (> Q3 + 1.5 IQR = {q3+1.5*(q3-q1):,.2f}): {int((ov.value>q3+1.5*(q3-q1)).sum()):,} orders ({(ov.value>q3+1.5*(q3-q1)).mean()*100:.1f}%). Currency is not stated in the dataset.")
R.sec("Value quartiles: late rate", ""); R.table(vt.merge(bounds, on="vgrp")[["vgrp", "min", "max", "n", "late_rate_%", "ci95_low_%", "ci95_high_%"]], "value_quartile_rates.csv")
R.sec("Top 5% value vs rest", ""); R.table(tt[["top5", "n", "late_rate_%", "ci95_low_%", "ci95_high_%"]])
rho, pr = stats.spearmanr(ov.value, ov.delay); rq, _ = stats.spearmanr(ov.value, ov.qty)
mq, pq = stats.mannwhitneyu(ov[ov.late == 1].value, ov[ov.late == 0].value); rbc = 1 - 2 * mq / (n1 * n0)
R.sec("Statistical tests", assoc_line(ov, "vgrp", "value quartile") + f"\n\nSpearman(value, delay) = {rho:.4f} (p={pr:.3g}); Spearman(value, quantity) = {rq:.3f}. Mann-Whitney value late vs not late: p = {pq:.3g}, rank-biserial = {rbc:.3f}. Median value late = {ov[ov.late==1].value.median():,.2f}, not late = {ov[ov.late==0].value.median():,.2f}.")
vm = ov.pivot_table(index="vgrp", columns="mode", values="late", aggfunc="mean", observed=True).mul(100).round(1).reset_index(); R.sec("Value quartile x shipping mode (late rate %)", ""); R.table(vm)
vmx = pd.crosstab(ov.vgrp, ov["mode"], normalize="index").mul(100).round(1).reset_index(); R.sec("Value quartile vs mode mix (% within quartile)", ""); R.table(vmx)
fig, ax = plt.subplots(figsize=(8, 4)); ax.hist(ov.value.clip(upper=ov.value.quantile(.99)), bins=60, color=C1); ax.set_xlabel("Order value (sum of Order Item Total; clipped at 99th pct)"); ax.set_ylabel("Orders"); ax.set_title(f"Order-value histogram (n={NV:,})"); save(fig, D, "01_value_hist.png")
fig, ax = plt.subplots(figsize=(6, 4.5)); sns.boxplot(data=ov.assign(o=ov.late.map({0: "Not late", 1: "Late"})), x="o", y="value", ax=ax, palette=[C1, C2], showfliers=False); ax.set_xlabel(""); ax.set_ylabel("Order value (outliers hidden)"); ax.set_title(f"Order value by delivery outcome (n={NV:,})"); save(fig, D, "02_value_boxplot.png")
rate_bar(ov, vt, "vgrp", "Late rate by order-value quartile (95% CI)", lambda f: save(f, D, "03_late_by_value.png"), figsize=(7, 3.5))
ov["vdec"] = pd.qcut(ov.value, 10, labels=False) + 1; dm = ov.groupby("vdec").agg(v=("value", "median"), d=("delay", "mean")).reset_index()
fig, ax = plt.subplots(figsize=(8, 4.2)); ax.hexbin(ov.value.clip(upper=p95 * 1.5), ov.delay, gridsize=30, cmap="Blues", mincnt=1); ax2 = ax; ax.plot(dm.v, dm.d, color=C2, marker="o", label="Mean delay per value decile"); ax.set_xlabel("Order value"); ax.set_ylabel("Delay days"); ax.set_title(f"Order value vs delay (n={NV:,})"); ax.legend(); save(fig, D, "04_value_vs_delay.png")
for f, c in [("01_value_hist.png", "Value histogram"), ("02_value_boxplot.png", "Value by outcome"), ("03_late_by_value.png", "Late by value"), ("04_value_vs_delay.png", "Value vs delay")]: R.fig(f, c)
vv = chi2_v(ov, "vgrp")[3]
R.sec("Interpretation", f"- Late rate across value quartiles: {vt['late_rate_%'].min():.1f}-{vt['late_rate_%'].max():.1f}% (V={vv:.3f}, {v_label(vv)}); Spearman(value, delay) = {rho:.3f}.\n- {'No practically meaningful value effect.' if abs(rho)<.05 and vv<.05 else 'A measurable effect exists; see tables.'}")
R.sec("Candidate ML features", "`order_total_value`, `value_group`, `avg_discount_rate` (conditional: available at order creation if prices/discounts are known then).")
R.sec("Limitations", "Currency and tax treatment unknown. Profit fields are excluded (post-sale).")
R.save(); KEY["value"] = (rho, vv)

# =============== PATTERN 7 ===============
D = folder("patterns", "product_category"); R = Report(D, "Pattern 7: Product and category patterns")
R.sec("Definitions and data used", f"Unit: **order line** (n = {len(Lv):,} lines in {NV:,} valid orders), because categories/products belong to lines and an order can hold several (mean categories per order = {ov.n_cat.mean():.2f}). A line inherits its order's lateness, so late rates here are 'share of lines belonging to a late order'. Min group size {MIN_N} lines. {Lv['Category Name'].nunique()} categories, {Lv['Product Name'].nunique()} products, {Lv['Department Name'].nunique()} departments. Overall line late rate = {Lv.late.mean()*100:.2f}%.")
Lv["exp"] = Lv["Shipping Mode"].map(Lv.groupby("Shipping Mode").late.mean())
def lgrp(col):
    t = rate_table(Lv, col, MIN_N); e = Lv.groupby(col).agg(mean_delay=("delay", "mean"), qty=("Order Item Quantity", "sum"), exp=("exp", "sum")).reset_index()
    t = t.merge(e, on=col); t["O/E"] = (t.late / t.exp).round(3)
    z = (t.late - t.exp) / np.sqrt((t.exp * (1 - t.exp / t.n)).clip(lower=1e-9)); t["p"] = 2 * stats.norm.sf(np.abs(z)); t["p_BH"] = bh(t.p.values)
    return t.drop(columns="exp")
ct = lgrp("Category Name"); pt = lgrp("Product Name")
for nm, t, col in [("Category", ct, "Category Name"), ("Product", pt, "Product Name")]:
    chi, p, dof, v = chi2_v(Lv, col)
    R.sec(f"{nm} summary", f"{len(t)} groups; {int(t.n_sufficient.sum())} with n>=100. Chi-square vs late: p = {p:.3g}, Cramer's V = {v:.3f} ({v_label(v)}). Groups deviating from the mode-expected late rate (BH p<.05, n>=100): **{int(((t.p_BH<.05)&t.n_sufficient).sum())}**.\n")
    R.table(t.sort_values("n", ascending=False)[[col, "n", "qty", "late_rate_%", "ci95_low_%", "ci95_high_%", "mean_delay", "O/E", "p_BH"]], f"{nm.lower()}_rates.csv", maxrows=20)
R.parts.append(f"\n**Categories with the highest / lowest late rate (n>=100):** see `category_rates.csv`.\n")
d_ = Lv["Department Name"].value_counts(); 
t = ct.sort_values("n", ascending=False).head(20); fig, ax = plt.subplots(figsize=(8, 6)); ax.barh(t["Category Name"], t.n, color=C1); ax.invert_yaxis(); ax.set_xlabel("Order lines"); ax.set_title(f"Top 20 categories by line count (n={len(Lv):,} lines)"); save(fig, D, "01_category_distribution.png")
t = ct[ct.n >= MIN_N].sort_values("late_rate_%", ascending=False); 
def ov_lv(d): return d
OV_L = Lv.late.mean() * 100
fig, ax = plt.subplots(figsize=(8, 9)); t2 = t; y = np.arange(len(t2)); ax.barh(y, t2["late_rate_%"], xerr=[t2["late_rate_%"] - t2["ci95_low_%"], t2["ci95_high_%"] - t2["late_rate_%"]], color=C1, alpha=.85, capsize=2); ax.set_yticks(y); ax.set_yticklabels([f"{a} (n={n:,})" for a, n in zip(t2["Category Name"], t2.n)], fontsize=7); ax.invert_yaxis(); ax.axvline(OV_L, color=C2, ls="--", label=f"Overall {OV_L:.1f}%"); ax.set_xlabel("Late rate of lines (%)"); ax.set_title("Late rate by category (n>=100 lines; 95% CI)"); ax.legend(); save(fig, D, "02_category_late_rate.png")
t = pt.sort_values("n", ascending=False).head(15); fig, ax = plt.subplots(figsize=(8, 5)); ax.barh(t["Product Name"].str[:40], t.n, color=C1); ax.invert_yaxis(); ax.set_xlabel("Order lines"); ax.set_title("Top 15 products by line count"); save(fig, D, "03_top_products.png")
tc = Lv["Category Name"].value_counts().head(15).index; hm = Lv[Lv["Category Name"].isin(tc)].pivot_table(index="Category Name", columns="Shipping Mode", values="late", aggfunc="size"); hm = hm.div(hm.sum(axis=1), axis=0).mul(100)
fig, ax = plt.subplots(figsize=(8, 6)); sns.heatmap(hm, annot=True, fmt=".0f", cmap="Blues", ax=ax, cbar_kws={"label": "% of category's lines"}); ax.set_title("Shipping-mode mix by top-15 category (% of lines)"); ax.set_ylabel(""); save(fig, D, "04_category_mode_heatmap.png")
for f, c in [("01_category_distribution.png", "Category distribution"), ("02_category_late_rate.png", "Category late rate"), ("03_top_products.png", "Top products"), ("04_category_mode_heatmap.png", "Category x mode")]: R.fig(f, c)
vc_ = chi2_v(Lv, "Category Name")[3]; ts = ct[ct.n_sufficient]
R.sec("Interpretation", f"- Category late rates span {ts['late_rate_%'].min():.1f}-{ts['late_rate_%'].max():.1f}% (n>=100). Cramer's V = {vc_:.3f} ({v_label(vc_)}). After adjusting for shipping mode and multiple testing, **{int(((ct.p_BH<.05)&ct.n_sufficient).sum())} categories** and **{int(((pt.p_BH<.05)&pt.n_sufficient).sum())} products** deviate.\n- Category/product frequency is concentrated in a few items, but concentration is not risk. No product or category is declared high risk unless it passes both the size filter and the adjusted test.")
R.sec("Candidate ML features", "`Category Name`, `Department Name` (conditional); `Product Name` (conditional, high cardinality: use frequency or target encoding fitted on training data only); category historical late rate (Pattern 12).")
R.sec("Limitations", "Line-level rates double-count an order's lateness once per line; order-level inference needs the Pattern 12 history features.")
R.save(); KEY["cat"] = (vc_,)
pd.to_pickle(KEY, "key_a.pkl")
for k, v in KEY.items(): print(k, v)
print(S.to_string())
print(chi2_v(ov, "mode"), "qty", chi2_v(ov, "qgrp"), "cat", chi2_v(Lv, "Category Name"), "prod", chi2_v(Lv, "Product Name"))
print(ct.sort_values("late_rate_%").query("n>=100")[["Category Name", "n", "late_rate_%", "p_BH"]].iloc[[0, 1, -2, -1]])
print(qt[["qgrp", "n", "late_rate_%"]]); print(vt[["vgrp", "n", "late_rate_%"]])
