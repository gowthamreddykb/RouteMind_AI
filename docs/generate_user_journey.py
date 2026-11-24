import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_journey_step(ax, x, y, w, h, step_num, title, desc, bg, border, title_bg, text_col, sub_col, num_col):
    # Outer box
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    # Header tab with Step Number badge
    th = 0.52
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.2, edgecolor=border, facecolor=title_bg)
    ax.add_patch(tbox)
    
    # Step badge circle
    badge = patches.Circle((x + 0.35, y + h - th/2), 0.18, facecolor=num_col, edgecolor=border, lw=1)
    ax.add_patch(badge)
    ax.text(x + 0.35, y + h - th/2, str(step_num), ha='center', va='center',
            color='#ffffff', fontsize=8.5, fontweight='bold', fontfamily='sans-serif')

    # Step Title
    ax.text(x + 0.65, y + h - th/2, title, ha='left', va='center',
            color=text_col, fontsize=9.2, fontweight='bold', fontfamily='sans-serif')
    ax.plot([x, x + w], [y + h - th, y + h - th], color=border, lw=1.0)

    # Description text
    ax.text(x + w/2, y + (h - th)/2, desc, ha='center', va='center',
            color=sub_col, fontsize=7.8, fontfamily='sans-serif', multialignment='center')

def render_user_journey(theme='dark'):
    fig, ax = plt.subplots(figsize=(15, 10.5), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        title_bg = '#1e293b'
        border_col = '#3e4046'
        text_col = '#f8fafc'
        sub_col = '#cbd5e1'
        arrow_col = '#94a3b8'
        badge_col = '#3b82f6'
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        title_bg = '#e2e8f0'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        sub_col = '#475569'
        arrow_col = '#475569'
        badge_col = '#2563eb'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    w = 3.2
    h = 1.9

    # 3-row zig-zag flow for 10 modules:
    # Row 1 (Left to Right, y = 7.8): Modules 1 -> 2 -> 3 -> 4
    # Row 2 (Right to Left, y = 4.4): Modules 7 <- 6 <- 5
    # Row 3 (Left to Right, y = 1.0): Modules 8 -> 9 -> 10

    # Row 1:
    # Mod 1: Login
    draw_journey_step(ax, 0.6, 7.8, w, h, 1, "Login Module",
                      "User enters credentials\n& Email OTP verification",
                      box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # Mod 2: Dashboard
    draw_journey_step(ax, 4.3, 7.8, w, h, 2, "Dashboard Module",
                      "View live Control Tower,\nKPI cards & risk charts",
                      box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # Mod 3: Shipment Management
    draw_journey_step(ax, 8.0, 7.8, w, h, 3, "Shipment Registry",
                      "Search, filter shipments\n& import CSV manifests",
                      box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # Mod 4: Shipment Details
    draw_journey_step(ax, 11.7, 7.8, w, h, 4, "Shipment Details",
                      "Inspect route, milestones,\nvessel & carrier data",
                      box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # Row 1 Horizontal Arrows
    ax.annotate("", xy=(4.3, 8.75), xytext=(3.8, 8.75), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.annotate("", xy=(8.0, 8.75), xytext=(7.5, 8.75), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.annotate("", xy=(11.7, 8.75), xytext=(11.2, 8.75), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # Turn down from Row 1 to Row 2: Mod 4 -> Mod 5
    ax.plot([13.3, 13.3], [7.8, 6.7], color=arrow_col, lw=1.5)
    ax.annotate("", xy=(13.3, 6.3), xytext=(13.3, 6.7), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # Row 2 (Right to Left):
    # Mod 5: Prediction Engine (x = 11.7)
    draw_journey_step(ax, 11.7, 4.4, w, h, 5, "ML Prediction Engine",
                      "Calculates delay probability\n& estimated late days",
                      box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # Mod 6: Exception Management (x = 8.0)
    draw_journey_step(ax, 8.0, 4.4, w, h, 6, "Exception Tickets",
                      "Auto-flags SLA breaches\n& logs operator remarks",
                      box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # Mod 7: Escalation Management (x = 4.3)
    draw_journey_step(ax, 4.3, 4.4, w, h, 7, "Manager Escalations",
                      "Routes critical bottlenecks\nto managers for review",
                      box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # Row 2 Horizontal Arrows (Right to Left)
    ax.annotate("", xy=(11.2, 5.35), xytext=(11.7, 5.35), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.annotate("", xy=(7.5, 5.35), xytext=(8.0, 5.35), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # Turn down from Row 2 to Row 3: Mod 7 -> Mod 8
    ax.plot([4.3, 2.2, 2.2], [5.35, 5.35, 3.3], color=arrow_col, lw=1.5)
    ax.annotate("", xy=(2.2, 2.9), xytext=(2.2, 3.3), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # Row 3 (Left to Right):
    # Mod 8: AI Communications (x = 0.6)
    draw_journey_step(ax, 0.6, 1.0, w, h, 8, "AI Communications",
                      "Auto-drafts carrier notices\n& SLA breach warnings",
                      box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # Mod 9: AI Assistant Copilot (x = 4.3)
    draw_journey_step(ax, 4.3, 1.0, w, h, 9, "AI Assistant Copilot",
                      "Chatbot answers operations\nquestions in natural language",
                      box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # Mod 10: Reports & Admin (x = 8.0)
    draw_journey_step(ax, 8.0, 1.0, w, h, 10, "Reports & Admin",
                      "Analyzes fleet performance,\nuser roles & audit logs",
                      box_bg, border_col, title_bg, text_col, sub_col, badge_col)

    # Row 3 Horizontal Arrows
    ax.annotate("", xy=(4.3, 1.95), xytext=(3.8, 1.95), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.annotate("", xy=(8.0, 1.95), xytext=(7.5, 1.95), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    ax.set_xlim(0, 15.5)
    ax.set_ylim(0.2, 10.5)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\user_journey_modules_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_user_journey('light')
render_user_journey('dark')
