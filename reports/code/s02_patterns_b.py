from common import *
from sklearn.metrics import roc_auc_score
o, L = load_orders()
ov = o[~o.canceled_ship].copy().reset_index(drop=True); Lv = L[~L.canceled_ship].copy()
OV = ov.late.mean() * 100; NV = len(ov)
base = f"Unit: **order** (n = {NV:,} valid orders; 'Shipping canceled' excluded); overall late rate = **{OV:.2f}%**."
Rm = ov.groupby("mode").late.mean(); ov["pmode"] = ov["mode"].map(Rm)
KEY = {}

def past_feat(d, key):
    """Past-only history: only orders of the same group whose delivery completion (shipping date) is strictly
    before this order's creation time are counted."""
    kc = key if isinstance(key, list) else [key]
    pn = np.zeros(len(d)); pl = np.zeros(len(d)); pd_ = np.zeros(len(d))
    od = d.order_dt.values; sd = d.ship_dt.values; lt = d.late.values; dl = d.delay.values
    for _, idx in d.groupby(kc, observed=True).indices.items():
        o_ = np.argsort(sd[idx]); comp = sd[idx][o_]; cl = np.cumsum(lt[idx][o_]); cd = np.cumsum(dl[idx][o_])
        pos = np.searchsorted(comp, od[idx], side="left")
        pn[idx] = pos; pl[idx] = np.where(pos > 0, cl[np.maximum(pos - 1, 0)], 0); pd_[idx] = np.where(pos > 0, cd[np.maximum(pos - 1, 0)], 0)
    with np.errstate(invalid="ignore", divide="ignore"): return pn, np.where(pn > 0, pl / pn, np.nan), np.where(pn > 0, pd_ / pn, np.nan)

def auc(y, s):
    m = ~np.isnan(s); 
    return roc_auc_score(y[m], s[m]) if m.sum() > 50 and len(set(y[m])) == 2 else np.nan

def rate_bar(t, lab, title, fn, figsize=(8, 5), xlabel="Late-delivery rate (%)"):
    fig, ax = plt.subplots(figsize=figsize); y = np.arange(len(t))
    ax.barh(y, t["late_rate_%"], xerr=[t["late_rate_%"] - t["ci95_low_%"], t["ci95_high_%"] - t["late_rate_%"]], color=C1, alpha=.85, ecolor="#555", capsize=2)
    ax.set_yticks(y); ax.set_yticklabels([f"{a} (n={n:,})" for a, n in zip(t[lab].astype(str), t["n"])], fontsize=8); ax.invert_yaxis()
    ax.axvline(OV, color=C2, ls="--", label=f"Overall {OV:.1f}%"); ax.set_xlabel(xlabel); ax.set_title(title); ax.legend(loc="lower right"); fn(fig)

def assoc_line(d, col, label):
    chi, p, dof, v = chi2_v(d, col)
    return f"Chi-square test of `{label}` vs late: chi2 = {chi:,.1f}, dof = {dof}, p = {p:.3g}, Cramer's V = {v:.3f} ({v_label(v)})."

# ---------- history features (used by patterns 8 and 12) ----------
H = {}
for nm, key in [("customer", "cust"), ("country", "country"), ("region", "region"), ("mode", "mode"), ("category", "cat_first"), ("market", "market"), ("mode_x_region", ["mode", "region"]), ("mode_x_country", ["mode", "country"])]:
    pn, pr, pdl = past_feat(ov, key); H[nm] = (pn, pr, pdl); ov[f"h_{nm}_n"] = pn; ov[f"h_{nm}_rate"] = pr; ov[f"h_{nm}_delay"] = pdl
ov.to_pickle("orders_valid_hist.pkl")
y = ov.late.values

# =============== PATTERN 8 ===============
D = folder("patterns", "customer_history"); R = Report(D, "Pattern 8: Customer historical patterns")
cu = ov.groupby("cust").agg(orders=("late", "size"), late=("late", "sum"), value=("value", "mean"), qty=("qty", "mean"), n_country=("country", "nunique"), tot=("value", "sum"), exp=("pmode", "sum"), var=("pmode", lambda p: (p * (1 - p)).sum())).reset_index()
cu["late_rate"] = cu.late / cu.orders
R.sec("Definitions and data used", base + f"\n\nCustomers with >=1 valid order: **{len(cu):,}**. Descriptive customer statistics use all of a customer's orders (full period); **history features** (below) use only the customer's earlier orders whose `shipping date` (used as completion time) is strictly before the current order's creation time, so no future outcomes are used.")
fq = cu.orders.clip(upper=8).value_counts().sort_index().rename_axis("orders per customer (8 = 8+)").reset_index(name="customers"); fq["%"] = (fq.customers / len(cu) * 100).round(1)
R.sec("Order frequency", f"Mean orders/customer {cu.orders.mean():.2f}, median {cu.orders.median():.0f}, max {cu.orders.max()}. Repeat customers (>=2 orders): {int((cu.orders>=2).sum()):,} ({(cu.orders>=2).mean()*100:.1f}%).\n"); R.table(fq)
R.sec("Order value and size per customer", f"Mean of customers' average order value = {cu.value.mean():,.2f} (median {cu.value.median():,.2f}); mean of customers' average quantity = {cu.qty.mean():.2f}. {int((cu.n_country>1).sum()):,} customers ({(cu.n_country>1).mean()*100:.1f}%) ordered to more than one destination country.")
ten = cu[cu.orders >= 5]
chi_d = ((ten.late - ten.exp) ** 2 / ten["var"]).sum(); dfree = len(ten); p_d = stats.chi2.sf(chi_d, dfree)
R.sec("Do customers differ in lateness? (overdispersion test)", f"Customers with >=5 valid orders: **{len(ten):,}** (orders: {int(ten.orders.sum()):,}). If lateness were driven only by shipping mode (no customer effect), the dispersion statistic sum((k-E)^2/Var) would be about {dfree:,}. Observed = **{chi_d:,.0f}** (ratio {chi_d/dfree:.3f}), p = {p_d:.3g}. {'The observed spread is consistent with chance: there is no evidence of persistent customer-level lateness beyond the shipping-mode mix.' if p_d>.05 else 'Customers vary more than chance given mode mix.'} Customers with >=2 late orders: {int((cu.late>=2).sum()):,}.")
# history features
rows = []
for nm in ["customer", "country", "region", "mode", "category", "market", "mode_x_region", "mode_x_country"]:
    pn, pr, pdl = H[nm]; has = (pn >= 1)
    for thr in ([1, 3, 5] if nm == "customer" else [30]):
        m = pn >= thr
        a = auc(y[m], pr[m]) if m.sum() > 50 else np.nan
        am = np.nanmean([auc(y[(ov["mode"] == mo).values & m], pr[(ov["mode"] == mo).values & m]) for mo in ov["mode"].unique()]) if m.sum() > 50 else np.nan
        rho = stats.spearmanr(pr[m], y[m])[0] if m.sum() > 50 else np.nan
        rows.append({"History feature": f"prior late rate by {nm}", "min prior orders": thr, "orders covered": int(m.sum()), "coverage %": round(m.mean() * 100, 1), "univariate AUC": a, "mean within-mode AUC": am, "Spearman vs late": rho})
