import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_clean_table(ax, x, y, w, h, name, pks, fks, attrs, 
                     bg='#222327', border='#3e4046', title_bg='#1e293b', 
                     text_col='#ffffff', pk_col='#38bdf8', fk_col='#fbbf24'):
    # Card outer box
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.3, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    # Title bar
    th = 0.45
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.3, edgecolor=border, facecolor=title_bg)
    ax.add_patch(tbox)
    ax.text(x + w/2, y + h - th/2, name, ha='center', va='center',
            color='#ffffff' if text_col=='#ffffff' else '#0f172a', 
            fontsize=10.5, fontweight='bold', fontfamily='sans-serif')
    ax.plot([x, x + w], [y + h - th, y + h - th], color=border, lw=1.1)

    # Content rows
    cy = y + h - th - 0.25
    line_h = 0.24
    
    for pk in pks:
        ax.text(x + 0.15, cy, "PK", ha='left', va='center', color=pk_col, fontsize=8.5, fontweight='bold', fontfamily='sans-serif')
        ax.text(x + 0.65, cy, pk, ha='left', va='center', color=text_col, fontsize=8.5, fontfamily='sans-serif', fontweight='bold')
        cy -= line_h

    for fk in fks:
        ax.text(x + 0.15, cy, "FK", ha='left', va='center', color=fk_col, fontsize=8.5, fontweight='bold', fontfamily='sans-serif')
        ax.text(x + 0.65, cy, fk, ha='left', va='center', color=fk_col, fontsize=8.5, fontfamily='sans-serif', fontweight='bold')
        cy -= line_h

    for attr in attrs:
        ax.text(x + 0.65, cy, attr, ha='left', va='center', color=text_col, fontsize=8.5, fontfamily='sans-serif')
        cy -= line_h

