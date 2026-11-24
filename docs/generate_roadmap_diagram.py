import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_roadmap_milestone(ax, x, y, w, h, phase_num, horizon, title, items, bg, border, title_bg, text_col, sub_col, tag_col):
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    th = 0.52
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.2, edgecolor=border, facecolor=title_bg)
    ax.add_patch(tbox)
    
    badge = patches.FancyBboxPatch((x + 0.15, y + h - th + 0.10), 0.95, 0.30,
                                  boxstyle="round,pad=0,rounding_size=0.04",
                                  linewidth=0.8, edgecolor=border, facecolor=tag_col)
    ax.add_patch(badge)
    ax.text(x + 0.62, y + h - th/2, f"PHASE {phase_num}", ha='center', va='center',
            color='#ffffff', fontsize=7.2, fontweight='bold', fontfamily='sans-serif')

    ax.text(x + 1.25, y + h - th/2, title, ha='left', va='center',
            color=text_col, fontsize=8.8, fontweight='bold', fontfamily='sans-serif')
    ax.plot([x, x + w], [y + h - th, y + h - th], color=border, lw=1.0)

    # Horizon tag
    ax.text(x + w - 0.20, y + h - th - 0.20, horizon, ha='right', va='center', color=tag_col, fontsize=7.2, fontweight='bold')

    cy = y + h - th - 0.42
    for item in items:
        ax.text(x + 0.20, cy, item, ha='left', va='center', color=sub_col, fontsize=7.6, fontfamily='sans-serif')
        cy -= 0.25

def render_roadmap_diagram(theme='dark'):
    fig, ax = plt.subplots(figsize=(15, 8.5), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        title_bg = '#1e293b'
        border_col = '#3e4046'
        text_col = '#f8fafc'
        sub_col = '#cbd5e1'
        arrow_col = '#94a3b8'
        c_p1 = '#38bdf8' # Cyan
        c_p2 = '#a855f7' # Purple
        c_p3 = '#f59e0b' # Amber
        c_p4 = '#10b981' # Green
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        title_bg = '#e2e8f0'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        sub_col = '#475569'
        arrow_col = '#475569'
        c_p1 = '#0284c7'
        c_p2 = '#9333ea'
        c_p3 = '#d97706'
        c_p4 = '#059669'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    w = 3.3
    h = 2.7
    y_pos = 2.4

    # 4 Sequential Milestones along a clean timeline
    # Phase 1: Satellite AIS & IoT
    draw_roadmap_milestone(ax, 0.6, y_pos, w, h, 1, "Q1 - Q2", "Satellite AIS & IoT",
                          ["• Live satellite vessel tracking",
                           "• Container IoT temperature logs",
                           "• Real-time GPS coordinate feeds",
                           "• Automated port geofencing"],
                          box_bg, border_col, title_bg, text_col, sub_col, c_p1)

    # Phase 2: Autonomous Carrier Webhooks
    draw_roadmap_milestone(ax, 4.3, y_pos, w, h, 2, "Q3", "Carrier Webhook Ingestion",
                          ["• Direct EDI / API carrier links",
                           "• Automated terminal milestone sync",
                           "• AI multi-carrier quotation",
                           "• Self-healing reroute engine"],
                          box_bg, border_col, title_bg, text_col, sub_col, c_p2)

    # Phase 3: Mobile Native App
    draw_roadmap_milestone(ax, 8.0, y_pos, w, h, 3, "Q4", "Mobile Operations App",
                          ["• Native iOS & Android builds",
                           "• Instant push notifications",
                           "• Manager 1-click approvals",
                           "• Offline barcode container scan"],
                          box_bg, border_col, title_bg, text_col, sub_col, c_p3)

    # Phase 4: Multi-Echelon Digital Twin
    draw_roadmap_milestone(ax, 11.7, y_pos, w, h, 4, "Future", "Supply Chain Digital Twin",
                          ["• Global network simulation",
                           "• What-if disruption modeling",
                           "• Multi-tier supplier visibility",
                           "• Autonomous inventory rebalancing"],
                          box_bg, border_col, title_bg, text_col, sub_col, c_p4)

    # Timeline connecting line
    ax.plot([2.25, 13.35], [5.8, 5.8], color=arrow_col, lw=2.0, linestyle='--')

    # Milestone nodes on the timeline
    for x, c, p in zip([2.25, 5.95, 9.65, 13.35], [c_p1, c_p2, c_p3, c_p4], [1, 2, 3, 4]):
        circle = patches.Circle((x, 5.8), 0.22, facecolor=c, edgecolor=border_col, lw=1.5)
        ax.add_patch(circle)
        ax.text(x, 5.8, str(p), ha='center', va='center', color='#ffffff', fontsize=8.5, fontweight='bold')
        ax.annotate("", xy=(x, y_pos + h), xytext=(x, 5.58), arrowprops=dict(arrowstyle="-|>", color=c, lw=1.5))

    # Bottom Banner
    banner = patches.FancyBboxPatch((0.6, 0.6), 14.4, 1.0, boxstyle="round,pad=0,rounding_size=0.08",
                                   linewidth=1.1, edgecolor=border_col, facecolor=title_bg)
    ax.add_patch(banner)
    ax.text(7.8, 1.25, "Strategic Vision: Transforming RouteMind AI from a Predictive Control Tower into an Autonomous Global Logistics Ecosystem.",
            ha='center', va='center', color=text_col, fontsize=8.8, fontweight='bold', fontfamily='sans-serif')
    ax.text(7.8, 0.88, "Continuous integration of satellite telemetry, IoT telematics, and agentic AI will eliminate transit blindspots worldwide.",
            ha='center', va='center', color=sub_col, fontsize=8.0, fontfamily='sans-serif')

    ax.set_xlim(0, 15.6)
    ax.set_ylim(0.2, 6.8)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\future_enhancements_roadmap_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated roadmap: {out}")

render_roadmap_diagram('light')
render_roadmap_diagram('dark')