HF = pd.DataFrame(rows); HF.to_csv(f"{folder('patterns','historical_delivery')}/history_feature_summary.csv", index=False)
cust_hf = HF[HF["History feature"].str.contains("customer")]
R.sec("Customer history feature (past-only)", "Univariate discrimination of the customer's prior late rate (AUC 0.5 = no information). This is a descriptive check, not model performance.\n"); R.table(cust_hf, floatfmt=".3f")
m3 = ov.h_customer_n >= 3; bk = pd.cut(ov.h_customer_rate[m3], [-.01, 0, .34, .67, .99, 1], labels=["0% late", "1-34%", "35-67%", "68-99%", "100% late"])
bt = rate_table(ov[m3].assign(bk=bk.values), "bk", MIN_N); R.sec("Current late rate by customer's prior late-rate bucket (customers with >=3 completed prior orders)", ""); R.table(bt[["bk", "n", "late_rate_%", "ci95_low_%", "ci95_high_%"]])
bt0 = rate_table(ov.assign(pb=pd.cut(ov.h_customer_n, [-1, 0, 1, 2, 4, 999], labels=["0 prior", "1", "2", "3-4", "5+"])), "pb", MIN_N); R.sec("Current late rate by number of completed prior orders", ""); R.table(bt0[["pb", "n", "late_rate_%", "ci95_low_%", "ci95_high_%"]])
top = cu.sort_values("orders", ascending=False).head(15).copy(); top["late_rate_%"] = (top.late_rate * 100).round(1); top["total_value"] = top.tot.round(0)
R.sec("Top repeat customers (Customer Id only; names are not shown)", ""); R.table(top[["cust", "orders", "late", "late_rate_%", "total_value"]])
# graphs
fig, ax = plt.subplots(figsize=(7, 4)); ax.bar(fq.iloc[:, 0].astype(str), fq.customers, color=C1); ax.set_xlabel("Valid orders per customer (8 = 8+)"); ax.set_ylabel("Customers"); ax.set_title(f"Customer order-frequency distribution ({len(cu):,} customers)"); save(fig, D, "01_customer_frequency.png")
rng = np.random.default_rng(42)
sims = []
pm_by = ov.groupby("cust").pmode.apply(np.array)
for c in ten.cust: sims.append(rng.binomial(1, pm_by[c]).mean())
fig, ax = plt.subplots(figsize=(8, 4.2)); bins = np.linspace(0, 1, 21); ax.hist(ten.late_rate, bins=bins, alpha=.7, color=C1, label="Observed"); ax.hist(sims, bins=bins, histtype="step", lw=2, color=C2, label="Expected from shipping-mode mix only (1 simulation)"); ax.set_xlabel("Customer late rate"); ax.set_ylabel("Customers"); ax.set_title(f"Customer late-rate distribution (customers with >=5 orders, n={len(ten):,})"); ax.legend(fontsize=8); save(fig, D, "02_customer_late_distribution.png")
fig, ax = plt.subplots(figsize=(8, 5)); ax.barh(top.cust.astype(str), top.orders, color=C1); [ax.text(v, i, f" {l:.0f}% late", va="center", fontsize=8) for i, (v, l) in enumerate(zip(top.orders, top["late_rate_%"]))]; ax.invert_yaxis(); ax.set_xlabel("Valid orders"); ax.set_ylabel("Customer Id"); ax.set_title("Top 15 repeat customers by order count"); ax.set_xlim(0, top.orders.max() * 1.2); save(fig, D, "03_top_customers.png")
rate_bar(bt0, "pb", "Late rate by number of completed prior orders (95% CI)", lambda f: save(f, D, "04_late_by_prior_orders.png"), figsize=(7, 3.5))
for f, c in [("01_customer_frequency.png", "Frequency"), ("02_customer_late_distribution.png", "Late-rate distribution vs expectation"), ("03_top_customers.png", "Top customers"), ("04_late_by_prior_orders.png", "Performance vs prior orders")]: R.fig(f, c)
a1 = cust_hf[cust_hf["min prior orders"] == 3]["univariate AUC"].iloc[0]
R.sec("Interpretation", f"- {len(cu):,} customers place {NV:,} valid orders (mean {cu.orders.mean():.2f} per customer).\n- Customer prior late rate has univariate AUC {a1:.3f} (>=3 prior completed orders); {'this is essentially chance level.' if abs(a1-.5)<.02 else 'a modest signal that needs validation.'} Dispersion ratio {chi_d/dfree:.3f}.\n- Repeat-customer lateness cannot be distinguished from the shipping-mode mix alone.")
R.sec("Candidate ML features", "`customer_prior_order_count` (conditional), `customer_prior_late_rate` (conditional: only past-completed orders; null when no history), `customer_avg_order_value` (past-only). Evidence is weak; test on held-out time-split data before approval.")
R.sec("Limitations", "Completion time is approximated by `shipping date`; ~3.2 orders per customer limits history depth; early-period orders have no history.")
R.save(); KEY["cust"] = dict(auc3=a1, disp=chi_d / dfree, p=p_d, repeat=(cu.orders >= 2).mean())

