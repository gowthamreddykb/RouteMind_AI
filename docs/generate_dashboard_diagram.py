import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_kpi_card(ax, x, y, w, h, title, val, delta, bg, border, text_col, num_col, delta_col):
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    ax.text(x + 0.20, y + h - 0.35, title, ha='left', va='center', color='#94a3b8' if text_col=='#f8fafc' else '#64748b', fontsize=8.2, fontweight='bold')
    ax.text(x + 0.20, y + h - 0.85, val, ha='left', va='center', color=num_col, fontsize=16, fontweight='bold', fontfamily='sans-serif')
    ax.text(x + 0.20, y + 0.30, delta, ha='left', va='center', color=delta_col, fontsize=7.5, fontfamily='sans-serif')

def draw_chart_box(ax, x, y, w, h, title, chart_type, bg, border, title_bg, text_col):
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    th = 0.42
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.2, edgecolor=border, facecolor=title_bg)
    ax.add_patch(tbox)
    ax.text(x + 0.20, y + h - th/2, title, ha='left', va='center',
            color=text_col, fontsize=8.8, fontweight='bold', fontfamily='sans-serif')
    ax.plot([x, x + w], [y + h - th, y + h - th], color=border, lw=1.0)

def render_dashboard_layout(theme='dark'):
    fig, ax = plt.subplots(figsize=(15, 10.5), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        title_bg = '#1e293b'
        border_col = '#3e4046'
        text_col = '#f8fafc'
        sub_col = '#cbd5e1'
        c_blue = '#38bdf8'
        c_green = '#34d399'
        c_amber = '#fbbf24'
        c_red = '#f87171'
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        title_bg = '#e2e8f0'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        sub_col = '#475569'
        c_blue = '#0284c7'
        c_green = '#059669'
        c_amber = '#d97706'
        c_red = '#dc2626'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    # 1. Top Section: 4 KPI Cards (y = 8.4, h = 1.6)
    kw = 3.3
    kh = 1.5
    draw_kpi_card(ax, 0.6, 8.4, kw, kh, "TOTAL CONSIGNMENTS", "1,248", "↑ 12% from last week", box_bg, border_col, text_col, c_blue, c_green)
    draw_kpi_card(ax, 4.3, 8.4, kw, kh, "ON-TIME DELIVERY RATE", "94.2%", "↑ +1.8% fleet target", box_bg, border_col, text_col, c_green, c_green)
    draw_kpi_card(ax, 8.0, 8.4, kw, kh, "HIGH-RISK SHIPMENTS", "48", "↓ 6 fewer than yesterday", box_bg, border_col, text_col, c_red, c_red)
    draw_kpi_card(ax, 11.7, 8.4, kw, kh, "ACTIVE EXCEPTIONS", "14", "9 under investigation", box_bg, border_col, text_col, c_amber, c_amber)

    # 2. Bottom Section: 4 Charts (2x2 Grid)
    cw = 6.9
    ch = 3.5

    # Chart 1: Volume by Destination Region (Top-Left, x=0.6, y=4.4)
    draw_chart_box(ax, 0.6, 4.4, cw, ch, "1. Shipment Volume by Destination Region", "bar", box_bg, border_col, title_bg, text_col)
    # Mini Bar Graphic
    regions = ["Europe", "North America", "East Asia", "Latin America", "Middle East"]
    vols = [420, 360, 240, 130, 98]
    max_v = 450
    for i, (r, v) in enumerate(zip(regions, vols)):
        bx = 0.9 + i * 1.3
        bh = (v / max_v) * 2.2
        r_box = patches.Rectangle((bx, 4.8), 0.8, bh, facecolor=c_blue, edgecolor='none', alpha=0.9)
        ax.add_patch(r_box)
        ax.text(bx + 0.4, 4.8 + bh + 0.08, str(v), ha='center', va='bottom', color=text_col, fontsize=7.5, fontweight='bold')
        ax.text(bx + 0.4, 4.6, r[:6], ha='center', va='top', color=sub_col, fontsize=7.0)

    # Chart 2: Shipment Status Overview (Top-Right, x=8.0, y=4.4)
    draw_chart_box(ax, 8.0, 4.4, cw, ch, "2. Shipment Status Overview", "bar", box_bg, border_col, title_bg, text_col)
    statuses = ["CREATED", "CONFIRMED", "DISPATCHED", "IN_TRANSIT", "DELIVERED"]
    s_vols = [110, 185, 290, 430, 233]
    for i, (s, v) in enumerate(zip(statuses, s_vols)):
        bx = 8.3 + i * 1.3
        bh = (v / 450) * 2.2
        s_box = patches.Rectangle((bx, 4.8), 0.8, bh, facecolor=c_green, edgecolor='none', alpha=0.9)
        ax.add_patch(s_box)
        ax.text(bx + 0.4, 4.8 + bh + 0.08, str(v), ha='center', va='bottom', color=text_col, fontsize=7.5, fontweight='bold')
        ax.text(bx + 0.4, 4.6, s[:6], ha='center', va='top', color=sub_col, fontsize=7.0)

    # Chart 3: Overall Shipment Risk Distribution (Bottom-Left, x=0.6, y=0.5)
    draw_chart_box(ax, 0.6, 0.5, cw, ch, "3. Overall Shipment Risk Distribution", "doughnut", box_bg, border_col, title_bg, text_col)
    # Donut pie representation
    donut_center = (2.4, 2.1)
    wedges, texts = ax.pie([72, 21, 7], center=donut_center, radius=1.2,
                           colors=[c_green, c_amber, c_red],
                           wedgeprops=dict(width=0.45, edgecolor=bg_main, lw=2))
    ax.text(donut_center[0], donut_center[1], "1,248\nFleet", ha='center', va='center', color=text_col, fontsize=9.0, fontweight='bold')
    
    # Legend for Donut
    ax.plot([4.4], [2.7], marker='s', markersize=9, color=c_green)
    ax.text(4.7, 2.7, "Low Risk (72% - 898 Shipments)", color=sub_col, fontsize=8.0, va='center')
    ax.plot([4.4], [2.1], marker='s', markersize=9, color=c_amber)
    ax.text(4.7, 2.1, "Medium Risk (21% - 262 Shipments)", color=sub_col, fontsize=8.0, va='center')
    ax.plot([4.4], [1.5], marker='s', markersize=9, color=c_red)
    ax.text(4.7, 1.5, "High Risk (7% - 88 Shipments)", color=sub_col, fontsize=8.0, va='center')

    # Chart 4: Exception Analysis by Priority (Bottom-Right, x=8.0, y=0.5)
    draw_chart_box(ax, 8.0, 0.5, cw, ch, "4. Exception Analysis by Priority", "bar", box_bg, border_col, title_bg, text_col)
    priorities = ["Normal", "High", "Urgent", "Critical"]
    p_vols = [18, 12, 7, 3]
    p_cols = [c_blue, c_amber, '#ea580c', c_red]
    for i, (p, v, col) in enumerate(zip(priorities, p_vols, p_cols)):
        bx = 8.5 + i * 1.6
        bh = (v / 20) * 2.2
        p_box = patches.Rectangle((bx, 0.9), 1.0, bh, facecolor=col, edgecolor='none', alpha=0.9)
        ax.add_patch(p_box)
        ax.text(bx + 0.5, 0.9 + bh + 0.08, f"{v}", ha='center', va='bottom', color=text_col, fontsize=8.0, fontweight='bold')
        ax.text(bx + 0.5, 0.7, p, ha='center', va='top', color=sub_col, fontsize=7.5)

    ax.set_xlim(0, 15.5)
    ax.set_ylim(0.1, 10.4)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\dashboard_analytics_kpi_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_dashboard_layout('light')
render_dashboard_layout('dark')
