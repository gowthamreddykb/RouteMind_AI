import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_er_entity(ax, x, y, w, h, name, pk_list, fk_list, attr_list, bg='#24252a', border='#4a4c54', text_col='#ffffff', pk_col='#38bdf8', fk_col='#fbbf24', sub_col='#9ca3af'):
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    # Title bar
    th = 0.36
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.06",
                                  linewidth=1.2, edgecolor=border, facecolor='#1a1b1e' if text_col=='#ffffff' else '#e2e8f0')
    ax.add_patch(tbox)
    ax.text(x + w/2, y + h - th/2, name.upper(), ha='center', va='center',
            color=text_col, fontsize=9.0, fontweight='bold', fontfamily='sans-serif')
    ax.plot([x, x + w], [y + h - th, y + h - th], color=border, lw=1)

    cy = y + h - th - 0.20
    # PKs
    for pk in pk_list:
        ax.text(x + 0.1, cy, f"PK  {pk}", ha='left', va='center', color=pk_col, fontsize=7.5, fontfamily='monospace', fontweight='bold')
        cy -= 0.18
    # FKs
    for fk in fk_list:
        ax.text(x + 0.1, cy, f"FK  {fk}", ha='left', va='center', color=fk_col, fontsize=7.5, fontfamily='monospace', fontweight='bold')
        cy -= 0.18
    # Normal attributes
    for attr in attr_list:
        ax.text(x + 0.1, cy, f"    {attr}", ha='left', va='center', color=text_col, fontsize=7.2, fontfamily='monospace')
        cy -= 0.18