# =============== PATTERN 9 ===============
D = folder("patterns", "time_based"); R = Report(D, "Pattern 9: Time-based patterns")
mo = ov.groupby("ym").size()
R.sec("Definitions and data used", base + f"\n\nDate coverage: orders from {o.order_dt.min()} to {o.order_dt.max()} (**37 calendar months**; January appears in 4 years, other months in 3). Time fields come from `order date (DateOrders)`.")
wd_o = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
def tt(col, order=None, label=None):
    t = rate_table(ov, col, MIN_N)
    if order is not None: t[col] = pd.Categorical(t[col], order, ordered=True); t = t.sort_values(col)
    return t
TW, TM, TQ, TY, TH = tt("weekday", wd_o), tt("month"), tt("quarter"), tt("year"), tt("hour")
for nm, t, col in [("Weekday", TW, "weekday"), ("Month of year", TM, "month"), ("Quarter", TQ, "quarter"), ("Year", TY, "year"), ("Hour of day", TH, "hour")]:
    chi, p, dof, v = chi2_v(ov, col); R.sec(f"{nm}: orders and late rate", assoc_line(ov, col, nm) + "\n"); R.table(t[[col, "n", "late", "late_rate_%", "ci95_low_%", "ci95_high_%"]], f"{col}_rates.csv", maxrows=24)
dv = ov.groupby("date").size(); wk = ov.groupby("week").size(); 
R.sec("Volume summary", f"Orders (valid) per day: mean {dv.mean():.1f}, median {dv.median():.0f}, min {dv.min()}, max {dv.max()} over {len(dv):,} days with orders. Per month: mean {mo.mean():.0f}, min {mo.min()} ({mo.idxmin()}), max {mo.max()} ({mo.idxmax()}). Weekly: mean {wk.mean():.0f}.")
ym_t = rate_table(ov, "ym"); ym_t["ym"] = ym_t.ym.astype(str); ym_t.to_csv(f"{D}/monthly_rates.csv", index=False)
pk = ym_t.sort_values("n", ascending=False).head(3); pl_ = ym_t.sort_values("late_rate_%", ascending=False).head(3)
R.sec("Peak periods", "Highest-volume months:\n"); R.table(pk[["ym", "n", "late_rate_%"]]); R.parts.append("\nHighest late-rate months:\n"); R.table(pl_[["ym", "n", "late_rate_%", "ci95_low_%", "ci95_high_%"]])
sd_ = ym_t["late_rate_%"].std(); exp_sd = np.sqrt(OV * (100 - OV) / ym_t.n.mean())
R.sec("Seasonality check", f"Std. deviation of monthly late rates = {sd_:.2f} pp; expected from sampling noise alone with ~{ym_t.n.mean():.0f} orders/month = {exp_sd:.2f} pp. {'Monthly variation is consistent with noise: no evidence of seasonality.' if sd_<1.5*exp_sd else 'Monthly variation exceeds noise: examine further.'} Only 3 full annual cycles exist, so seasonal conclusions are limited.")
mo_pivot = ov.pivot_table(index="month", columns="year", values="late", aggfunc="mean").mul(100).round(1).reset_index(); R.sec("Late rate (%) by month-of-year and year", ""); R.table(mo_pivot)
ov["noon"] = np.where(ov.hour >= 12, "12:00-23:59", "00:00-11:59")
hm_ = ov.groupby(["mode", "noon"]).late.agg(n="size", late="sum").reset_index(); hm_["late_rate_%"] = (hm_.late / hm_.n * 100).round(2); lo_, hi_ = wilson(hm_.late, hm_.n); hm_["ci95_low_%"] = (lo_ * 100).round(2); hm_["ci95_high_%"] = (hi_ * 100).round(2)
R.sec("Hour effect is confined to Same Day orders (within-mode check)", "The overall hour pattern (a step at 12:00) is **not** a general time-of-day effect. Splitting by shipping mode and order time before/after noon:\n"); R.table(hm_, "hour_by_mode.csv")
sdm = ov[ov["mode"] == "Same Day"]; R.parts.append(f"\nIn Same Day orders (n={len(sdm):,}) the rule 'ordered at or after 12:00 => late' matches the Late flag in **{((sdm.hour>=12).astype(int)==sdm.late).mean()*100:.1f}%** of orders. Other modes show no order-hour association (chi-square within mode: First Class constant; Second Class p=0.97; Standard Class p=0.86). The hour feature is therefore only useful *in interaction with shipping mode*.\n")
fig, ax = plt.subplots(figsize=(8, 4)); pv = hm_.pivot(index="mode", columns="noon", values="late_rate_%"); pv.plot.bar(ax=ax, color=[C1, C2]); ax.set_ylabel("Late rate (%)"); ax.set_xlabel(""); ax.set_title("Late rate by shipping mode and order time (before/after 12:00)"); plt.setp(ax.get_xticklabels(), rotation=0); ax.legend(title="Order time"); save(fig, D, "08_mode_noon_cutoff.png")
# graphs
def line_ts(series, title, ylabel, fn, color=C1):
    fig, ax = plt.subplots(figsize=(11, 4)); ax.plot(np.arange(len(series)), series.values, color=color, marker="o", ms=3); ax.set_xticks(np.arange(len(series))[::3]); ax.set_xticklabels(series.index.astype(str)[::3], rotation=45, ha="right"); ax.set_ylabel(ylabel); ax.set_title(title); fn(fig)
