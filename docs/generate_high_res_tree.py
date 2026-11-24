import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_table_card(ax, x, y, w, h, title, fields, bg='#212226', border='#3a3b40', text='#e5e7eb', title_bg='#1b1c20', fontsize=8.5):
    # Outer box
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    # Title bar
    th = 0.38
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.06",
                                  linewidth=1.2, edgecolor=border, facecolor=title_bg)
    ax.add_patch(tbox)
    ax.text(x + w/2, y + h - th/2, title, ha='center', va='center',
            color='#ffffff', fontsize=fontsize+1.5, fontweight='bold', fontfamily='sans-serif')
    ax.plot([x, x + w], [y + h - th, y + h - th], color=border, lw=1)
    
    # Text lines
    cy = y + h - th - 0.22
    for f in fields:
        ax.text(x + 0.12, cy, f, ha='left', va='center', color=text, fontsize=fontsize, fontfamily='monospace')
        cy -= 0.22

def render_high_res_tree(theme='dark'):
    fig, ax = plt.subplots(figsize=(14, 16), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        border_col = '#3e4046'
        text_col = '#f3f4f6'
        title_bg = '#1a1b1e'
        arrow_col = '#8b929e'
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        title_bg = '#e2e8f0'
        arrow_col = '#475569'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    # Box sizes
    w = 2.4
    
    # Coordinates matching the exact user screenshot layout:
    # Top level:
    # User (x=10.0, y=13.2)
    # AuditLog (x=1.2, y=10.8)
    # ChatConversation (x=4.0, y=10.2)
    # Shipment (x=10.0, y=8.8)
    
    # Row below Shipment (y=5.2):
    # ChatMessage (x=3.8, y=5.2) [under ChatConversation]
    # ModelScore (x=6.4, y=5.4)
    # Communication (x=9.0, y=5.2)
    # ShipmentEvent (x=11.6, y=5.2)
    # ShipmentException (x=14.2, y=5.2)
    
    # Below Communication (y=2.4):
    # CommunicationLog (x=9.0, y=2.4)
    
    # Below ShipmentException (y=2.4):
    # ManagerEscalation (x=14.2, y=2.2)
    
    # Below ManagerEscalation (y=-0.6):
    # EscalationHistory (x=14.2, y=-0.5)

    # 1. User
    draw_table_card(ax, 10.0, 13.0, w, 2.4, "User", [
        "+ id: Integer (PK)",
        "+ full_name: String",
        "+ email: String",
        "+ role: String",
        "+ is_active: Boolean",
        "+ check_password()"
    ], box_bg, border_col, text_col, title_bg)

    # 2. AuditLog
    draw_table_card(ax, 1.0, 10.8, w, 2.2, "AuditLog", [
        "+ id: Integer (PK)",
        "+ user_id: Integer (FK)",
        "+ action: String",
        "+ entity_type: String",
        "+ timestamp: DateTime"
    ], box_bg, border_col, text_col, title_bg)

    # 3. ChatConversation
    draw_table_card(ax, 3.8, 10.2, w+0.2, 2.4, "ChatConversation", [
        "+ id: Integer (PK)",
        "+ user_id: Integer (FK)",
        "+ session_id: String",
        "+ created_at: DateTime"
    ], box_bg, border_col, text_col, title_bg)

    # 4. Shipment
    draw_table_card(ax, 9.8, 8.4, w+0.4, 3.4, "Shipment", [
        "+ id: Integer (PK)",
        "+ shipment_number: String",
        "+ order_status: String",
        "+ shipping_mode: String",
        "+ origin_port: String",
        "+ destination_port: String",
        "+ risk_level: String",
        "+ delay_days: Float"
    ], box_bg, border_col, text_col, title_bg)

    # 5. ChatMessage (under ChatConversation)
    draw_table_card(ax, 3.8, 5.2, w+0.2, 2.4, "ChatMessage", [
        "+ id: Integer (PK)",
        "+ conversation_id: Integer (FK)",
        "+ role: String",
        "+ message_text: Text",
        "+ timestamp: DateTime"
    ], box_bg, border_col, text_col, title_bg)

    # 6. ModelScore
    draw_table_card(ax, 6.7, 5.2, w, 2.4, "ModelScore", [
        "+ id: Integer (PK)",
        "+ shipment_id: Integer (FK)",
        "+ stage: String",
        "+ late_probability: Float",
        "+ delay_days_est: Float"
    ], box_bg, border_col, text_col, title_bg)

    # 7. Communication
    draw_table_card(ax, 9.4, 5.2, w, 2.4, "Communication", [
        "+ id: Integer (PK)",
        "+ shipment_id: Integer (FK)",
        "+ recipient_email: String",
        "+ notice_type: String",
        "+ status: String"
    ], box_bg, border_col, text_col, title_bg)

    # 8. ShipmentEvent
    draw_table_card(ax, 12.1, 5.2, w, 2.4, "ShipmentEvent", [
        "+ id: Integer (PK)",
        "+ shipment_id: Integer (FK)",
        "+ event_type: String",
        "+ location: String",
        "+ timestamp: DateTime"
    ], box_bg, border_col, text_col, title_bg)

    # 9. ShipmentException
    draw_table_card(ax, 14.8, 5.2, w, 2.4, "ShipmentException", [
        "+ id: Integer (PK)",
        "+ shipment_id: Integer (FK)",
        "+ exception_type: String",
        "+ severity: String",
        "+ status: String",
        "+ remarks: String"
    ], box_bg, border_col, text_col, title_bg)

    # 10. CommunicationLog
    draw_table_card(ax, 9.4, 1.8, w, 2.2, "CommunicationLog", [
        "+ id: Integer (PK)",
        "+ communication_id: Integer (FK)",
        "+ delivery_status: String",
        "+ sent_at: DateTime"
    ], box_bg, border_col, text_col, title_bg)

    # 11. ManagerEscalation
    draw_table_card(ax, 14.8, 1.6, w, 2.6, "ManagerEscalation", [
        "+ id: Integer (PK)",
        "+ shipment_id: Integer (FK)",
        "+ exception_id: Integer (FK)",
        "+ priority: String",
        "+ status: String",
        "+ assigned_manager: String"
    ], box_bg, border_col, text_col, title_bg)

    # 12. EscalationHistory
    draw_table_card(ax, 14.8, -1.8, w, 2.4, "EscalationHistory", [
        "+ id: Integer (PK)",
        "+ escalation_id: Integer (FK)",
        "+ previous_status: String",
        "+ new_status: String",
        "+ changed_at: DateTime"
    ], box_bg, border_col, text_col, title_bg)

    # Orthogonal Connecting Lines
    # User -> AuditLog
    ax.plot([10.0, 2.2, 2.2], [14.0, 14.0, 13.0], color=arrow_col, lw=1.3)
    ax.annotate("", xy=(2.2, 13.0), xytext=(2.2, 13.1), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.3))
    ax.text(2.0, 13.4, "logs", color=arrow_col, fontsize=8)

    # User -> ChatConversation
    ax.plot([10.0, 5.1, 5.1], [13.7, 13.7, 12.6], color=arrow_col, lw=1.3)
    ax.annotate("", xy=(5.1, 12.6), xytext=(5.1, 12.7), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.3))
    ax.text(4.7, 13.1, "creates", color=arrow_col, fontsize=8)

    # User -> Shipment
    ax.plot([11.2, 11.2], [13.0, 11.8], color=arrow_col, lw=1.3)
    ax.annotate("", xy=(11.2, 11.8), xytext=(11.2, 11.9), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.3))
    ax.text(11.4, 12.4, "manages", color=arrow_col, fontsize=8)

    # ChatConversation -> ChatMessage
    ax.plot([5.1, 5.1], [10.2, 7.6], color=arrow_col, lw=1.3)
    ax.annotate("", xy=(5.1, 7.6), xytext=(5.1, 7.7), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.3))
    ax.text(5.3, 8.9, "contains", color=arrow_col, fontsize=8)

    # Shipment branching bus line
    ship_y = 8.0
    ax.plot([11.2, 11.2], [8.4, ship_y], color=arrow_col, lw=1.3)
    ax.plot([7.9, 16.0], [ship_y, ship_y], color=arrow_col, lw=1.3)

    # -> ModelScore
    ax.plot([7.9, 7.9], [ship_y, 7.6], color=arrow_col, lw=1.3)
    ax.annotate("", xy=(7.9, 7.6), xytext=(7.9, 7.7), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.3))
    ax.text(7.7, 7.75, "scores", color=arrow_col, fontsize=7.5, ha='right')

    # -> Communication
    ax.plot([10.6, 10.6], [ship_y, 7.6], color=arrow_col, lw=1.3)
    ax.annotate("", xy=(10.6, 7.6), xytext=(10.6, 7.7), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.3))
    ax.text(10.4, 7.75, "dispatches", color=arrow_col, fontsize=7.5, ha='right')

    # -> ShipmentEvent
    ax.plot([13.3, 13.3], [ship_y, 7.6], color=arrow_col, lw=1.3)
    ax.annotate("", xy=(13.3, 7.6), xytext=(13.3, 7.7), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.3))
    ax.text(13.1, 7.75, "tracks", color=arrow_col, fontsize=7.5, ha='right')

    # -> ShipmentException
    ax.plot([16.0, 16.0], [ship_y, 7.6], color=arrow_col, lw=1.3)
    ax.annotate("", xy=(16.0, 7.6), xytext=(16.0, 7.7), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.3))
    ax.text(15.8, 7.75, "generates", color=arrow_col, fontsize=7.5, ha='right')

    # Communication -> CommunicationLog
    ax.plot([10.6, 10.6], [5.2, 4.0], color=arrow_col, lw=1.3)
    ax.annotate("", xy=(10.6, 4.0), xytext=(10.6, 4.1), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.3))
    ax.text(10.8, 4.6, "logs", color=arrow_col, fontsize=8)

    # ShipmentException -> ManagerEscalation
    ax.plot([16.0, 16.0], [5.2, 4.2], color=arrow_col, lw=1.3)
    ax.annotate("", xy=(16.0, 4.2), xytext=(16.0, 4.3), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.3))
    ax.text(16.2, 4.7, "triggers", color=arrow_col, fontsize=8)

    # ManagerEscalation -> EscalationHistory
    ax.plot([16.0, 16.0], [1.6, 0.6], color=arrow_col, lw=1.3)
    ax.annotate("", xy=(16.0, 0.6), xytext=(16.0, 0.7), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.3))
    ax.text(16.2, 1.1, "records", color=arrow_col, fontsize=8)

    ax.set_xlim(0, 18.0)
    ax.set_ylim(-2.5, 16.0)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\class_diagram_tree_high_res_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.2, dpi=300)
    plt.close()
    print(f"Generated high quality image: {out}")

render_high_res_tree('dark')
render_high_res_tree('light')