def render_er_diagram(theme='dark'):
    fig, ax = plt.subplots(figsize=(15, 11), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        border_col = '#3e4046'
        text_col = '#f3f4f6'
        pk_col = '#38bdf8' # cyan
        fk_col = '#fbbf24' # amber
        sub_col = '#94a3b8'
        arrow_col = '#8b929e'
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        pk_col = '#0284c7'
        fk_col = '#d97706'
        sub_col = '#475569'
        arrow_col = '#475569'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    w = 2.6
    h = 2.0

    # Grid arrangement: 4 columns x 3 rows
    # Col 0: x=0.5
    # Col 1: x=4.3
    # Col 2: x=8.1
    # Col 3: x=11.9
    
    # Row 0: y=7.8
    # Row 1: y=4.4
    # Row 2: y=1.0

    # 1. USERS
    draw_er_entity(ax, 0.5, 7.8, w, h, "users", ["id"], [], ["full_name", "username", "email", "role", "password_hash"], box_bg, border_col, text_col, pk_col, fk_col, sub_col)
    
    # 2. SHIPMENTS (Central)
    draw_er_entity(ax, 4.3, 7.8, w+0.2, 2.4, "shipments", ["id"], [], ["shipment_number", "order_status", "shipping_mode", "origin_port", "destination_port", "risk_level"], box_bg, border_col, text_col, pk_col, fk_col, sub_col)

    # 3. MODEL_SCORES
    draw_er_entity(ax, 8.1, 7.8, w, h, "model_scores", ["id"], ["shipment_id"], ["stage", "late_probability", "delay_days_est", "risk_category"], box_bg, border_col, text_col, pk_col, fk_col, sub_col)

    # 4. SHIPMENT_EVENTS
    draw_er_entity(ax, 11.9, 7.8, w, h, "shipment_events", ["id"], ["shipment_id"], ["event_type", "location", "remarks", "timestamp"], box_bg, border_col, text_col, pk_col, fk_col, sub_col)

    # 5. AUDIT_LOGS
    draw_er_entity(ax, 0.5, 4.4, w, h, "audit_logs", ["id"], ["user_id"], ["action", "entity_type", "entity_id", "timestamp"], box_bg, border_col, text_col, pk_col, fk_col, sub_col)

    # 6. SHIPMENT_EXCEPTIONS
    draw_er_entity(ax, 4.3, 4.4, w+0.2, h, "shipment_exceptions", ["id"], ["shipment_id"], ["exception_type", "severity", "status", "assigned_to"], box_bg, border_col, text_col, pk_col, fk_col, sub_col)

    # 7. MANAGER_ESCALATIONS
    draw_er_entity(ax, 8.1, 4.4, w, 2.2, "manager_escalations", ["id"], ["shipment_id", "exception_id"], ["priority", "status", "assigned_mgr", "notes"], box_bg, border_col, text_col, pk_col, fk_col, sub_col)

    # 8. ESCALATION_HISTORY
    draw_er_entity(ax, 11.9, 4.4, w, h, "escalation_history", ["id"], ["escalation_id"], ["previous_status", "new_status", "notes", "changed_at"], box_bg, border_col, text_col, pk_col, fk_col, sub_col)

    # 9. EMAIL_OTPS
    draw_er_entity(ax, 0.5, 1.0, w, h, "email_otps", ["id"], ["user_id"], ["email", "otp_hash", "expires_at", "is_verified"], box_bg, border_col, text_col, pk_col, fk_col, sub_col)

    # 10. COMMUNICATIONS
    draw_er_entity(ax, 4.3, 1.0, w+0.2, h, "communications", ["id"], ["shipment_id"], ["recipient_email", "notice_type", "status", "created_at"], box_bg, border_col, text_col, pk_col, fk_col, sub_col)

    # 11. COMMUNICATION_LOGS
    draw_er_entity(ax, 8.1, 1.0, w, h, "communication_logs", ["id"], ["communication_id"], ["delivery_status", "smtp_response", "sent_at"], box_bg, border_col, text_col, pk_col, fk_col, sub_col)

    # 12. CHAT_MESSAGES
    draw_er_entity(ax, 11.9, 1.0, w, h, "chat_messages", ["id"], ["conversation_id"], ["user_id", "role", "message_text", "timestamp"], box_bg, border_col, text_col, pk_col, fk_col, sub_col)

    # ER Relationship lines (Crow's foot / arrows)
    # users -> shipments
    ax.annotate("1:M", xy=(4.3, 8.8), xytext=(3.1, 8.8),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4), color=sub_col, fontsize=7.5, fontweight='bold')
    # shipments -> model_scores
    ax.annotate("1:M", xy=(8.1, 8.8), xytext=(7.1, 8.8),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4), color=sub_col, fontsize=7.5, fontweight='bold')
    # shipments -> shipment_events
    ax.annotate("1:M", xy=(11.9, 8.8), xytext=(10.7, 8.8),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4), color=sub_col, fontsize=7.5, fontweight='bold')

    # users -> audit_logs
    ax.annotate("1:M", xy=(1.8, 6.4), xytext=(1.8, 7.8),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4), color=sub_col, fontsize=7.5, fontweight='bold')
    # users -> email_otps
    ax.annotate("1:M", xy=(1.8, 3.0), xytext=(1.8, 4.4),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4), color=sub_col, fontsize=7.5, fontweight='bold')

    # shipments -> shipment_exceptions
    ax.annotate("1:M", xy=(5.6, 6.4), xytext=(5.6, 7.8),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4), color=sub_col, fontsize=7.5, fontweight='bold')
    # shipment_exceptions -> manager_escalations
    ax.annotate("1:1", xy=(8.1, 5.4), xytext=(7.1, 5.4),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4), color=sub_col, fontsize=7.5, fontweight='bold')
    # manager_escalations -> escalation_history
    ax.annotate("1:M", xy=(11.9, 5.4), xytext=(10.7, 5.4),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4), color=sub_col, fontsize=7.5, fontweight='bold')

    # shipments -> communications
    ax.annotate("1:M", xy=(5.6, 3.0), xytext=(5.6, 4.4),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4), color=sub_col, fontsize=7.5, fontweight='bold')
    # communications -> communication_logs
    ax.annotate("1:M", xy=(8.1, 2.0), xytext=(7.1, 2.0),
                arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4), color=sub_col, fontsize=7.5, fontweight='bold')
    # users -> chat_messages
    ax.plot([3.1, 3.6, 3.6, 11.9], [8.2, 8.2, 0.4, 1.8], color=arrow_col, lw=1.2)
    ax.annotate("", xy=(11.9, 1.8), xytext=(11.8, 1.7), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.2))

    ax.set_xlim(0, 15.0)
    ax.set_ylim(0, 10.6)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\er_diagram_schema_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_er_diagram('light')
render_er_diagram('dark')
