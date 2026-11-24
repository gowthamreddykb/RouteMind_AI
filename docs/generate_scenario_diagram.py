import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_step_card(ax, x, y, w, h, step_tag, title, details, bg, border, title_bg, text_col, sub_col, tag_col):
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    th = 0.50
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.2, edgecolor=border, facecolor=title_bg)
    ax.add_patch(tbox)
    
    # Tag
    badge = patches.FancyBboxPatch((x + 0.15, y + h - th + 0.10), 0.70, 0.30,
                                  boxstyle="round,pad=0,rounding_size=0.04",
                                  linewidth=0.8, edgecolor=border, facecolor=tag_col)
    ax.add_patch(badge)
    ax.text(x + 0.50, y + h - th/2, step_tag, ha='center', va='center',
            color='#ffffff', fontsize=7.2, fontweight='bold', fontfamily='sans-serif')

    # Title
    ax.text(x + 0.95, y + h - th/2, title, ha='left', va='center',
            color=text_col, fontsize=8.8, fontweight='bold', fontfamily='sans-serif')
    ax.plot([x, x + w], [y + h - th, y + h - th], color=border, lw=1.0)

    # Details lines
    cy = y + h - th - 0.22
    for line in details:
        ax.text(x + 0.18, cy, line, ha='left', va='center', color=sub_col, fontsize=7.5, fontfamily='sans-serif')
        cy -= 0.24

def render_scenario_walkthrough(theme='dark'):
    fig, ax = plt.subplots(figsize=(15, 10.5), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        title_bg = '#1e293b'
        border_col = '#3e4046'
        text_col = '#f8fafc'
        sub_col = '#cbd5e1'
        arrow_col = '#94a3b8'
        c_step1 = '#38bdf8' # Cyan
        c_step2 = '#f59e0b' # Amber
        c_step3 = '#a855f7' # Purple
        c_step4 = '#ef4444' # Red
        c_step5 = '#3b82f6' # Blue
        c_step6 = '#10b981' # Green
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        title_bg = '#e2e8f0'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        sub_col = '#475569'
        arrow_col = '#475569'
        c_step1 = '#0284c7'
        c_step2 = '#d97706'
        c_step3 = '#9333ea'
        c_step4 = '#dc2626'
        c_step5 = '#2563eb'
        c_step6 = '#059669'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    w = 4.4
    h = 2.4

    # Grid: 2 rows x 3 columns
    # Row 1 (y = 5.8): Step 1 (Left) -> Step 2 (Center) -> Step 3 (Right)
    # Row 2 (y = 1.0): Step 6 (Left) <- Step 5 (Center) <- Step 4 (Right)

    # 1. Step 1: Shipment Creation & Baseline Prediction
    draw_step_card(ax, 0.6, 5.8, w, h, "STEP 1", "Shipment Creation",
                   ["• Consignment: SHP-10042 (Rotterdam -> Hamburg)",
                    "• Cargo: Commercial Electronics (Container MSCU-882)",
                    "• Scheduled Transit Days: 4.0 Days",
                    "• ML Stage 1: Order Creation Probability = 22%",
                    "• Initial Risk Category: LOW RISK (Safe)"],
                   box_bg, border_col, title_bg, text_col, sub_col, c_step1)

    # 2. Step 2: Warehouse Dispatch & Risk Spike
    draw_step_card(ax, 5.4, 5.8, w, h, "STEP 2", "Dispatch & Delay Surge",
                   ["• Vessel Casts Off: MV Arctic Voyager (Dispatched)",
                    "• Adverse Weather & Port Dwell Time finalized",
                    "• ML Stage 2: Late Probability jumps to 68%",
                    "• CatBoost Delay Estimation: +2.0 Days Late",
                    "• Status auto-flags: HIGH RISK ALERT!"],
                   box_bg, border_col, title_bg, text_col, sub_col, c_step2)

    # 3. Step 3: SHAP Root-Cause Explainability
    draw_step_card(ax, 10.2, 5.8, w, h, "STEP 3", "SHAP Risk Explanation",
                   ["• Operator inspects 'AI Risk Drivers' panel",
                    "• Carrier Historical Delay Rate: +24% Push",
                    "• Destination Port Berth Congestion: +18% Push",
                    "• Scheduled Buffer Margin: -8% Reduction",
                    "• Transparent explanation replaces black box"],
                   box_bg, border_col, title_bg, text_col, sub_col, c_step3)

    # Row 1 Arrows: 1 -> 2 -> 3
    ax.annotate("", xy=(5.4, 7.0), xytext=(5.0, 7.0), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6))
    ax.annotate("", xy=(10.2, 7.0), xytext=(9.8, 7.0), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6))

    # Turn down from Step 3 to Step 4
    ax.plot([12.4, 12.4], [5.8, 4.3], color=arrow_col, lw=1.6)
    ax.annotate("", xy=(12.4, 3.4), xytext=(12.4, 4.3), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6))

    # 4. Step 4: Exception Creation & Manager Escalation
    draw_step_card(ax, 10.2, 1.0, w, h, "STEP 4", "Exception & Escalation",
                   ["• Dispatcher creates Exception Ticket (Severity: High)",
                    "• Imminent customer SLA breach detected",
                    "• Ticket escalated to Operations Manager",
                    "• Escalation record saved in manager_escalations",
                    "• Priority assigned: CRITICAL"],
                   box_bg, border_col, title_bg, text_col, sub_col, c_step4)

    # 5. Step 5: AI Copilot & Automated SLA Notice
    draw_step_card(ax, 5.4, 1.0, w, h, "STEP 5", "AI Copilot & SLA Notice",
                   ["• AI Copilot suggests: 'Request Priority Berth Handling'",
                    "• GenAI auto-drafts Carrier SLA Breach Notice",
                    "• Manager reviews and edits draft email",
                    "• Email sent via Gmail SMTP to Carrier Operations",
                    "• Delivery confirmation logged in database"],
                   box_bg, border_col, title_bg, text_col, sub_col, c_step5)

    # 6. Step 6: Arrival, Delivery & Audit Completion
    draw_step_card(ax, 0.6, 1.0, w, h, "STEP 6", "Delivery & Completion",
                   ["• Carrier accelerates drayage; berth secured",
                    "• Arrived at Hamburg Haven; customs cleared",
                    "• Proof of Delivery (POD) confirmed by consignee",
                    "• Final Status updated: DELIVERED & CLOSED",
                    "• Audit log sealed in audit_logs table"],
                   box_bg, border_col, title_bg, text_col, sub_col, c_step6)

    # Row 2 Arrows: 4 -> 5 -> 6 (Right to Left)
    ax.annotate("", xy=(9.8, 2.2), xytext=(10.2, 2.2), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6))
    ax.annotate("", xy=(5.0, 2.2), xytext=(5.4, 2.2), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6))

    # Bottom Tagline
    banner = patches.FancyBboxPatch((0.6, 0.2), 14.0, 0.55, boxstyle="round,pad=0,rounding_size=0.06",
                                   linewidth=1.1, edgecolor=border_col, facecolor=title_bg)
    ax.add_patch(banner)
    ax.text(7.6, 0.47, "Outcome: Proactive ML prediction and automated exception escalation prevented an expensive customer SLA breach penalty.",
            ha='center', va='center', color=c_step6, fontsize=8.5, fontweight='bold', fontfamily='sans-serif')

    ax.set_xlim(0, 15.2)
    ax.set_ylim(0.0, 8.8)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\scenario_walkthrough_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_scenario_walkthrough('light')
render_scenario_walkthrough('dark')
