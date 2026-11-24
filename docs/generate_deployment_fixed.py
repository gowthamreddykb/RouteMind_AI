import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_3d_node_fixed(ax, x, y, w, h, depth, title, items, bg_node, border_node, 
                       card_bg, card_border, text_title_col, text_card_col, sub_col):
    # Front face of the 3D node
    front = patches.Rectangle((x, y), w, h, linewidth=1.3, edgecolor=border_node, facecolor=bg_node)
    ax.add_patch(front)
    
    # Top face
    top = patches.Polygon([[x, y + h], [x + depth, y + h + depth], [x + w + depth, y + h + depth], [x + w, y + h]],
                          closed=True, linewidth=1.3, edgecolor=border_node, facecolor=border_node)
    ax.add_patch(top)
    
    # Right face
    right = patches.Polygon([[x + w, y], [x + w + depth, y + depth], [x + w + depth, y + h + depth], [x + w, y + h]],
                           closed=True, linewidth=1.3, edgecolor=border_node, facecolor=border_node)
    ax.add_patch(right)

    # Node Header
    ax.text(x + w/2, y + h - 0.32, "«device / node»", ha='center', va='center',
            color=sub_col, fontsize=8.5, fontfamily='sans-serif', fontweight='bold')
    ax.text(x + w/2, y + h - 0.65, title, ha='center', va='center',
            color=text_title_col, fontsize=10.5, fontweight='bold', fontfamily='sans-serif')
    ax.plot([x + 0.25, x + w - 0.25], [y + h - 0.95, y + h - 0.95], color=border_node, lw=1.0)

    # Inner boxes (Component cards inside the node)
    cy = y + h - 1.35
    for item in items:
        comp = patches.FancyBboxPatch((x + 0.25, cy - 0.26), w - 0.5, 0.48,
                                      boxstyle="round,pad=0,rounding_size=0.06",
                                      linewidth=1.1, edgecolor=card_border, facecolor=card_bg)
        ax.add_patch(comp)
        # Clear, bold, high-contrast text inside the card
        ax.text(x + w/2, cy - 0.02, item, ha='center', va='center',
                color=text_card_col, fontsize=8.8, fontweight='bold', fontfamily='sans-serif')
        cy -= 0.62

def render_deployment_fixed(theme='dark'):
    fig, ax = plt.subplots(figsize=(13.5, 9.2), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        bg_node = '#222327'
        border_node = '#3e4046'
        text_title_col = '#ffffff'
        sub_col = '#94a3b8'
        # Inner cards: Deep dark slate with bright white bold text for extreme readability
        card_bg = '#1a1b1e'
        card_border = '#4b5563'
        text_card_col = '#ffffff'
        arrow_col = '#cbd5e1'
        label_col = '#e2e8f0'
    else:
        bg_main = '#ffffff'
        bg_node = '#f8fafc'
        border_node = '#cbd5e1'
        text_title_col = '#0f172a'
        sub_col = '#64748b'
        # Inner cards: White with bold dark navy text
        card_bg = '#ffffff'
        card_border = '#94a3b8'
        text_card_col = '#0f172a'
        arrow_col = '#334155'
        label_col = '#1e293b'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    depth = 0.28

    # 1. Node: Client Device (Left)
    draw_3d_node_fixed(ax, 0.6, 2.4, 3.4, 4.2, depth, "Client Device\n(Workstation / Mobile)",
                       ["«artifact» Web Browser", "«artifact» HTML5 / CSS3 UI", "«artifact» Chart.js Dashboard"],
                       bg_node, border_node, card_bg, card_border, text_title_col, text_card_col, sub_col)

    # 2. Node: Application Server (Center)
    draw_3d_node_fixed(ax, 4.9, 1.4, 4.1, 5.8, depth, "Application Server Node\n(Zoho Catalyst / AppSail VM)",
                       ["«execution environment» Python 3.10+", "«server» Flask 3.x WSGI App", "«service» Blueprints & RBAC", "«engine» XGBoost / CatBoost ML", "«service» AI Assistant Controller"],
                       bg_node, border_node, card_bg, card_border, text_title_col, text_card_col, sub_col)

    # 3. Node: Database Server (Top Right)
    draw_3d_node_fixed(ax, 9.9, 4.6, 3.4, 3.8, depth, "Database Server Node\n(MySQL / SQLite Storage)",
                       ["«DBMS» MySQL 8.0 Engine", "«database» 12 Relational Tables", "«storage» Immutable Audit Logs"],
                       bg_node, border_node, card_bg, card_border, text_title_col, text_card_col, sub_col)

    # 4. Node: External Cloud Services (Bottom Right)
    draw_3d_node_fixed(ax, 9.9, 0.5, 3.4, 3.6, depth, "Cloud AI & Mail APIs\n(External Cloud Providers)",
                       ["«cloud API» Groq / Gemini API", "«SMTP server» Gmail Mail Relay", "«protocol» TLS / HTTPS Endpoints"],
                       bg_node, border_node, card_bg, card_border, text_title_col, text_card_col, sub_col)

    # Connections & High-contrast Labels
    # Client <--> App Server
    ax.annotate("", xy=(4.9, 4.5), xytext=(4.0 + depth, 4.5),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.8))
    ax.text(4.45, 4.9, "HTTPS / REST\n(Port 443 / 5000)", ha='center', va='center',
            color=label_col, fontsize=8.5, fontweight='bold')

    # App Server <--> Database Server
    ax.plot([9.0 + depth, 9.45, 9.45, 9.9], [5.5, 5.5, 6.4, 6.4], color=arrow_col, lw=1.6)
    ax.annotate("", xy=(9.9, 6.4), xytext=(9.8, 6.4),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.6))
    ax.text(9.45, 6.75, "SQL / TCP (Port 3306)", ha='center', va='center',
            color=label_col, fontsize=8.5, fontweight='bold')

    # App Server <--> Cloud APIs
    ax.plot([9.0 + depth, 9.45, 9.45, 9.9], [3.2, 3.2, 2.3, 2.3], color=arrow_col, lw=1.6)
    ax.annotate("", xy=(9.9, 2.3), xytext=(9.8, 2.3),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.6))
    ax.text(9.45, 2.65, "Outbound HTTPS / SMTP\n(Ports 443 / 587)", ha='center', va='center',
            color=label_col, fontsize=8.5, fontweight='bold')

    ax.set_xlim(0, 14.0)
    ax.set_ylim(0, 9.2)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\deployment_diagram_fixed_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_deployment_fixed('dark')
render_deployment_fixed('light')
