import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_state_box(ax, x, y, w, h, state_num, title, desc, bg, border, title_bg, text_col, sub_col, num_col):
    # Main rounded card
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    # Header bar with number badge
    th = 0.50
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.2, edgecolor=border, facecolor=title_bg)
    ax.add_patch(tbox)
    
    badge = patches.Circle((x + 0.35, y + h - th/2), 0.18, facecolor=num_col, edgecolor=border, lw=1)
    ax.add_patch(badge)
    ax.text(x + 0.35, y + h - th/2, str(state_num), ha='center', va='center',
            color='#ffffff', fontsize=8.5, fontweight='bold', fontfamily='sans-serif')

    ax.text(x + 0.65, y + h - th/2, title, ha='left', va='center',
            color=text_col, fontsize=9.0, fontweight='bold', fontfamily='sans-serif')
    ax.plot([x, x + w], [y + h - th, y + h - th], color=border, lw=1.0)

    ax.text(x + w/2, y + (h - th)/2, desc, ha='center', va='center',
            color=sub_col, fontsize=7.6, fontfamily='sans-serif', multialignment='center')

def render_lifecycle_diagram(theme='dark'):
    fig, ax = plt.subplots(figsize=(15, 8.5), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        title_bg = '#1e293b'
        border_col = '#3e4046'
        text_col = '#f8fafc'
        sub_col = '#cbd5e1'
        arrow_col = '#94a3b8'
        badge_col = '#0ea5e9' # Ocean blue
        event_bg = '#1f2937'
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        title_bg = '#e2e8f0'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        sub_col = '#475569'
        arrow_col = '#475569'
        badge_col = '#0284c7'
        event_bg = '#f1f5f9'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    w = 3.2
    h = 2.0

    # Row 1: States 1 -> 2 -> 3 -> 4 (y = 5.2)
    # Row 2: States 8 <- 7 <- 6 <- 5 (y = 1.0)

    # 1. Created
    draw_state_box(ax, 0.6, 5.2, w, h, 1, "Shipment Created",
                   "Order intake & lane assigned\nStage 1 ML Prediction logged",
                   box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # 2. Booking Confirmed
    draw_state_box(ax, 4.3, 5.2, w, h, 2, "Booking Confirmed",
                   "Vessel space & container\nbooking reserved with carrier",
                   box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # 3. Ready for Dispatch
    draw_state_box(ax, 8.0, 5.2, w, h, 3, "Ready for Dispatch",
                   "Cargo packed, staged at dock\n& terminal manifest verified",
                   box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # 4. Dispatched
    draw_state_box(ax, 11.7, 5.2, w, h, 4, "Dispatched (Gate-Out)",
                   "Loaded on vessel / carrier\nStage 2 ML Risk evaluated",
                   box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # Row 1 Horizontal Arrows
    ax.annotate("", xy=(4.3, 6.2), xytext=(3.8, 6.2), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6))
    ax.annotate("", xy=(8.0, 6.2), xytext=(7.5, 6.2), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6))
    ax.annotate("", xy=(11.7, 6.2), xytext=(11.2, 6.2), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6))

    # Turn down from Row 1 to Row 2: State 4 -> State 5
    ax.plot([13.3, 13.3], [5.2, 3.6], color=arrow_col, lw=1.6)
    ax.annotate("", xy=(13.3, 3.0), xytext=(13.3, 3.6), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6))

    # Row 2 (Right to Left):
    # 5. In Transit (x = 11.7)
    draw_state_box(ax, 11.7, 1.0, w, h, 5, "In-Transit Processing",
                   "Deep-sea maritime voyage\nWaypoint checkpoints logged",
                   box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # 6. Arrived at Destination (x = 8.0)
    draw_state_box(ax, 8.0, 1.0, w, h, 6, "Arrived at Destination",
                   "Vessel berthed at port\nCustoms & drayage clearance",
                   box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # 7. Out for Delivery (x = 4.3)
    draw_state_box(ax, 4.3, 1.0, w, h, 7, "Out for Delivery",
                   "Loaded on inland transport\nEn route to final receiver",
                   box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # 8. Completed / Delivered (x = 0.6)
    draw_state_box(ax, 0.6, 1.0, w, h, 8, "Delivery Completed",
                   "Consignee proof of delivery\nFinal SLA & delay audit logged",
                   box_bg, border_col, title_bg, text_col, sub_col, '#10b981')

    # Row 2 Horizontal Arrows (Right to Left)
    ax.annotate("", xy=(11.2, 2.0), xytext=(11.7, 2.0), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6))
    ax.annotate("", xy=(7.5, 2.0), xytext=(8.0, 2.0), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6))
    ax.annotate("", xy=(3.8, 2.0), xytext=(4.3, 2.0), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6))

    # Bottom Banner: Automatic Audit Logging
    audit_banner = patches.FancyBboxPatch((0.6, 0.15), 14.3, 0.55, boxstyle="round,pad=0,rounding_size=0.06",
                                         linewidth=1.1, edgecolor=border_col, facecolor=event_bg)
    ax.add_patch(audit_banner)
    ax.text(7.75, 0.42, "✓ Automatic Audit: Every milestone transition records a timestamped record in the 'shipment_events' table",
            ha='center', va='center', color=sub_col, fontsize=8.2, fontweight='bold', fontfamily='sans-serif')

    ax.set_xlim(0, 15.5)
    ax.set_ylim(0.0, 7.8)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\shipment_lifecycle_flow_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_lifecycle_diagram('light')
render_lifecycle_diagram('dark')
