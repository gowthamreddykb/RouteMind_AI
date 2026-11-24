import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_activity_node(ax, x, y, w, h, text, bg='#2b2d31', border='#4b5563', text_col='#ffffff', radius=0.15, fontsize=9.5):
    rect = patches.FancyBboxPatch((x - w/2, y - h/2), w, h,
                                 boxstyle=f"round,pad=0,rounding_size={radius}",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    ax.text(x, y, text, ha='center', va='center', color=text_col,
            fontsize=fontsize, fontweight='bold', fontfamily='sans-serif', multialignment='center')

def draw_decision_diamond(ax, x, y, size, text, bg='#374151', border='#9ca3af', text_col='#ffffff', fontsize=8.5):
    # Diamond polygon
    d = size / 2
    diamond = patches.Polygon([[x, y + d], [x + d*1.3, y], [x, y - d], [x - d*1.3, y]],
                              closed=True, linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(diamond)
    ax.text(x, y, text, ha='center', va='center', color=text_col,
            fontsize=fontsize, fontweight='bold', fontfamily='sans-serif', multialignment='center')

def render_activity_diagram(theme='dark'):
    fig, ax = plt.subplots(figsize=(10, 13), dpi=300)
    
    if theme == 'dark':
        bg_main = '#18191c'
        node_bg = '#26272b'
        border_col = '#4f535a'
        text_col = '#f3f4f6'
        decision_bg = '#1e293b'
        arrow_col = '#9ca3af'
        start_col = '#10b981' # emerald
        end_col = '#ef4444'   # red
    else:
        bg_main = '#ffffff'
        node_bg = '#f8fafc'
        border_col = '#94a3b8'
        text_col = '#0f172a'
        decision_bg = '#e2e8f0'
        arrow_col = '#475569'
        start_col = '#059669'
        end_col = '#dc2626'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    # 1. Start Node (Circle)
    start_circle = patches.Circle((5.0, 12.0), 0.22, facecolor=start_col, edgecolor=border_col, lw=1.2)
    ax.add_patch(start_circle)
    ax.text(5.0, 12.4, "Start", ha='center', va='center', color=text_col, fontsize=10, fontweight='bold')

    # Arrow from Start -> Node 1
    ax.annotate("", xy=(5.0, 10.9), xytext=(5.0, 11.75),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6, mutation_scale=12))

    # 2. Activity: ML Model Identifies High Delay Risk
    draw_activity_node(ax, 5.0, 10.3, 4.4, 0.9, "ML Predicts High Delay Risk\n(Late Probability ≥ 60%)",
                       bg=node_bg, border=border_col, text_col=text_col)

    # Arrow -> Node 2
    ax.annotate("", xy=(5.0, 9.1), xytext=(5.0, 9.85),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6, mutation_scale=12))

    # 3. Activity: Create Shipment Exception Ticket
    draw_activity_node(ax, 5.0, 8.5, 4.2, 0.9, "Create Exception Ticket\n(Assign Type, Priority & Remarks)",
                       bg=node_bg, border=border_col, text_col=text_col)

    # Arrow -> Decision 1
    ax.annotate("", xy=(5.0, 7.3), xytext=(5.0, 8.05),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6, mutation_scale=12))

    # 4. Decision Diamond: Is Manager Review Required?
    draw_decision_diamond(ax, 5.0, 6.6, 1.2, "Critical SLA\nImpact?",
                          bg=decision_bg, border=border_col, text_col=text_col)

    # Decision Branch 1: [No - Minor Issue] -> Goes Left to Dispatcher Actions
    ax.plot([4.2, 2.2, 2.2], [6.6, 6.6, 5.4], color=arrow_col, lw=1.4)
    ax.annotate("", xy=(2.2, 5.4), xytext=(2.2, 5.5),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4, mutation_scale=12))
    ax.text(3.1, 6.8, "[No: Low/Med]", color=arrow_col, fontsize=8.5, fontweight='bold', ha='center')

    draw_activity_node(ax, 2.2, 4.8, 3.2, 0.9, "Dispatcher Resolves Issue\n(Contact Carrier / Port Hold)",
                       bg=node_bg, border=border_col, text_col=text_col)

    # Decision Branch 2: [Yes - Severe Issue] -> Goes Right to Manager Escalation
    ax.plot([5.8, 7.8, 7.8], [6.6, 6.6, 5.4], color=arrow_col, lw=1.4)
    ax.annotate("", xy=(7.8, 5.4), xytext=(7.8, 5.5),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4, mutation_scale=12))
    ax.text(6.9, 6.8, "[Yes: High SLA Risk]", color=arrow_col, fontsize=8.5, fontweight='bold', ha='center')

    draw_activity_node(ax, 7.8, 4.8, 3.4, 0.9, "Escalate to Operations Manager\n(Create Escalation Ticket)",
                       bg=node_bg, border=border_col, text_col=text_col)

    # From Manager Escalation -> Manager Triage Actions
    ax.annotate("", xy=(7.8, 3.6), xytext=(7.8, 4.35),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4, mutation_scale=12))

    draw_activity_node(ax, 7.8, 3.0, 3.4, 0.9, "Manager Action & Resolution\n(Expedite Freight / Reroute)",
                       bg=node_bg, border=border_col, text_col=text_col)

    # Merge point back to common resolution
    # Left branch down to merge y=1.8
    ax.plot([2.2, 2.2, 4.0], [4.35, 1.8, 1.8], color=arrow_col, lw=1.4)
    # Right branch down to merge y=1.8
    ax.plot([7.8, 7.8, 6.0], [2.55, 1.8, 1.8], color=arrow_col, lw=1.4)
    ax.annotate("", xy=(5.0, 1.2), xytext=(5.0, 1.8),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4, mutation_scale=12))

    # 5. Activity: Log Resolution Feedback & Close Ticket
    draw_activity_node(ax, 5.0, 0.6, 4.4, 0.9, "Log Audit Feedback & Remarks\n(Mark Exception RESOLVED & CLOSED)",
                       bg=node_bg, border=border_col, text_col=text_col)

    # Arrow to End Node
    ax.annotate("", xy=(5.0, -0.6), xytext=(5.0, 0.15),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4, mutation_scale=12))

    # End Node (Bullseye / Double Circle)
    outer_end = patches.Circle((5.0, -0.9), 0.28, facecolor='none', edgecolor=end_col, lw=1.6)
    inner_end = patches.Circle((5.0, -0.9), 0.18, facecolor=end_col, edgecolor='none')
    ax.add_patch(outer_end)
    ax.add_patch(inner_end)
    ax.text(5.0, -1.4, "End", ha='center', va='center', color=text_col, fontsize=10, fontweight='bold')

    ax.set_xlim(0, 10.0)
    ax.set_ylim(-1.8, 13.0)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\activity_diagram_escalation_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.2, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_activity_diagram('light')
render_activity_diagram('dark')
