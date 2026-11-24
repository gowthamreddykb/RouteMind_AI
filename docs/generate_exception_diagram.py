import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_triage_node(ax, x, y, w, h, title, subtext, bg, border, title_bg, text_col, sub_col, badge_text, badge_col):
    # Rounded outer box
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    # Header bar
    th = 0.50
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.2, edgecolor=border, facecolor=title_bg)
    ax.add_patch(tbox)
    
    # Badge
    badge = patches.FancyBboxPatch((x + 0.15, y + h - th + 0.08), 0.75, 0.32,
                                  boxstyle="round,pad=0,rounding_size=0.04",
                                  linewidth=0.8, edgecolor=border, facecolor=badge_col)
    ax.add_patch(badge)
    ax.text(x + 0.52, y + h - th/2, badge_text, ha='center', va='center',
            color='#ffffff', fontsize=7.5, fontweight='bold', fontfamily='sans-serif')

    # Title
    ax.text(x + 1.05, y + h - th/2, title, ha='left', va='center',
            color=text_col, fontsize=8.8, fontweight='bold', fontfamily='sans-serif')
    ax.plot([x, x + w], [y + h - th, y + h - th], color=border, lw=1.0)

    # Subtext
    ax.text(x + w/2, y + (h - th)/2, subtext, ha='center', va='center',
            color=sub_col, fontsize=7.8, fontfamily='sans-serif', multialignment='center')