line_ts(mo, f"Monthly order volume (n={NV:,} valid orders)", "Orders", lambda f: save(f, D, "01_monthly_volume.png"))
fig, ax = plt.subplots(figsize=(11, 4)); x = np.arange(len(ym_t)); ax.plot(x, ym_t["late_rate_%"], color=C2, marker="o", ms=3); ax.fill_between(x, ym_t["ci95_low_%"], ym_t["ci95_high_%"], color=C2, alpha=.15); ax.axhline(OV, color=C3, ls="--"); ax.set_xticks(x[::3]); ax.set_xticklabels(ym_t.ym[::3], rotation=45, ha="right"); ax.set_ylabel("Late rate (%)"); ax.set_title("Monthly late-delivery rate with 95% CI"); save(fig, D, "02_monthly_late_rate.png")
fig, ax = plt.subplots(figsize=(7, 4)); ax.bar(TW.weekday.astype(str), TW.n, color=C1); ax.set_ylabel("Orders"); ax.set_title("Orders by weekday"); plt.setp(ax.get_xticklabels(), rotation=30); save(fig, D, "03_weekday_orders.png")
rate_bar(TW, "weekday", "Late rate by weekday (95% CI)", lambda f: save(f, D, "04_weekday_late_rate.png"), figsize=(7, 4))
fig, ax = plt.subplots(figsize=(9, 4)); ax.bar(TH.hour, TH.n, color=C1); ax.set_xlabel("Hour of day (order timestamp)"); ax.set_ylabel("Orders"); ax.set_title("Hourly order distribution"); save(fig, D, "05_hourly_orders.png")
fig, ax = plt.subplots(figsize=(9, 4)); ax.errorbar(TH.hour, TH["late_rate_%"], yerr=[TH["late_rate_%"] - TH["ci95_low_%"], TH["ci95_high_%"] - TH["late_rate_%"]], fmt="o-", color=C2, ms=3, capsize=2); ax.axhline(OV, color=C3, ls="--"); ax.set_xlabel("Hour of day"); ax.set_ylabel("Late rate (%)"); ax.set_title("Late rate by order hour (95% CI)"); save(fig, D, "06_hourly_late_rate.png")
fig, ax = plt.subplots(figsize=(11, 4)); w = ov.groupby("week").agg(n=("late", "size"), r=("late", "mean")); w = w[w.n >= 30]; ax2 = ax.twinx(); ax.plot(w.index, w.n, color=C1, label="Weekly orders"); ax2.plot(w.index, w.r.rolling(4).mean() * 100, color=C2, label="Late rate (4-week rolling, %)"); ax.set_ylabel("Orders per week"); ax2.set_ylabel("Late rate (%)"); ax2.grid(False); ax.set_title("Weekly volume and rolling late rate (weeks with >=30 orders)"); h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=8); save(fig, D, "07_weekly_trend.png")
for f, c in [("01_monthly_volume.png", "Monthly volume"), ("02_monthly_late_rate.png", "Monthly late rate"), ("03_weekday_orders.png", "Weekday orders"), ("04_weekday_late_rate.png", "Weekday late rate"), ("05_hourly_orders.png", "Hourly orders"), ("06_hourly_late_rate.png", "Hourly late rate"), ("07_weekly_trend.png", "Weekly trend"), ("08_mode_noon_cutoff.png", "Mode x noon cutoff")]: R.fig(f, c)
vm = {nm: chi2_v(ov, c)[3] for nm, c in [("weekday", "weekday"), ("month", "month"), ("hour", "hour"), ("year", "year")]}
R.sec("Interpretation", f"- Cramer's V vs late: weekday {vm['weekday']:.3f}, month {vm['month']:.3f}, hour {vm['hour']:.3f}, year {vm['year']:.3f} (weekday, month, year negligible; hour weak overall because of the Same Day noon cutoff).\n- Late-rate range by weekday {TW['late_rate_%'].min():.1f}-{TW['late_rate_%'].max():.1f}%, by month {TM['late_rate_%'].min():.1f}-{TM['late_rate_%'].max():.1f}%, by hour {TH['late_rate_%'].min():.1f}-{TH['late_rate_%'].max():.1f}%.")
R.sec("Candidate ML features", "`order_hour` / `ordered_after_noon` x `Shipping Mode` (**approved candidate**: deterministic for Same Day); `order_month`, `order_weekday`, `is_weekend`, `quarter`: rejected/low value (no effect found). Use year only for time-split validation, not as a feature.")
R.sec("Limitations", "Three annual cycles only; timestamps have a synthetic-looking distribution if flat (check hourly chart); no holiday calendar.")
R.save(); KEY["time"] = vm

