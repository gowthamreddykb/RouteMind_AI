import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_security_layer(ax, y, h, title, subtitle, items, bg, border, title_bg, text_col, sub_col, tag_text, tag_col):
    x = 0.8
    w = 13.8
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    th = 0.45
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.2, edgecolor=border, facecolor=title_bg)
    ax.add_patch(tbox)
    
    # Layer Title
    ax.text(x + 0.25, y + h - th/2, title, ha='left', va='center',
            color=text_col, fontsize=9.2, fontweight='bold', fontfamily='sans-serif')
    
    # Tag
    badge = patches.FancyBboxPatch((x + w - 1.6, y + h - th + 0.08), 1.4, 0.28,
                                  boxstyle="round,pad=0,rounding_size=0.04",
                                  linewidth=0.8, edgecolor=border, facecolor=tag_col)
    ax.add_patch(badge)
    ax.text(x + w - 0.9, y + h - th/2, tag_text, ha='center', va='center',
            color='#ffffff', fontsize=7.2, fontweight='bold', fontfamily='sans-serif')

    ax.plot([x, x + w], [y + h - th, y + h - th], color=border, lw=1.0)

    # 3-column items inside the layer
    col_w = w / 3
    for i, item in enumerate(items):
        cx = x + i * col_w + 0.2
        cy = y + (h - th) / 2
        ax.text(cx, cy + 0.22, item[0], ha='left', va='center', color=text_col, fontsize=8.2, fontweight='bold', fontfamily='sans-serif')
        ax.text(cx, cy - 0.18, item[1], ha='left', va='center', color=sub_col, fontsize=7.5, fontfamily='sans-serif')

def render_security_diagram(theme='dark'):
    fig, ax = plt.subplots(figsize=(15, 9.5), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        title_bg = '#1e293b'
        border_col = '#3e4046'
        text_col = '#f8fafc'
        sub_col = '#cbd5e1'
        arrow_col = '#94a3b8'
        c_net = '#38bdf8'    # Cyan
        c_auth = '#a855f7'   # Purple
        c_audit = '#10b981'  # Green
        c_db = '#f59e0b'     # Amber
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        title_bg = '#e2e8f0'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        sub_col = '#475569'
        arrow_col = '#475569'
        c_net = '#0284c7'
        c_auth = '#9333ea'
        c_audit = '#059669'
        c_db = '#d97706'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    layer_h = 1.6
    gap = 0.5

    # 1. Layer 1: Network & Session Transport (Top, y = 6.9)
    draw_security_layer(ax, 6.9, layer_h, "Layer 1: Network & Client Session Security", "TRANSPORT",
                        [("HTTPS & TLS Encryption", "Encrypted data in transit across ports 443/587"),
                         ("CSRF Token Verification", "Flask-WTF cryptographically signed form tokens"),
                         ("HttpOnly Session Cookies", "Prevents XSS theft with 12-hour auto-timeout")],
                        box_bg, border_col, title_bg, text_col, sub_col, "LAYER 1", c_net)

    # Arrow 1 -> 2
    ax.annotate("", xy=(7.7, 6.4), xytext=(7.7, 6.9), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # 2. Layer 2: Identity & Access Control (y = 4.8)
    draw_security_layer(ax, 4.8, layer_h, "Layer 2: Authentication & Role-Based Access (RBAC)", "IDENTITY",
                        [("Salted Scrypt Hashing", "Werkzeug password encryption resistant to GPU attacks"),
                         ("Email OTP Verification", "6-digit time-limited one-time password via SMTP"),
                         ("Role Enforcers (@role_required)", "Blocks unauthorized views with HTTP 403 Forbidden")],
                        box_bg, border_col, title_bg, text_col, sub_col, "LAYER 2", c_auth)

    # Arrow 2 -> 3
    ax.annotate("", xy=(7.7, 4.3), xytext=(7.7, 4.8), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # 3. Layer 3: Immutable Audit Trail (y = 2.7)
    draw_security_layer(ax, 2.7, layer_h, "Layer 3: Enterprise Activity & Compliance Audit", "GOVERNANCE",
                        [("User Action Logging", "Captures logins, password changes & user edits"),
                         ("Shipment Lifecycle Audit", "Logs every status advancement in shipment_events"),
                         ("Immutable History Logs", "Permanent escalation notes in escalation_history")],
                        box_bg, border_col, title_bg, text_col, sub_col, "LAYER 3", c_audit)

    # Arrow 3 -> 4
    ax.annotate("", xy=(7.7, 2.2), xytext=(7.7, 2.7), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # 4. Layer 4: Database & SQL Injection Defense (y = 0.6)
    draw_security_layer(ax, 0.6, layer_h, "Layer 4: Database Persistence & Storage Security", "STORAGE",
                        [("SQLAlchemy ORM Parameterization", "Zero raw string concatenation; stops SQL injection"),
                         ("Foreign Key Integrity", "Strict referential constraints prevent orphaned rows"),
                         ("ACID Transactions & Rollbacks", "Automatic database rollback on unexpected errors")],
                        box_bg, border_col, title_bg, text_col, sub_col, "LAYER 4", c_db)

    ax.set_xlim(0, 15.5)
    ax.set_ylim(0.0, 9.0)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\security_audit_layers_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_security_diagram('light')
render_security_diagram('dark')
