import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_ml_card(ax, x, y, w, h, title, subtitle, items, bg, border, title_bg, text_col, sub_col, tag_col):
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    th = 0.52
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.2, edgecolor=border, facecolor=title_bg)
    ax.add_patch(tbox)
    
    ax.text(x + 0.15, y + h - th/2, title, ha='left', va='center',
            color=text_col, fontsize=9.2, fontweight='bold', fontfamily='sans-serif')
    
    # Tag badge
    badge = patches.FancyBboxPatch((x + w - 0.95, y + h - th + 0.10), 0.82, 0.30,
                                  boxstyle="round,pad=0,rounding_size=0.04",
                                  linewidth=0.8, edgecolor=border, facecolor=tag_col)
    ax.add_patch(badge)
    ax.text(x + w - 0.54, y + h - th/2, subtitle, ha='center', va='center',
            color='#ffffff', fontsize=7.2, fontweight='bold', fontfamily='sans-serif')
    
    ax.plot([x, x + w], [y + h - th, y + h - th], color=border, lw=1.0)

    cy = y + h - th - 0.24
    for item in items:
        ax.text(x + 0.20, cy, item, ha='left', va='center', color=sub_col, fontsize=7.8, fontfamily='sans-serif')
        cy -= 0.25

def render_ml_diagram(theme='dark'):
    fig, ax = plt.subplots(figsize=(15, 9.5), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        title_bg = '#1e293b'
        border_col = '#3e4046'
        text_col = '#f8fafc'
        sub_col = '#cbd5e1'
        arrow_col = '#94a3b8'
        m1_col = '#3b82f6'  # Blue
        m2_col = '#8b5cf6'  # Purple
        m3_col = '#10b981'  # Green
        flask_col = '#f59e0b' # Amber
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        title_bg = '#e2e8f0'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        sub_col = '#475569'
        arrow_col = '#475569'
        m1_col = '#2563eb'
        m2_col = '#7c3aed'
        m3_col = '#059669'
        flask_col = '#d97706'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    w = 3.6
    h = 2.4

    # Top Level: Input Raw Features (y = 6.4)
    # Box 1: Order Booking Data
    draw_ml_card(ax, 0.6, 6.4, w, h, "Stage 1 Input Data", "BOOKING",
                 ["• Shipping Mode (Standard, First, Same Day)",
                  "• Customer Segment (Corporate, Home)",
                  "• Department & Product Category",
                  "• Scheduled Transit Days",
                  "• Origin & Destination Ports"],
                 box_bg, border_col, title_bg, text_col, sub_col, m1_col)

    # Box 2: Dispatch Operational Data
    draw_ml_card(ax, 5.8, 6.4, w, h, "Stage 2 Input Data", "DISPATCH",
                 ["• Confirmed Carrier Code & Vessel Name",
                  "• Warehouse Processing Duration",
                  "• Actual Dispatch Departure Hour",
                  "• Historical Carrier Delay Rate",
                  "• Port Congestion Index"],
                 box_bg, border_col, title_bg, text_col, sub_col, m2_col)

    # Box 3: Model 01 (Logistic Regression) - Mid-Left (y = 3.2)
    draw_ml_card(ax, 0.6, 3.2, w, h, "Model 01: Baseline Risk", "LOGISTIC REG",
                 ["• Algorithm: Scikit-Learn Logistic Regression",
                  "• Preprocessing: One-Hot Encoder + Scaler",
                  "• Execution: Immediate at Order Booking",
                  "• Output: Baseline Delay Probability (0-100%)",
                  "• Output: Initial Risk Tier (Low / Med / High)"],
                 box_bg, border_col, title_bg, text_col, sub_col, m1_col)

    # Box 4: Model 02 & Model 03 (XGBoost + CatBoost) - Mid-Center (y = 3.2)
    draw_ml_card(ax, 5.8, 3.2, w, h, "Model 02 & 03: Dispatch AI", "XGB + CATBOOST",
                 ["• Model 02: XGBoost Gradient Classifier",
                  "  -> Predicts Final Late Delivery Likelihood",
                  "• Model 03: CatBoost Regressor",
                  "  -> Predicts Exact Delay Duration (+Days)",
                  "• Threshold Optimization (Selected at 0.40)"],
                 box_bg, border_col, title_bg, text_col, sub_col, m2_col)

    # Box 5: Model Integration & Flask Control Tower - Right Side (y = 3.2)
    draw_ml_card(ax, 10.8, 3.2, 3.8, 5.6, "Flask Unified Inference Engine", "PRODUCTION",
                 ["1. Sub-second In-Memory Scoring (<50ms):",
                  "   Pre-trained .joblib artifacts loaded on startup",
                  "",
                  "2. Dual-Stage Execution Trigger:",
                  "   Stage 1 on POST /shipments/create",
                  "   Stage 2 on POST /shipments/status (DISPATCHED)",
                  "",
                  "3. Database Persistence:",
                  "   Saves probability into shipments table",
                  "   Logs granular score in model_scores table",
                  "",
                  "4. Operational Action Guard:",
                  "   If Late Probability ≥ 60% ->",
                  "   Auto-generate High-Risk Exception Alert!"],
                 box_bg, border_col, title_bg, text_col, sub_col, flask_col)

    # Bottom Banner: Model Explainability (y = 0.5)
    shap_box = patches.FancyBboxPatch((0.6, 0.5), 14.0, 1.8, boxstyle="round,pad=0,rounding_size=0.08",
                                     linewidth=1.2, edgecolor=border_col, facecolor=box_bg)
    ax.add_patch(shap_box)
    th_shap = 0.45
    tbox_shap = patches.FancyBboxPatch((0.6, 0.5 + 1.8 - th_shap), 14.0, th_shap, boxstyle="round,pad=0,rounding_size=0.08",
                                       linewidth=1.2, edgecolor=border_col, facecolor=title_bg)
    ax.add_patch(tbox_shap)
    ax.text(0.8, 0.5 + 1.8 - th_shap/2, "Explainable AI (XAI) & SHAP Risk Drivers", ha='left', va='center',
            color=text_col, fontsize=9.2, fontweight='bold', fontfamily='sans-serif')
    ax.text(1.0, 1.25, "• SHAP Feature Analysis reveals exact delay causes (e.g. 'Carrier historical late rate contributed +24% to risk')",
            color=sub_col, fontsize=8.2, fontfamily='sans-serif')
    ax.text(1.0, 0.85, "• Transforms black-box machine learning predictions into transparent, actionable operational intelligence for managers.",
            color=sub_col, fontsize=8.2, fontfamily='sans-serif')

    # Arrows
    # Data 1 -> Model 1
    ax.annotate("", xy=(2.4, 5.6), xytext=(2.4, 6.4), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    # Data 2 -> Model 2/3
    ax.annotate("", xy=(7.6, 5.6), xytext=(7.6, 6.4), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # Model 1 -> Flask Engine
    ax.plot([4.2, 5.0, 5.0, 10.8], [4.4, 4.4, 5.0, 5.0], color=arrow_col, lw=1.4)
    ax.annotate("", xy=(10.8, 5.0), xytext=(10.7, 5.0), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4))

    # Model 2/3 -> Flask Engine
    ax.annotate("", xy=(10.8, 4.4), xytext=(9.4, 4.4), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # Flask Engine -> SHAP banner
    ax.plot([12.7, 12.7, 10.0], [3.2, 2.5, 2.3], color=arrow_col, lw=1.4)
    ax.annotate("", xy=(10.0, 2.3), xytext=(10.1, 2.3), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4))

    ax.set_xlim(0, 15.2)
    ax.set_ylim(0.2, 9.2)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\ml_predictive_architecture_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_ml_diagram('light')
render_ml_diagram('dark')
