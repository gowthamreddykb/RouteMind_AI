import matplotlib.pyplot as plt
import matplotlib.patches as patches

def render_shap_waterfall(theme='dark'):
    fig, ax = plt.subplots(figsize=(14, 8.5), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        card_bg = '#222327'
        border_col = '#3e4046'
        text_col = '#f8fafc'
        sub_col = '#cbd5e1'
        bar_pos = '#ef4444' # Red pushes risk UP
        bar_neg = '#10b981' # Green pushes risk DOWN
        base_col = '#3b82f6' # Blue base
        final_col = '#f59e0b' # Amber final risk
        line_col = '#64748b'
    else:
        bg_main = '#ffffff'
        card_bg = '#f8fafc'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        sub_col = '#475569'
        bar_pos = '#dc2626'
        bar_neg = '#059669'
        base_col = '#2563eb'
        final_col = '#d97706'
        line_col = '#94a3b8'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    # Waterfall elements:
    # 0: Base Rate (20%)
    # 1: Carrier Late History (+18%) -> 38%
    # 2: Port Congestion Index (+14%) -> 52%
    # 3: Warehouse Processing Time (+10%) -> 62%
    # 4: Favorable Shipping Lane Weather (-9%) -> 53%
    # 5: First-Class Priority Handling (-5%) -> 48%
    # 6: Final Risk Score (48% - Medium Risk)

    labels = [
        "Base Fleet Risk\n(Population Mean)",
        "Carrier Late History\n(+18% Risk Push)",
        "Port Congestion Index\n(+14% Risk Push)",
        "Warehouse Dwell Time\n(+10% Risk Push)",
        "Favorable Weather\n(-9% Risk Reduction)",
        "Priority Booking\n(-5% Risk Reduction)",
        "Final Predicted Risk\n(Shipment SHP-10042)"
    ]

    bottoms = [0, 20, 38, 52, 53, 48, 0]
    heights = [20, 18, 14, 10, -9, -5, 48]
    colors = [base_col, bar_pos, bar_pos, bar_pos, bar_neg, bar_neg, final_col]

    x_positions = [1.2, 3.2, 5.2, 7.2, 9.2, 11.2, 13.2]
    bar_width = 1.1

    # Draw bars
    for i in range(len(labels)):
        b = bottoms[i]
        h = heights[i]
        c = colors[i]
        x = x_positions[i]

        # In case of negative height: draw from b down to b+h
        if h < 0:
            rect = patches.FancyBboxPatch((x - bar_width/2, b + h), bar_width, abs(h),
                                         boxstyle="round,pad=0,rounding_size=0.06",
                                         linewidth=1.2, edgecolor=border_col, facecolor=c)
            ax.add_patch(rect)
            # Label inside/above bar
            ax.text(x, b + h/2, f"{h}%", ha='center', va='center', color='#ffffff', fontsize=9.5, fontweight='bold')
        else:
            rect = patches.FancyBboxPatch((x - bar_width/2, b), bar_width, h,
                                         boxstyle="round,pad=0,rounding_size=0.06",
                                         linewidth=1.2, edgecolor=border_col, facecolor=c)
            ax.add_patch(rect)
            ax.text(x, b + h/2, f"+{h}%" if i not in [0, 6] else f"{h}%", ha='center', va='center',
                    color='#ffffff', fontsize=9.5, fontweight='bold')

        # Connectors between waterfall steps
        if i < 5:
            next_start_y = bottoms[i] + heights[i]
            ax.plot([x + bar_width/2, x_positions[i+1] - bar_width/2], [next_start_y, next_start_y],
                    color=line_col, linestyle=':', lw=1.3)

    # Connect to final bar
    ax.plot([x_positions[5] + bar_width/2, x_positions[6] - bar_width/2], [48, 48],
            color=line_col, linestyle=':', lw=1.3)

    # X-axis Labels
    for x, lbl in zip(x_positions, labels):
        ax.text(x, -5.5, lbl, ha='center', va='top', color=text_col, fontsize=8.2, fontweight='bold', multialignment='center')

    # Gridlines and Y-axis
    for y in range(0, 80, 10):
        ax.axhline(y, color=border_col, linestyle='--', lw=0.7, alpha=0.6)
        ax.text(0.3, y, f"{y}%", ha='right', va='center', color=sub_col, fontsize=8.5)

    ax.text(0.3, 72, "Late Delivery Probability (%)", ha='left', va='center', color=text_col, fontsize=9.5, fontweight='bold')

    # Title & Legend Box
    leg_box = patches.FancyBboxPatch((4.5, 68), 9.8, 8.5, boxstyle="round,pad=0,rounding_size=0.08",
                                    linewidth=1.1, edgecolor=border_col, facecolor=card_bg)
    ax.add_patch(leg_box)
    ax.text(4.8, 73.5, "SHAP Risk Factor Legend:", color=text_col, fontsize=9.0, fontweight='bold')
    
    # Red bullet: Increases risk
    ax.plot([8.2], [73.5], marker='s', markersize=9, color=bar_pos)
    ax.text(8.5, 73.5, "Pushes Risk UP (Delay Driver)", color=sub_col, fontsize=8.0, va='center')
    
    # Green bullet: Decreases risk
    ax.plot([12.0], [73.5], marker='s', markersize=9, color=bar_neg)
    ax.text(12.3, 73.5, "Reduces Risk (Protective Factor)", color=sub_col, fontsize=8.0, va='center')

    ax.set_xlim(-0.2, 14.5)
    ax.set_ylim(-13.0, 78.0)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\shap_waterfall_explanation_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_shap_waterfall('light')
render_shap_waterfall('dark')