# =============== PATTERN 10 ===============
D = folder("patterns", "scheduled_shipping"); R = Report(D, "Pattern 10: Scheduled-shipping patterns")
st = rate_table(ov, "sched", MIN_N); e = ov.groupby("sched").agg(mean_actual=("real", "mean"), median_actual=("real", "median"), mean_delay=("delay", "mean")).reset_index(); st = st.merge(e, on="sched")
R.sec("Definitions and data used", base + "\n\nScheduled = `Days for shipment (scheduled)` (promise); actual = `Days for shipping (real)`. Scheduled days are a **function of shipping mode** (verified: 1 distinct value per mode), so every 'by scheduled days' table is the same grouping as 'by mode'.")
R.sec("Late rate and delay by scheduled duration", ""); R.table(st[["sched", "n", "late_rate_%", "ci95_low_%", "ci95_high_%", "mean_actual", "median_actual", "mean_delay"]], "scheduled_rates.csv")
ct = pd.crosstab(ov.sched, ov.real); R.sec("Counts: scheduled days (rows) x actual days (columns)", ""); R.table(ct.reset_index(), floatfmt=".0f")
ctp = pd.crosstab(ov.sched, ov.real, normalize="index").mul(100).round(1); R.sec("Row %: distribution of actual days within each scheduled duration", ""); R.table(ctp.reset_index())
mx = pd.crosstab(ov["mode"], ov.sched); R.sec("Scheduled duration vs shipping mode", ""); R.table(mx.reset_index(), floatfmt=".0f")
rho, p = stats.spearmanr(ov.sched, ov.real); rho2, _ = stats.spearmanr(ov.sched, ov.delay)
R.sec("Statistical tests", assoc_line(ov, "sched", "scheduled days") + f"\n\nSpearman(scheduled, actual) = {rho:.3f} (p={p:.3g}); Spearman(scheduled, delay) = {rho2:.3f}. Kruskal-Wallis of actual days by scheduled days: H = {stats.kruskal(*[g.real.values for _, g in ov.groupby('sched')])[0]:,.0f}.")
hm = ov.pivot_table(index="region", columns="sched", values="late", aggfunc="mean").mul(100); hn = ov.pivot_table(index="region", columns="sched", values="late", aggfunc="size"); hm = hm.where(hn >= MIN_N_MULTI)
R.sec("Scheduled duration vs destination region", f"Late rate (%) by region x scheduled days (cells with n>={MIN_N_MULTI}) is in the heatmap below.")
fig, ax = plt.subplots(figsize=(7, 4)); ax.bar(st.sched.astype(str), st.n, color=C1); ax.set_xlabel("Scheduled shipping days"); ax.set_ylabel("Orders"); ax.set_title("Scheduled-duration distribution"); save(fig, D, "01_scheduled_distribution.png")
fig, ax = plt.subplots(figsize=(8, 4.5)); sns.heatmap(ctp, annot=True, fmt=".0f", cmap="Blues", ax=ax, cbar_kws={"label": "% of scheduled group"}); ax.set_xlabel("Actual shipping days"); ax.set_ylabel("Scheduled shipping days"); ax.set_title("Actual days by scheduled duration (row %)"); save(fig, D, "02_actual_vs_scheduled.png")
rate_bar(st.assign(sched=st.sched.astype(str) + " days"), "sched", "Late rate by scheduled duration (95% CI)", lambda f: save(f, D, "03_late_by_scheduled.png"), figsize=(7, 3.5))
cc = pd.crosstab(ov.sched, ov.real); fig, ax = plt.subplots(figsize=(6.5, 5)); sc = ax.scatter(*np.array([(a, b) for a in cc.index for b in cc.columns]).T, s=[cc.loc[a, b] / cc.values.max() * 1800 + 5 for a in cc.index for b in cc.columns], color=C1, alpha=.6); ax.plot([0, 6], [0, 6], color=C2, ls="--", label="actual = scheduled"); ax.set_xlabel("Scheduled days"); ax.set_ylabel("Actual days"); ax.set_title(f"Scheduled vs actual days (bubble = orders, n={NV:,})"); ax.legend(); save(fig, D, "04_scheduled_vs_actual_scatter.png")
fig, ax = plt.subplots(figsize=(7, 8)); sns.heatmap(hm, annot=True, fmt=".0f", cmap="RdYlBu_r", ax=ax, cbar_kws={"label": "Late rate (%)"}); ax.set_title("Late rate (%) by region x scheduled days"); save(fig, D, "05_region_scheduled_heatmap.png")
for f, c in [("01_scheduled_distribution.png", "Scheduled distribution"), ("02_actual_vs_scheduled.png", "Actual vs scheduled"), ("03_late_by_scheduled.png", "Late by scheduled"), ("04_scheduled_vs_actual_scatter.png", "Scatter"), ("05_region_scheduled_heatmap.png", "Region x scheduled")]: R.fig(f, c)
R.sec("Interpretation", "- Actual shipping time is similar across modes (see row % table), but the promise differs by mode (0, 1, 2 or 4 days). Lateness therefore mainly reflects **how tight the promise is**, not how slow the actual shipping is.\n- Important checks for the business: a 100% late rate for a mode means actual days always exceeded the promise; confirm that scheduled days for this mode are realistic and not a data-definition artefact.\n- This pattern describes *commitments* (known at order creation if mode is chosen) vs *outcomes* (known only after delivery).")
R.sec("Candidate ML features", "`Days for shipment (scheduled)` / `scheduled_duration_group`: approved candidate for order-creation (if known at creation), but fully redundant with `Shipping Mode`: keep one for linear models. Never include actual days.")
R.sec("Limitations", "Only 4 distinct scheduled values; no continuous variation to learn from.")
R.save(); KEY["sched"] = st[["sched", "n", "late_rate_%", "mean_actual"]].values.tolist(); KEY["ctp"] = ctp.to_dict()