def render_ultra_clean_er(theme='dark'):
    fig, ax = plt.subplots(figsize=(16, 12), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        title_bg = '#1e293b'
        border_col = '#475569'
        text_col = '#f8fafc'
        pk_col = '#38bdf8'  # Bright Cyan
        fk_col = '#fbbf24'  # Bright Amber
        arrow_col = '#94a3b8'
        tag_bg = '#334155'
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        title_bg = '#e2e8f0'
        border_col = '#94a3b8'
        text_col = '#0f172a'
        pk_col = '#0284c7'  # Deep Blue
        fk_col = '#d97706'  # Deep Amber
        arrow_col = '#475569'
        tag_bg = '#e2e8f0'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    w = 2.9
    h = 2.6

    # Clean 4-column layout
    # Col 1: Identity & Security (x = 0.8)
    # Col 2: Core Shipments & Exceptions (x = 4.8)
    # Col 3: ML & Escalations (x = 8.8)
    # Col 4: Telemetry & Logs (x = 12.8)

    # Row 1 (y = 8.6)
    # Row 2 (y = 4.8)
    # Row 3 (y = 1.0)

    # 1. USERS (Col 1, Row 1)
    draw_clean_table(ax, 0.8, 8.6, w, h, "USERS", 
                     ["id"], [], ["full_name", "username", "email", "role", "password_hash"],
                     box_bg, border_col, title_bg, text_col, pk_col, fk_col)

    # 2. SHIPMENTS (Col 2, Row 1) - Central Master
    draw_clean_table(ax, 4.8, 8.4, w+0.2, h+0.4, "SHIPMENTS", 
                     ["id"], [], ["shipment_number", "order_status", "shipping_mode", "origin_port", "destination_port", "risk_level"],
                     box_bg, border_col, title_bg, text_col, pk_col, fk_col)

    # 3. MODEL_SCORES (Col 3, Row 1)
    draw_clean_table(ax, 8.8, 8.6, w, h, "MODEL_SCORES", 
                     ["id"], ["shipment_id"], ["stage", "late_probability", "delay_days_est", "risk_category"],
                     box_bg, border_col, title_bg, text_col, pk_col, fk_col)

    # 4. SHIPMENT_EVENTS (Col 4, Row 1)
    draw_clean_table(ax, 12.6, 8.6, w, h, "SHIPMENT_EVENTS", 
                     ["id"], ["shipment_id"], ["event_type", "location", "remarks", "timestamp"],
                     box_bg, border_col, title_bg, text_col, pk_col, fk_col)

    # 5. AUDIT_LOGS (Col 1, Row 2)
    draw_clean_table(ax, 0.8, 4.8, w, h, "AUDIT_LOGS", 
                     ["id"], ["user_id"], ["action", "entity_type", "entity_id", "timestamp"],
                     box_bg, border_col, title_bg, text_col, pk_col, fk_col)

    # 6. SHIPMENT_EXCEPTIONS (Col 2, Row 2)
    draw_clean_table(ax, 4.8, 4.8, w+0.2, h, "SHIPMENT_EXCEPTIONS", 
                     ["id"], ["shipment_id"], ["exception_type", "severity", "status", "assigned_to"],
                     box_bg, border_col, title_bg, text_col, pk_col, fk_col)

    # 7. MANAGER_ESCALATIONS (Col 3, Row 2)
    draw_clean_table(ax, 8.8, 4.8, w, h, "MANAGER_ESCALATIONS", 
                     ["id"], ["shipment_id", "exception_id"], ["priority", "status", "assigned_manager"],
                     box_bg, border_col, title_bg, text_col, pk_col, fk_col)

    # 8. ESCALATION_HISTORY (Col 4, Row 2)
    draw_clean_table(ax, 12.6, 4.8, w, h, "ESCALATION_HISTORY", 
                     ["id"], ["escalation_id"], ["previous_status", "new_status", "changed_at"],
                     box_bg, border_col, title_bg, text_col, pk_col, fk_col)

    # 9. EMAIL_OTPS (Col 1, Row 3)
    draw_clean_table(ax, 0.8, 1.0, w, h, "EMAIL_OTPS", 
                     ["id"], ["user_id"], ["email", "otp_hash", "expires_at", "is_verified"],
                     box_bg, border_col, title_bg, text_col, pk_col, fk_col)

    # 10. COMMUNICATIONS (Col 2, Row 3)
    draw_clean_table(ax, 4.8, 1.0, w+0.2, h, "COMMUNICATIONS", 
                     ["id"], ["shipment_id"], ["recipient_email", "notice_type", "status"],
                     box_bg, border_col, title_bg, text_col, pk_col, fk_col)

    # 11. COMMUNICATION_LOGS (Col 3, Row 3)
    draw_clean_table(ax, 8.8, 1.0, w, h, "COMMUNICATION_LOGS", 
                     ["id"], ["communication_id"], ["delivery_status", "smtp_response", "sent_at"],
                     box_bg, border_col, title_bg, text_col, pk_col, fk_col)

    # 12. CHAT_MESSAGES (Col 4, Row 3)
    draw_clean_table(ax, 12.6, 1.0, w, h, "CHAT_MESSAGES", 
                     ["id"], ["conversation_id"], ["user_id", "role", "message_text", "timestamp"],
                     box_bg, border_col, title_bg, text_col, pk_col, fk_col)

    # CLEAN STRAIGHT ARROWS (Zero crossing diagonal lines!)
    # USERS -> SHIPMENTS (Row 1)
    ax.annotate("", xy=(4.8, 9.9), xytext=(3.7, 9.9),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6, mutation_scale=13))
    ax.text(4.25, 10.15, "1 : M", ha='center', va='center', color=arrow_col, fontsize=8.5, fontweight='bold')

    # SHIPMENTS -> MODEL_SCORES (Row 1)
    ax.annotate("", xy=(8.8, 9.9), xytext=(7.9, 9.9),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6, mutation_scale=13))
    ax.text(8.35, 10.15, "1 : M", ha='center', va='center', color=arrow_col, fontsize=8.5, fontweight='bold')

    # MODEL_SCORES -> SHIPMENT_EVENTS (Row 1)
    ax.annotate("", xy=(12.6, 9.9), xytext=(11.7, 9.9),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6, mutation_scale=13))
    ax.text(12.15, 10.15, "1 : M", ha='center', va='center', color=arrow_col, fontsize=8.5, fontweight='bold')

    # USERS -> AUDIT_LOGS (Col 1: Vertical)
    ax.annotate("", xy=(2.25, 7.4), xytext=(2.25, 8.6),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6, mutation_scale=13))
    ax.text(2.65, 8.0, "1 : M", ha='center', va='center', color=arrow_col, fontsize=8.5, fontweight='bold')

    # AUDIT_LOGS -> EMAIL_OTPS (Col 1: Vertical)
    ax.annotate("", xy=(2.25, 3.6), xytext=(2.25, 4.8),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6, mutation_scale=13))
    ax.text(2.65, 4.2, "1 : M", ha='center', va='center', color=arrow_col, fontsize=8.5, fontweight='bold')

    # SHIPMENTS -> SHIPMENT_EXCEPTIONS (Col 2: Vertical)
    ax.annotate("", xy=(6.35, 7.4), xytext=(6.35, 8.4),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6, mutation_scale=13))
    ax.text(6.75, 7.9, "1 : M", ha='center', va='center', color=arrow_col, fontsize=8.5, fontweight='bold')

    # SHIPMENT_EXCEPTIONS -> COMMUNICATIONS (Col 2: Vertical)
    ax.annotate("", xy=(6.35, 3.6), xytext=(6.35, 4.8),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6, mutation_scale=13))
    ax.text(6.75, 4.2, "1 : M", ha='center', va='center', color=arrow_col, fontsize=8.5, fontweight='bold')

    # SHIPMENT_EXCEPTIONS -> MANAGER_ESCALATIONS (Row 2: Horizontal)
    ax.annotate("", xy=(8.8, 6.1), xytext=(7.9, 6.1),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6, mutation_scale=13))
    ax.text(8.35, 6.35, "1 : 1", ha='center', va='center', color=arrow_col, fontsize=8.5, fontweight='bold')

    # MANAGER_ESCALATIONS -> ESCALATION_HISTORY (Row 2: Horizontal)
    ax.annotate("", xy=(12.6, 6.1), xytext=(11.7, 6.1),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6, mutation_scale=13))
    ax.text(12.15, 6.35, "1 : M", ha='center', va='center', color=arrow_col, fontsize=8.5, fontweight='bold')

    # COMMUNICATIONS -> COMMUNICATION_LOGS (Row 3: Horizontal)
    ax.annotate("", xy=(8.8, 2.3), xytext=(7.9, 2.3),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6, mutation_scale=13))
    ax.text(8.35, 2.55, "1 : M", ha='center', va='center', color=arrow_col, fontsize=8.5, fontweight='bold')

    # Clean Perimeter Connector for CHAT_MESSAGES (Row 3: Horizontal)
    ax.annotate("", xy=(12.6, 2.3), xytext=(11.7, 2.3),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6, mutation_scale=13))
    ax.text(12.15, 2.55, "1 : M", ha='center', va='center', color=arrow_col, fontsize=8.5, fontweight='bold')

    ax.set_xlim(0, 16.2)
    ax.set_ylim(0.2, 12.0)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\er_diagram_clean_grid_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated clean ER diagram: {out}")

render_ultra_clean_er('dark')
render_ultra_clean_er('light')
