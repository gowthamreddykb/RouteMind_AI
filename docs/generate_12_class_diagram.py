import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_class(ax, x, y, w, h, name, fields, bg='#2b2d31', border='#4b5563', text='#f9fafb', title_bg='#1f2937'):
    # Outer box
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06",
                                 linewidth=1.1, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    # Title
    th = 0.28
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.06",
                                 linewidth=1.1, edgecolor=border, facecolor=title_bg)
    ax.add_patch(tbox)
    ax.text(x + w/2, y + h - th/2, name, ha='center', va='center',
            color=text, fontsize=9.5, fontweight='bold', fontfamily='sans-serif')
    ax.plot([x, x + w], [y + h - th, y + h - th], color=border, lw=0.9)
    
    # Fields
    cy = y + h - th - 0.14
    for f in fields:
        ax.text(x + 0.08, cy, f, ha='left', va='center', color=text, fontsize=7.5, fontfamily='monospace')
        cy -= 0.14

def generate_12_class_diagram(theme='dark'):
    fig, ax = plt.subplots(figsize=(16, 11), dpi=300)
    
    if theme == 'dark':
        bg_main = '#18191c'
        box_bg = '#26272b'
        border_col = '#3f4147'
        text_col = '#f3f4f6'
        title_bg = '#1e293b'
        arrow_col = '#94a3b8'
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        title_bg = '#e2e8f0'
        arrow_col = '#475569'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    w = 2.8
    h = 1.9

    # Grid positions: 4 columns x 3 rows
    # Col 0: x = 0.5
    # Col 1: x = 4.3
    # Col 2: x = 8.1
    # Col 3: x = 11.9
    
    # Row 0 (Top): y = 7.5
    # Row 1 (Mid): y = 4.2
    # Row 2 (Bot): y = 0.9

    # 1. User (Top Left)
    draw_class(ax, 0.5, 7.5, w, h, "User", [
        "+ id: Integer (PK)",
        "+ full_name: String",
        "+ email: String",
        "+ role: String",
        "+ is_active: Boolean",
        "+ check_password()"
    ], box_bg, border_col, text_col, title_bg)

    # 2. Shipment (Top Mid-Left - Central)
    draw_class(ax, 4.3, 7.5, w, 2.3, "Shipment", [
        "+ id: Integer (PK)",
        "+ shipment_number: String",
        "+ order_status: String",
        "+ shipping_mode: String",
        "+ origin_port: String",
        "+ destination_port: String",
        "+ risk_level: String",
        "+ delay_days: Float"
    ], box_bg, border_col, text_col, title_bg)

    # 3. ModelScore (Top Mid-Right)
    draw_class(ax, 8.1, 7.5, w, h, "ModelScore", [
        "+ id: Integer (PK)",
        "+ shipment_id: Integer (FK)",
        "+ stage: String",
        "+ late_probability: Float",
        "+ delay_days_est: Float",
        "+ risk_level: String"
    ], box_bg, border_col, text_col, title_bg)

    # 4. ShipmentEvent (Top Right)
    draw_class(ax, 11.9, 7.5, w, h, "ShipmentEvent", [
        "+ id: Integer (PK)",
        "+ shipment_id: Integer (FK)",
        "+ event_type: String",
        "+ location: String",
        "+ remarks: String",
        "+ timestamp: DateTime"
    ], box_bg, border_col, text_col, title_bg)

    # 5. AuditLog (Mid Left)
    draw_class(ax, 0.5, 4.2, w, h, "AuditLog", [
        "+ id: Integer (PK)",
        "+ user_id: Integer (FK)",
        "+ action: String",
        "+ entity_type: String",
        "+ entity_id: String",
        "+ timestamp: DateTime"
    ], box_bg, border_col, text_col, title_bg)

    # 6. ShipmentException (Mid Mid-Left)
    draw_class(ax, 4.3, 4.2, w, h, "ShipmentException", [
        "+ id: Integer (PK)",
        "+ shipment_id: Integer (FK)",
        "+ exception_type: String",
        "+ severity: String",
        "+ status: String",
        "+ remarks: String"
    ], box_bg, border_col, text_col, title_bg)

    # 7. ManagerEscalation (Mid Mid-Right)
    draw_class(ax, 8.1, 4.2, w, h, "ManagerEscalation", [
        "+ id: Integer (PK)",
        "+ shipment_id: Integer (FK)",
        "+ exception_id: Integer (FK)",
        "+ priority: String",
        "+ status: String",
        "+ assigned_manager: String"
    ], box_bg, border_col, text_col, title_bg)

    # 8. EscalationHistory (Mid Right)
    draw_class(ax, 11.9, 4.2, w, h, "EscalationHistory", [
        "+ id: Integer (PK)",
        "+ escalation_id: Integer (FK)",
        "+ previous_status: String",
        "+ new_status: String",
        "+ notes: String",
        "+ changed_at: DateTime"
    ], box_bg, border_col, text_col, title_bg)

    # 9. EmailOTP (Bot Left)
    draw_class(ax, 0.5, 0.9, w, h, "EmailOTP", [
        "+ id: Integer (PK)",
        "+ user_id: Integer (FK)",
        "+ email: String",
        "+ otp_hash: String",
        "+ expires_at: DateTime",
        "+ is_verified: Boolean"
    ], box_bg, border_col, text_col, title_bg)

    # 10. Communication (Bot Mid-Left)
    draw_class(ax, 4.3, 0.9, w, h, "Communication", [
        "+ id: Integer (PK)",
        "+ shipment_id: Integer (FK)",
        "+ recipient_email: String",
        "+ notice_type: String",
        "+ subject: String",
        "+ status: String"
    ], box_bg, border_col, text_col, title_bg)

    # 11. CommunicationLog (Bot Mid-Right)
    draw_class(ax, 8.1, 0.9, w, h, "CommunicationLog", [
        "+ id: Integer (PK)",
        "+ communication_id: Integer (FK)",
        "+ delivery_status: String",
        "+ smtp_response: String",
        "+ sent_at: DateTime",
        "+ error_message: String"
    ], box_bg, border_col, text_col, title_bg)

    # 12. ChatConversation & ChatMessage (Bot Right)
    draw_class(ax, 11.9, 0.9, w, h, "ChatConversation & Message", [
        "+ id: Integer (PK)",
        "+ user_id: Integer (FK)",
        "+ session_id: String",
        "+ role: String (user/assistant)",
        "+ message_text: Text",
        "+ timestamp: DateTime"
    ], box_bg, border_col, text_col, title_bg)

    # Connectors & Multiplicities
    # User -> Shipment
    ax.annotate("1..*", xy=(4.3, 8.5), xytext=(3.3, 8.5),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.5),
                color=text_col, fontsize=8, fontweight='bold', va='center')
    ax.text(3.8, 8.65, "manages", color=arrow_col, fontsize=7.5, ha='center')

    # Shipment -> ModelScore
    ax.annotate("1..*", xy=(8.1, 8.5), xytext=(7.1, 8.5),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.5),
                color=text_col, fontsize=8, fontweight='bold', va='center')
    ax.text(7.6, 8.65, "scores", color=arrow_col, fontsize=7.5, ha='center')

    # Shipment -> ShipmentEvent
    ax.annotate("1..*", xy=(11.9, 8.5), xytext=(10.9, 8.5),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.5),
                color=text_col, fontsize=8, fontweight='bold', va='center')
    ax.text(11.4, 8.65, "tracks", color=arrow_col, fontsize=7.5, ha='center')

    # User -> AuditLog
    ax.annotate("1..*", xy=(1.9, 6.1), xytext=(1.9, 7.5),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.5),
                color=text_col, fontsize=8, fontweight='bold', ha='center')
    ax.text(2.3, 6.8, "logs", color=arrow_col, fontsize=7.5, va='center')

    # User -> EmailOTP
    ax.annotate("1..*", xy=(1.9, 2.8), xytext=(1.9, 4.2),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.5),
                color=text_col, fontsize=8, fontweight='bold', ha='center')
    ax.text(2.3, 3.5, "requests", color=arrow_col, fontsize=7.5, va='center')

    # Shipment -> ShipmentException
    ax.annotate("1..*", xy=(5.7, 6.1), xytext=(5.7, 7.5),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.5),
                color=text_col, fontsize=8, fontweight='bold', ha='center')
    ax.text(6.1, 6.8, "generates", color=arrow_col, fontsize=7.5, va='center')

    # ShipmentException -> ManagerEscalation
    ax.annotate("1", xy=(8.1, 5.1), xytext=(7.1, 5.1),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.5),
                color=text_col, fontsize=8, fontweight='bold', va='center')
    ax.text(7.6, 5.25, "triggers", color=arrow_col, fontsize=7.5, ha='center')

    # ManagerEscalation -> EscalationHistory
    ax.annotate("1..*", xy=(11.9, 5.1), xytext=(10.9, 5.1),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.5),
                color=text_col, fontsize=8, fontweight='bold', va='center')
    ax.text(11.4, 5.25, "history", color=arrow_col, fontsize=7.5, ha='center')

    # Shipment -> Communication
    ax.annotate("1..*", xy=(5.7, 2.8), xytext=(5.7, 4.2),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.5),
                color=text_col, fontsize=8, fontweight='bold', ha='center')
    ax.text(6.2, 3.5, "dispatches", color=arrow_col, fontsize=7.5, va='center')

    # Communication -> CommunicationLog
    ax.annotate("1..*", xy=(8.1, 1.8), xytext=(7.1, 1.8),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.5),
                color=text_col, fontsize=8, fontweight='bold', va='center')
    ax.text(7.6, 1.95, "logs", color=arrow_col, fontsize=7.5, ha='center')

    # User -> ChatConversation
    # From User to ChatConversation: via bottom
    ax.annotate("1..*", xy=(11.9, 1.8), xytext=(10.9, 1.8),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.5),
                color=text_col, fontsize=8, fontweight='bold', va='center')
    ax.text(11.4, 1.95, "chats", color=arrow_col, fontsize=7.5, ha='center')

    ax.set_xlim(0, 15.2)
    ax.set_ylim(0, 10.5)
    ax.axis('off')

    plt.tight_layout()
    output_path = rf'C:\gowtham_mithraz\RouteMind_AI\docs\class_diagram_12_tables_{theme}.png'
    plt.savefig(output_path, facecolor=bg_main, bbox_inches='tight', pad_inches=0.2)
    plt.close()
    print(f"Generated 12-table diagram: {output_path}")

generate_12_class_diagram('light')
generate_12_class_diagram('dark')