# =============== PATTERN 11 ===============
D = folder("patterns", "origin_destination"); R = Report(D, "Pattern 11: Origin-destination patterns")
ov["route"] = ov.cust_country + " -> " + ov.country
rt = rate_table(ov, "route", MIN_N_MULTI); rs = rt[rt.n >= MIN_N]
R.sec("Status", "**True origin-destination (route) analysis cannot be completed reliably.** Searched all columns: there is **no origin, warehouse, depot, carrier, port or dispatch-location field**. `Latitude`/`Longitude` equal the **customer's residence** (country means: EE. UU. 36.8/-96.3; Puerto Rico 18.4/-66.6), not a shipping origin, and the customer country is never equal to the order country (0% of rows).")
R.sec("Exploratory proxy (not a real route)", f"For transparency only: *customer residence country -> destination country* pairs. Pairs: {len(rt)} with n>={MIN_N_MULTI}; {len(rs)} with n>={MIN_N}. Customer country has just 2 values, so this mostly repeats the destination-country analysis (Pattern 3). **Do not treat as route performance.**")
if len(rs): R.table(rs.sort_values("n", ascending=False)[["route", "n", "late_rate_%", "ci95_low_%", "ci95_high_%"]], "route_proxy_rates.csv", maxrows=15)
chi, p, dof, v = chi2_v(ov[ov.route.isin(rs.route)], "route") if len(rs) > 1 else (np.nan,) * 4
R.parts.append(f"\nChi-square (pairs n>={MIN_N}): chi2 = {chi:,.1f}, dof = {dof}, p = {p:.3g}, Cramer's V = {v:.3f}.\n")
hm = ov.pivot_table(index="cust_country", columns="region", values="late", aggfunc="mean").mul(100); hn = ov.pivot_table(index="cust_country", columns="region", values="late", aggfunc="size"); hm = hm.where(hn >= MIN_N_MULTI)
fig, ax = plt.subplots(figsize=(13, 3)); sns.heatmap(hm, annot=True, fmt=".0f", cmap="RdYlBu_r", ax=ax, cbar_kws={"label": "Late rate (%)"}); ax.set_title(f"Exploratory: late rate (%) customer country x destination region (n>={MIN_N_MULTI}; not a true route)"); plt.setp(ax.get_xticklabels(), rotation=60, ha="right", fontsize=7); save(fig, D, "01_proxy_heatmap.png")
t = rs.sort_values("n", ascending=False).head(15)
if len(t): rate_bar(t, "route", "Exploratory proxy: top 15 pairs by volume, late rate (95% CI)", lambda f: save(f, D, "02_proxy_top_pairs.png"), figsize=(9, 5.5))
R.fig("01_proxy_heatmap.png", "Proxy heatmap"); 
if len(t): R.fig("02_proxy_top_pairs.png", "Top proxy pairs")
R.sec("Not produced", "Route map (no valid origin or destination coordinates), route volume/late-rate rankings, route consistency over time, mode-by-route analysis.")
R.sec("Additional data required", "Origin warehouse/depot ID and location, carrier, dispatch timestamp, and destination coordinates or standard postal codes.")
R.sec("Candidate ML features", "None approved. `route_historical_late_rate` is **unavailable** until origin data exists. A destination-based substitute (mode x region history) is evaluated in Pattern 12.")
R.save()

# =============== PATTERN 12 ===============
D = folder("patterns", "historical_delivery"); R = Report(D, "Pattern 12: Historical delivery-performance patterns")
ref = auc(y, ov.pmode.values)
R.sec("Definitions and data used", base + f"\n\nEvery history feature is **past-only**: for an order created at time T, only earlier orders of the same group whose `shipping date` (used as the completion time) is strictly before T are counted. History is undefined (missing) when no completed prior order exists. Univariate AUC is used only to *describe* signal; it is **not** model performance.\n\nReference: AUC of the shipping-mode late rate alone (full-sample rates, 4 groups) = **{ref:.3f}**.")
R.sec("History features: coverage and univariate signal", ""); R.table(HF, floatfmt=".3f")
# first-order completeness for groups
cov = []
for nm in ["customer", "country", "region", "mode", "category", "mode_x_region"]:
    pn = H[nm][0]; cov.append({"Group": nm, "orders with >=1 prior": f"{(pn>=1).mean()*100:.1f}%", "median prior orders": float(np.median(pn)), "orders with >=30 prior": f"{(pn>=30).mean()*100:.1f}%"})
