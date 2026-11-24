import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_class_box(ax, x, y, width, height, title, attributes, bg_color='#2b2d31', border_color='#4f535a', text_color='#ffffff', title_bg='#1e2024'):
    # Outer box
    rect = patches.FancyBboxPatch((x, y), width, height,
                                 boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.2, edgecolor=border_color, facecolor=bg_color)
    ax.add_patch(rect)
    
    # Title bar
    title_height = 0.35
    title_box = patches.FancyBboxPatch((x, y + height - title_height), width, title_height,
                                      boxstyle="round,pad=0,rounding_size=0.08",
                                      linewidth=1.2, edgecolor=border_color, facecolor=title_bg)
    ax.add_patch(title_box)
    
    # Title text
    ax.text(x + width/2, y + height - title_height/2, title,
            ha='center', va='center', color=text_color, fontsize=10.5, fontweight='bold', fontfamily='sans-serif')
    
    # Line separator under title
    ax.plot([x, x + width], [y + height - title_height, y + height - title_height], color=border_color, lw=1)
    
    # Attributes text
    curr_y = y + height - title_height - 0.18
    for attr in attributes:
        ax.text(x + 0.12, curr_y, attr,
                ha='left', va='center', color=text_color, fontsize=8.5, fontfamily='monospace')
        curr_y -= 0.18

def generate_class_diagram(theme='dark'):
    fig, ax = plt.subplots(figsize=(12, 7.5), dpi=300)
    
    if theme == 'dark':
        bg_main = '#18191c'
        box_bg = '#2b2d31'
        border_col = '#4b5563'
        text_col = '#f9fafb'
        title_bg = '#1f2937'
        arrow_col = '#9ca3af'
    else:
        bg_main = '#ffffff'
        box_bg = '#f9fafb'
        border_col = '#9ca3af'
        text_col = '#111827'
        title_bg = '#e5e7eb'
        arrow_col = '#374151'
        
    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    # 1. User Class (Top Left)
    draw_class_box(ax, x=0.5, y=4.5, width=2.6, height=2.4, title="User",
                   attributes=["+ id: Integer", "+ full_name: String", "+ email: String", "+ role: String", "+ is_active: Boolean", "+ check_password()"],
                   bg_color=box_bg, border_color=border_col, text_color=text_col, title_bg=title_bg)

    # 2. Shipment Class (Center)
    draw_class_box(ax, x=4.4, y=3.8, width=3.2, height=3.2, title="Shipment",
                   attributes=["+ id: Integer", "+ shipment_number: String", "+ order_status: String", "+ shipping_mode: String", "+ origin_port: String", "+ destination_port: String", "+ risk_level: String", "+ delay_days: Float"],
                   bg_color=box_bg, border_color=border_col, text_color=text_col, title_bg=title_bg)

    # 3. ModelScore Class (Top Right)
    draw_class_box(ax, x=8.8, y=4.8, width=2.7, height=2.1, title="ModelScore",
                   attributes=["+ id: Integer", "+ shipment_id: Integer", "+ stage: String", "+ late_probability: Float", "+ delay_days_est: Float"],
                   bg_color=box_bg, border_color=border_col, text_color=text_col, title_bg=title_bg)

    # 4. ShipmentException Class (Bottom Center)
    draw_class_box(ax, x=4.4, y=0.5, width=3.2, height=2.4, title="ShipmentException",
                   attributes=["+ id: Integer", "+ shipment_id: Integer", "+ exception_type: String", "+ severity: String", "+ status: String", "+ remarks: String"],
                   bg_color=box_bg, border_color=border_col, text_color=text_col, title_bg=title_bg)

    # 5. ManagerEscalation Class (Bottom Right)
    draw_class_box(ax, x=8.8, y=0.5, width=2.7, height=2.4, title="ManagerEscalation",
                   attributes=["+ id: Integer", "+ shipment_id: Integer", "+ priority: String", "+ status: String", "+ assigned_manager: String", "+ resolution_notes: String"],
                   bg_color=box_bg, border_color=border_col, text_color=text_col, title_bg=title_bg)

    # 6. AuditLog Class (Bottom Left)
    draw_class_box(ax, x=0.5, y=0.8, width=2.6, height=2.1, title="AuditLog",
                   attributes=["+ id: Integer", "+ user_id: Integer", "+ action: String", "+ entity: String", "+ timestamp: DateTime"],
                   bg_color=box_bg, border_color=border_col, text_color=text_col, title_bg=title_bg)

    # Arrows & Relationships
    # User -> Shipment (1 to many)
    ax.annotate("1..*", xy=(4.4, 5.6), xytext=(3.1, 5.6),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.6),
                color=text_col, fontsize=9, fontweight='bold', va='center')
    ax.text(3.6, 5.8, "manages", color=arrow_col, fontsize=8.5, ha='center')

    # Shipment -> ModelScore (1 to many)
    ax.annotate("1..*", xy=(8.8, 5.8), xytext=(7.6, 5.8),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.6),
                color=text_col, fontsize=9, fontweight='bold', va='center')
    ax.text(8.2, 6.0, "scores", color=arrow_col, fontsize=8.5, ha='center')

    # Shipment -> ShipmentException (1 to many)
    ax.annotate("1..*", xy=(6.0, 2.9), xytext=(6.0, 3.8),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.6),
                color=text_col, fontsize=9, fontweight='bold', ha='center')
    ax.text(6.3, 3.3, "generates", color=arrow_col, fontsize=8.5, va='center')

    # ShipmentException -> ManagerEscalation (0..1 to 1)
    ax.annotate("1", xy=(8.8, 1.7), xytext=(7.6, 1.7),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.6),
                color=text_col, fontsize=9, fontweight='bold', va='center')
    ax.text(8.2, 1.9, "triggers", color=arrow_col, fontsize=8.5, ha='center')

    # User -> AuditLog (1 to many)
    ax.annotate("1..*", xy=(1.8, 2.9), xytext=(1.8, 4.5),
                arrowprops=dict(arrowstyle="->", color=arrow_col, lw=1.6),
                color=text_col, fontsize=9, fontweight='bold', ha='center')
    ax.text(2.2, 3.6, "records", color=arrow_col, fontsize=8.5, va='center')

    ax.set_xlim(0, 12.0)
    ax.set_ylim(0, 7.5)
    ax.axis('off')

    plt.tight_layout()
    output_path = rf'C:\gowtham_mithraz\RouteMind_AI\docs\class_diagram_{theme}.png'
    plt.savefig(output_path, facecolor=bg_main, bbox_inches='tight', pad_inches=0.2)
    plt.close()
    print(f"Generated: {output_path}")

generate_class_diagram('dark')
generate_class_diagram('light')