def render_exception_diagram(theme='dark'):
    fig, ax = plt.subplots(figsize=(15, 9.5), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        title_bg = '#1e293b'
        border_col = '#3e4046'
        text_col = '#f8fafc'
        sub_col = '#cbd5e1'
        arrow_col = '#94a3b8'
        decision_bg = '#1e293b'
        disp_col = '#0d9488' # Teal
        mgr_col = '#2563eb'  # Blue
        close_col = '#10b981' # Emerald
        err_col = '#ef4444'  # Red
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        title_bg = '#e2e8f0'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        sub_col = '#475569'
        arrow_col = '#475569'
        decision_bg = '#e2e8f0'
        disp_col = '#0f766e'
        mgr_col = '#1d4ed8'
        close_col = '#059669'
        err_col = '#dc2626'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    w = 3.3
    h = 2.0

    # Section 1: Dispatcher Exception Triage (Top Row, y = 6.4)
    # Section 2: Manager Escalation Flow (Middle Row, y = 3.4)
    # Section 3: Resolution & Audit (Bottom Row, y = 0.5)

    # Step 1: Exception Created
    draw_triage_node(ax, 0.6, 6.4, w, h, "Exception Created",
                     "Triggered by ML High Risk (≥60%)\nor physical delay reported",
                     box_bg, border_col, title_bg, text_col, sub_col, "TICKET", disp_col)

    # Step 2: Investigation & Status
    draw_triage_node(ax, 4.4, 6.4, w, h, "Triage & Investigation",
                     "Status: UNDER INVESTIGATION\nSeverity: Low / Medium / High",
                     box_bg, border_col, title_bg, text_col, sub_col, "ASSIGN", disp_col)

    # Arrow 1 -> 2
    ax.annotate("", xy=(4.4, 7.4), xytext=(3.9, 7.4), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # Decision Diamond: Critical SLA Threat? (x = 9.2, y = 7.4)
    size = 1.3
    d = size / 2
    diamond = patches.Polygon([[9.2, 7.4 + d], [9.2 + d*1.3, 7.4], [9.2, 7.4 - d], [9.2 - d*1.3, 7.4]],
                              closed=True, linewidth=1.2, edgecolor=border_col, facecolor=decision_bg)
    ax.add_patch(diamond)
    ax.text(9.2, 7.4, "Severe SLA\nBreach?", ha='center', va='center', color=text_col, fontsize=8.0, fontweight='bold', multialignment='center')

    # Arrow 2 -> Decision
    ax.annotate("", xy=(8.35, 7.4), xytext=(7.7, 7.4), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # Branch 1 [No - Minor Issue] -> Step 3: Dispatcher Direct Fix (Top Right, x = 11.4)
    draw_triage_node(ax, 11.4, 6.4, w, h, "Direct Resolution",
                     "Dispatcher contacts carrier,\nupdates port hold remarks",
                     box_bg, border_col, title_bg, text_col, sub_col, "SOLVE", disp_col)
    ax.annotate("", xy=(11.4, 7.4), xytext=(10.05, 7.4), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.text(10.6, 7.65, "[No: Minor]", ha='center', va='center', color=sub_col, fontsize=7.8, fontweight='bold')

    # Branch 2 [Yes - Critical Issue] -> Down into Manager Escalation (Middle Row)
    # Step 4: Manager Escalation Raised (x = 4.4, y = 3.4)
    draw_triage_node(ax, 4.4, 3.4, w, h, "Manager Escalation",
                     "Escalated to Operations Manager\nPriority: High / Urgent / Critical",
                     box_bg, border_col, title_bg, text_col, sub_col, "ESCALATE", mgr_col)

    # Arrow from Decision down to Manager Escalation
    ax.plot([9.2, 9.2, 7.7], [6.75, 4.4, 4.4], color=err_col, lw=1.4)
    ax.annotate("", xy=(7.7, 4.4), xytext=(7.8, 4.4), arrowprops=dict(arrowstyle="-|>", color=err_col, lw=1.4))
    ax.text(9.2, 5.5, "[Yes: Major SLA Risk]", ha='left', va='center', color=err_col, fontsize=7.8, fontweight='bold')

    # Step 5: Manager Action & Strategy (Middle Right, x = 11.4, y = 3.4)
    draw_triage_node(ax, 11.4, 3.4, w, h, "Managerial Remediation",
                     "Authorizes priority rerouting,\nsecondary carrier or SLA notice",
                     box_bg, border_col, title_bg, text_col, sub_col, "ACTION", mgr_col)
    ax.annotate("", xy=(11.4, 4.4), xytext=(7.7, 4.4), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # Step 6: Final Resolution & Audit Closure (Bottom Center, x = 5.8, y = 0.5)
    draw_triage_node(ax, 5.8, 0.5, 4.4, h, "Resolution & Audit Closure",
                     "Status updated to RESOLVED & CLOSED\nAudit trail saved in escalation_history",
                     box_bg, border_col, title_bg, text_col, sub_col, "CLOSED", close_col)

    # Connections to Final Resolution
    # From Direct Resolution (Top Right) -> Down to Resolution
    ax.plot([13.0, 13.0, 10.2], [6.4, 1.5, 1.5], color=arrow_col, lw=1.4)
    ax.annotate("", xy=(10.2, 1.5), xytext=(10.3, 1.5), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4))

    # From Manager Action -> Down to Resolution
    ax.plot([13.0, 13.0, 10.2], [3.4, 1.5, 1.5], color=arrow_col, lw=1.4)

    # End Bullseye Circle (Bottom Left, x = 2.0, y = 1.5)
    ax.annotate("", xy=(2.7, 1.5), xytext=(5.8, 1.5), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    end_outer = patches.Circle((2.2, 1.5), 0.28, facecolor='none', edgecolor=close_col, lw=1.6)
    end_inner = patches.Circle((2.2, 1.5), 0.18, facecolor=close_col, edgecolor='none')
    ax.add_patch(end_outer)
    ax.add_patch(end_inner)
    ax.text(2.2, 0.95, "Ticket Closed", ha='center', va='center', color=text_col, fontsize=8.8, fontweight='bold')

    ax.set_xlim(0, 15.2)
    ax.set_ylim(0.2, 9.0)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\exception_escalation_flow_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_exception_diagram('light')
render_exception_diagram('dark')