R.sec("History depth", ""); R.table(pd.DataFrame(cov))
# time stability by mode and region group
ov["half"] = ov.order_dt.dt.year.astype(str) + "H" + ((ov.order_dt.dt.month > 6) + 1).astype(str)
sm = ov.pivot_table(index="mode", columns="half", values="late", aggfunc="mean").mul(100).round(1); sn = ov.pivot_table(index="mode", columns="half", values="late", aggfunc="size")
R.sec("Stability over time: late rate (%) by mode and half-year", ""); R.table(sm.reset_index())
reg_year = ov.pivot_table(index="region", columns="year", values="late", aggfunc="mean").mul(100).round(1)
r_sd = reg_year.std(axis=1).mean(); R.sec("Stability over time: region x year", f"Mean across-year standard deviation of regional late rate = {r_sd:.2f} pp (noise expectation for ~{ov.groupby(['region','year']).size().median():.0f} orders/cell ≈ {np.sqrt(OV*(100-OV)/ov.groupby(['region','year']).size().median()):.2f} pp).")
# graphs
fig, ax = plt.subplots(figsize=(8, 4)); t = HF[HF["min prior orders"].isin([3, 30])].copy(); t["label"] = t["History feature"].str.replace("prior late rate by ", "") + " (>=" + t["min prior orders"].astype(str) + ")"
ax.barh(t.label, t["univariate AUC"], color=C1); ax.axvline(.5, color=C2, ls="--", label="No information (0.5)"); ax.axvline(ref, color="#27ae60", ls=":", label=f"Mode-only reference ({ref:.3f})"); ax.set_xlim(.45, max(.75, ref + .03)); ax.set_xlabel("Univariate AUC (descriptive)"); ax.set_title("Signal in past-only history features"); ax.legend(fontsize=8); ax.invert_yaxis(); save(fig, D, "01_history_signal.png")
fig, ax = plt.subplots(figsize=(11, 4)); mm = ov.pivot_table(index="ym", columns="mode", values="late", aggfunc="mean").mul(100)
for c in mm: ax.plot(np.arange(len(mm)), mm[c], label=c, marker="o", ms=2)
ax.set_xticks(np.arange(len(mm))[::3]); ax.set_xticklabels(mm.index.astype(str)[::3], rotation=45, ha="right"); ax.set_ylabel("Late rate (%)"); ax.set_title("Historical performance over time by shipping mode (monthly)"); ax.legend(fontsize=8, ncol=4); save(fig, D, "02_mode_over_time.png")
fig, ax = plt.subplots(figsize=(9, 5)); ro = ov.groupby("region").agg(r=("late", "mean"), n=("late", "size")).sort_values("r"); ax.barh(ro.index, ro.r * 100, color=C1); ax.axvline(OV, color=C2, ls="--"); ax.set_xlabel("Historical late rate (%), all years"); ax.set_title("Historical performance by destination region (23 regions; every n>=100)"); save(fig, D, "03_region_history.png")
ov["cust_hist_group"] = pd.cut(ov.h_customer_n, [-1, 0, 2, 4, 999], labels=["No history", "1-2 prior", "3-4 prior", "5+ prior"]); cg = rate_table(ov, "cust_hist_group", MIN_N)
rate_bar(cg, "cust_hist_group", "Late rate by customer-history depth (95% CI)", lambda f: save(f, D, "04_customer_group.png"), figsize=(7, 3.5))
for f, c in [("01_history_signal.png", "History signal"), ("02_mode_over_time.png", "Mode over time"), ("03_region_history.png", "Region history"), ("04_customer_group.png", "Customer group")]: R.fig(f, c)
best = HF.dropna(subset=["mean within-mode AUC"]).sort_values("mean within-mode AUC", ascending=False).iloc[0]
R.sec("Interpretation", f"- Mode-only reference AUC is {ref:.3f}. The strongest history feature **within shipping mode** is `{best['History feature']}` with mean within-mode AUC {best['mean within-mode AUC']:.3f}; values near 0.5 mean the history adds little beyond mode.\n- Customer/destination/category histories are noisy and, per Patterns 3, 7 and 8, mostly mirror chance variation.\n- History features are valid only when built strictly past-only (as done here); building them over the full dataset would leak future outcomes.")
R.sec("Candidate ML features", "`mode_historical_late_rate` (conditional: nearly constant per mode), `mode_x_region_historical_late_rate` (conditional), `customer_prior_late_rate` and `category_historical_late_rate` (conditional / weak). All must be recomputed inside each training fold with the same past-only rule and a smoothing/minimum-count rule.")
R.sec("Limitations", "Completion time is approximated; no carrier or route history is available; history is sparse early in the period.")
R.save(); KEY["hist"] = (ref, HF.to_dict("records"))

