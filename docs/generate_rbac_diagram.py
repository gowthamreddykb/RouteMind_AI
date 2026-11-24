import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_role_card(ax, x, y, w, h, role_title, perms, bg_col, border_col, title_bg, text_col, badge_col):
    # Main box
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.2, edgecolor=border_col, facecolor=bg_col)
    ax.add_patch(rect)
    
    # Title bar
    th = 0.55
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.2, edgecolor=border_col, facecolor=title_bg)
    ax.add_patch(tbox)
    
    # Title text
    ax.text(x + w/2, y + h - th/2, role_title, ha='center', va='center',
            color='#ffffff' if text_col=='#ffffff' else '#0f172a', fontsize=10, fontweight='bold', fontfamily='sans-serif')
    ax.plot([x, x + w], [y + h - th, y + h - th], color=border_col, lw=1.1)

    # Permission bullet points
    cy = y + h - th - 0.28
    for p in perms:
        ax.plot([x + 0.25], [cy], marker='o', markersize=3.5, color=badge_col)
        ax.text(x + 0.45, cy, p, ha='left', va='center', color=text_col, fontsize=8.2, fontfamily='sans-serif')
        cy -= 0.30

def render_rbac_diagram(theme='dark'):
    fig, ax = plt.subplots(figsize=(13.5, 8.5), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        border_col = '#3e4046'
        text_col = '#f8fafc'
        sub_col = '#94a3b8'
        arrow_col = '#cbd5e1'
        # Role header colors
        disp_bg = '#0f766e' # Teal
        mgr_bg = '#1d4ed8'  # Blue
        admin_bg = '#b91c1c' # Red
        guard_bg = '#334155' # Slate
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        sub_col = '#475569'
        arrow_col = '#334155'
        disp_bg = '#0d9488'
        mgr_bg = '#2563eb'
        admin_bg = '#dc2626'
        guard_bg = '#e2e8f0'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    w = 3.6
    h = 3.0

    # 1. Three User Roles (Top Row, y = 4.8)
    # Role 1: Dispatcher
    draw_role_card(ax, 0.6, 4.8, w, h, "Dispatcher / Operations Analyst",
                   ["View Control Tower & Telemetry", "Advance Lifecycle (Dispatch/Deliver)", "Log Shipment Exception Tickets", "Upload & Validate CSV Manifests", "Ask AI Copilot Operational Queries"],
                   box_bg, border_col, disp_bg, text_col, '#2dd4bf')

    # Role 2: Operations Manager
    draw_role_card(ax, 4.9, 4.8, w, h, "Operations Manager",
                   ["All Dispatcher Permissions Included", "Access Manager Escalation Desk", "Authorize Freight Remediation", "Approve Carrier SLA Breach Notices", "Formally Resolve & Close Tickets"],
                   box_bg, border_col, mgr_bg, text_col, '#60a5fa')

    # Role 3: Administrator
    draw_role_card(ax, 9.2, 4.8, w, h, "System Administrator",
                   ["All Manager Permissions Included", "Manage User Accounts & Roles", "Monitor Master Security Audit Logs", "Configure Risk & ML Thresholds", "Database & Environment Maintenance"],
                   box_bg, border_col, admin_bg, text_col, '#f87171')

    # 2. Middle Layer: RBAC Guard & Security Decorator (y = 2.4)
    guard_box = patches.FancyBboxPatch((2.5, 2.4), 8.5, 1.4, boxstyle="round,pad=0,rounding_size=0.08",
                                       linewidth=1.3, edgecolor=border_col, facecolor=guard_bg)
    ax.add_patch(guard_box)
    ax.text(6.75, 3.25, "Security Layer: Role-Based Access Enforcement (@role_required)", ha='center', va='center',
            color=text_col, fontsize=10, fontweight='bold', fontfamily='sans-serif')
    ax.text(6.75, 2.80, "Verifies User Session + Role Membership Before Route Execution\n(Unauthorized Access Aborts with HTTP 403 Forbidden)", ha='center', va='center',
            color=sub_col, fontsize=8.2, fontfamily='sans-serif')

    # Arrows from Roles to Security Guard
    ax.annotate("", xy=(3.5, 3.8), xytext=(2.4, 4.8), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.annotate("", xy=(6.75, 3.8), xytext=(6.75, 4.8), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.annotate("", xy=(10.0, 3.8), xytext=(11.0, 4.8), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # 3. Bottom Layer: System Workspaces (y = 0.4)
    # Box 1: Operations Workspace
    ws1 = patches.FancyBboxPatch((0.6, 0.4), 3.6, 1.2, boxstyle="round,pad=0,rounding_size=0.06",
                                 linewidth=1.1, edgecolor=border_col, facecolor=box_bg)
    ax.add_patch(ws1)
    ax.text(2.4, 1.2, "Operations Workspace", ha='center', va='center', color=text_col, fontsize=9.2, fontweight='bold')
    ax.text(2.4, 0.75, "Shipments, Exceptions, AI Chat", ha='center', va='center', color=sub_col, fontsize=8.0)

    # Box 2: Manager Workspace
    ws2 = patches.FancyBboxPatch((4.9, 0.4), 3.6, 1.2, boxstyle="round,pad=0,rounding_size=0.06",
                                 linewidth=1.1, edgecolor=border_col, facecolor=box_bg)
    ax.add_patch(ws2)
    ax.text(6.7, 1.2, "Management Desk", ha='center', va='center', color=text_col, fontsize=9.2, fontweight='bold')
    ax.text(6.7, 0.75, "Escalation Review & Approvals", ha='center', va='center', color=sub_col, fontsize=8.0)

    # Box 3: Admin Console
    ws3 = patches.FancyBboxPatch((9.2, 0.4), 3.6, 1.2, boxstyle="round,pad=0,rounding_size=0.06",
                                 linewidth=1.1, edgecolor=border_col, facecolor=box_bg)
    ax.add_patch(ws3)
    ax.text(11.0, 1.2, "Admin Console", ha='center', va='center', color=text_col, fontsize=9.2, fontweight='bold')
    ax.text(11.0, 0.75, "User Roster & Master Audit Logs", ha='center', va='center', color=sub_col, fontsize=8.0)

    # Arrows from Guard to Workspaces
    ax.annotate("", xy=(2.4, 1.6), xytext=(4.0, 2.4), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.annotate("", xy=(6.75, 1.6), xytext=(6.75, 2.4), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.annotate("", xy=(11.0, 1.6), xytext=(9.5, 2.4), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    ax.set_xlim(0, 13.5)
    ax.set_ylim(0, 8.5)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\rbac_roles_architecture_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_rbac_diagram('light')
render_rbac_diagram('dark')