# =============== PATTERN 13 ===============
D = folder("patterns", "order_volume"); R = Report(D, "Pattern 13: Order-volume patterns")
dd = ov.groupby("date").agg(n=("late", "size"), late=("late", "mean"), pm=("pmode", "mean")).reset_index(); dd["year"] = dd.date.dt.year
R.sec("Definitions and data used", base + f"\n\nVolume = valid orders created per calendar day (n days = {len(dd):,}); late rate per day uses the same orders. **No capacity, staffing or warehouse-throughput data exists**, so any volume-delay relation is descriptive and cannot show cause.")
R.sec("Daily/weekly/monthly volume", f"Daily orders: mean {dd.n.mean():.1f}, median {dd.n.median():.0f}, SD {dd.n.std():.1f}, min {dd.n.min()}, max {dd.n.max()}; yearly mean daily volume: " + ", ".join(f"{y_} = {v_:.1f}" for y_, v_ in dd.groupby("year").n.mean().items()) + ".")
thr = dd.n.quantile(.9); dd["hv"] = np.where(dd.n >= thr, "High-volume days (top 10%)", "Other days")
oh = ov.merge(dd[["date", "hv", "n"]].rename(columns={"n": "day_vol"}), on="date")
ht = rate_table(oh, "hv", MIN_N); chi, p, dof, v = chi2_v(oh, "hv")
# within-year definition
dd["thr_y"] = dd.groupby("year").n.transform(lambda s: s.quantile(.9)); dd["hv_y"] = np.where(dd.n >= dd.thr_y, "High (top 10% within year)", "Other"); oh = oh.merge(dd[["date", "hv_y"]], on="date"); ht2 = rate_table(oh, "hv_y", MIN_N); chi2_, p2_, _, v2_ = chi2_v(oh, "hv_y")
R.sec("High-volume days: late rate", f"Definition A: day volume >= {thr:.0f} orders (global 90th percentile). Chi-square p = {p:.3g}, V = {v:.3f}.\n"); R.table(ht[["hv", "n", "late_rate_%", "ci95_low_%", "ci95_high_%"]])
R.parts.append(f"\nDefinition B (within-year 90th percentile, removes the year trend): chi-square p = {p2_:.3g}, V = {v2_:.3f}.\n"); R.table(ht2[["hv_y", "n", "late_rate_%", "ci95_low_%", "ci95_high_%"]])
dm = dd[dd.n >= 10]; rho, pr = stats.spearmanr(dm.n, dm.late); dd["resid"] = dd.late - dd.pm; dm = dd[dd.n >= 10]; rho_r, pr_r = stats.spearmanr(dm.n, dm.resid)
R.sec("Volume vs late rate (daily)", f"Days with >=10 orders: {len(dm):,}. Spearman(volume, daily late rate) = {rho:.3f} (p={pr:.3g}). After removing the effect of each day's shipping-mode mix (late rate minus mode-expected rate): Spearman = {rho_r:.3f} (p={pr_r:.3g}).")
rv = ov.groupby("region").size().sort_values(ascending=False); sh = rv / rv.sum(); hhi = (sh ** 2).sum()
mv = ov.groupby("mode").size()
R.sec("Regional concentration", f"{len(rv)} regions; top-3 regions hold {sh.head(3).sum()*100:.1f}% of orders; Herfindahl index = {hhi:.3f} (1/{len(rv)} = {1/len(rv):.3f} would be perfectly even).\n"); R.table(rv.rename_axis("region").reset_index(name="orders").assign(**{"share_%": (sh.values * 100).round(1)}), "region_volume.csv", maxrows=23)
R.sec("Volume by shipping mode", ""); R.table(mv.rename_axis("mode").reset_index(name="orders").assign(**{"share_%": (mv.values / NV * 100).round(1)}))
# regional monthly volume vs late (region-month cells)
rm = ov.groupby(["region", "ym"]).agg(n=("late", "size"), r=("late", "mean"), pm=("pmode", "mean")).reset_index(); rm = rm[rm.n >= 20]; rho_rm, p_rm = stats.spearmanr(rm.n, rm.r - rm.pm)
R.sec("Region-month volume vs mode-adjusted late rate", f"Region-month cells with >=20 orders: {len(rm):,}. Spearman(volume, late rate minus mode-expected) = {rho_rm:.3f} (p={p_rm:.3g}).")
fig, ax = plt.subplots(figsize=(11, 4)); ax.plot(dd.date, dd.n, color=C3, lw=.6, label="Daily orders"); ax.plot(dd.date, dd.n.rolling(30, center=True).mean(), color=C1, lw=2, label="30-day mean"); ax.set_ylabel("Orders per day"); ax.set_title(f"Daily order volume (valid orders, n={NV:,})"); ax.legend(); save(fig, D, "01_daily_monthly_volume.png")
fig, ax = plt.subplots(figsize=(8, 6)); ax.barh(rv.index[::-1], rv.values[::-1], color=C1); ax.set_xlabel("Orders"); ax.set_title("Order volume by destination region"); save(fig, D, "02_region_volume.png")
fig, ax = plt.subplots(figsize=(7, 4.5)); ax.scatter(dm.n, dm.late * 100, s=8, alpha=.4, color=C1); z = np.polyfit(dm.n, dm.late * 100, 1); xs = np.linspace(dm.n.min(), dm.n.max(), 50); ax.plot(xs, np.polyval(z, xs), color=C2, label=f"Linear fit; Spearman={rho:.3f}"); ax.set_xlabel("Orders per day"); ax.set_ylabel("Daily late rate (%)"); ax.set_title(f"Daily volume vs late rate ({len(dm):,} days with >=10 orders)"); ax.legend(); save(fig, D, "03_volume_vs_late.png")
fig, ax = plt.subplots(figsize=(7, 4)); tt_ = ht2.copy(); ax.bar(tt_.hv_y, tt_["late_rate_%"], yerr=[tt_["late_rate_%"] - tt_["ci95_low_%"], tt_["ci95_high_%"] - tt_["late_rate_%"]], color=[C2, C1], capsize=4); [ax.text(i, 1, f"n={n:,}", ha="center", color="white", fontsize=9) for i, n in enumerate(tt_.n)]; ax.set_ylim(0, 100); ax.set_ylabel("Late rate (%)"); ax.set_title("Late rate: high-volume days vs other days (within-year definition)"); save(fig, D, "04_high_volume_comparison.png")
for f, c in [("01_daily_monthly_volume.png", "Daily volume trend"), ("02_region_volume.png", "Regional volume"), ("03_volume_vs_late.png", "Volume vs late"), ("04_high_volume_comparison.png", "High vs normal")]: R.fig(f, c)
R.sec("Interpretation", f"- High-volume vs other days: late rates {ht2['late_rate_%'].iloc[0]:.1f}% vs {ht2['late_rate_%'].iloc[1]:.1f}% (V = {v2_:.3f}); daily Spearman {rho:.3f}, mode-adjusted {rho_r:.3f}.\n- {'No evidence that busy days are later.' if abs(rho_r)<.1 and v2_<.05 else 'There is a measurable association; it does not prove a workload effect.'} Capacity data would be required to test a workload mechanism.")
R.sec("Candidate ML features", "`orders_same_day_count`, `orders_same_day_region_count`, rolling 7-day order count (conditional: must be computed from orders created before the prediction time only; at order creation use counts of earlier orders, not the whole day).")
R.sec("Limitations", "Same-day totals include orders created after a given order, so they are **future-derived** for early-day orders; any feature must use prior-only counts. No capacity data.")
R.save(); KEY["vol"] = dict(v2=v2_, rho=rho, rho_r=rho_r, hv=ht2[["hv_y", "n", "late_rate_%"]].values.tolist(), rho_rm=rho_rm)
pd.to_pickle(KEY, "key_b.pkl")
for k, v in KEY.items(): print(k, v)
print(HF.to_string())
