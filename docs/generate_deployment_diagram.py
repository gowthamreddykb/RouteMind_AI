import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_3d_node(ax, x, y, w, h, depth, title, items, bg='#24252a', border='#4a4c54', text_col='#ffffff', sub_col='#9ca3af'):
    # Front face
    front = patches.Rectangle((x, y), w, h, linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(front)
    
    # Top face
    top = patches.Polygon([[x, y + h], [x + depth, y + h + depth], [x + w + depth, y + h + depth], [x + w, y + h]],
                          closed=True, linewidth=1.2, edgecolor=border, facecolor=border)
    ax.add_patch(top)
    
    # Right face
    right = patches.Polygon([[x + w, y], [x + w + depth, y + depth], [x + w + depth, y + h + depth], [x + w, y + h]],
                           closed=True, linewidth=1.2, edgecolor=border, facecolor=border)
    ax.add_patch(right)

    # Title (stereotyped node)
    ax.text(x + w/2, y + h - 0.35, f"«device / node»", ha='center', va='center',
            color=sub_col, fontsize=7.5, fontfamily='sans-serif')
    ax.text(x + w/2, y + h - 0.65, title, ha='center', va='center',
            color=text_col, fontsize=9.5, fontweight='bold', fontfamily='sans-serif')
    ax.plot([x + 0.2, x + w - 0.2], [y + h - 0.9, y + h - 0.9], color=border, lw=0.9)

    # Deployed artifacts/components inside the node
    cy = y + h - 1.25
    for item in items:
        # Mini component box inside node
        comp = patches.FancyBboxPatch((x + 0.25, cy - 0.25), w - 0.5, 0.45,
                                      boxstyle="round,pad=0,rounding_size=0.04",
                                      linewidth=0.9, edgecolor=border, facecolor='#1a1b1e' if text_col=='#ffffff' else '#e2e8f0')
        ax.add_patch(comp)
        ax.text(x + w/2, cy - 0.02, item, ha='center', va='center',
                color=text_col, fontsize=7.5, fontfamily='monospace')
        cy -= 0.55

def render_deployment_diagram(theme='dark'):
    fig, ax = plt.subplots(figsize=(13, 8.5), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        border_col = '#3e4046'
        text_col = '#f3f4f6'
        sub_col = '#9ca3af'
        arrow_col = '#8b929e'
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        sub_col = '#475569'
        arrow_col = '#475569'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    depth = 0.25

    # 1. Node: Client Device (Left)
    draw_3d_node(ax, 0.6, 2.5, 3.2, 3.8, depth, "Client Device\n(Workstation / Mobile)",
                 ["«artifact» Web Browser", "«artifact» HTML5 / CSS3 UI", "«artifact» Chart.js Dashboard"],
                 box_bg, border_col, text_col, sub_col)

    # 2. Node: Application Server (Center)
    draw_3d_node(ax, 4.8, 1.8, 3.8, 5.2, depth, "Application Server Node\n(Zoho Catalyst / AppSail VM)",
                 ["«execution environment» Python 3.10+", "«server» Flask 3.x WSGI App", "«service» Blueprints & RBAC", "«engine» XGBoost / CatBoost ML", "«service» AI Assistant Controller"],
                 box_bg, border_col, text_col, sub_col)

    # 3. Node: Database Server (Top Right)
    draw_3d_node(ax, 9.6, 4.6, 3.2, 3.2, depth, "Database Server Node\n(MySQL / SQLite Storage)",
                 ["«DBMS» MySQL 8.0 Engine", "«database» 12 Relational Tables", "«storage» Immutable Audit Logs"],
                 box_bg, border_col, text_col, sub_col)

    # 4. Node: External Cloud Services (Bottom Right)
    draw_3d_node(ax, 9.6, 0.6, 3.2, 3.2, depth, "Cloud AI & Mail APIs\n(External Cloud Providers)",
                 ["«cloud API» Groq / Gemini API", "«SMTP server» Gmail Mail Relay", "«protocol» TLS / HTTPS Endpoints"],
                 box_bg, border_col, text_col, sub_col)

    # Connections & Protocols
    # Client <--> App Server (HTTPS / REST / WSS)
    ax.annotate("", xy=(4.8, 4.5), xytext=(3.8 + depth, 4.5),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.6))
    ax.text(4.4, 4.8, "HTTPS / REST\n(Port 443 / 5000)", ha='center', va='center',
            color=arrow_col, fontsize=7.5, fontweight='bold')

    # App Server <--> Database Server (TCP / IP SQL)
    ax.plot([8.6 + depth, 9.1, 9.1, 9.6], [5.2, 5.2, 6.2, 6.2], color=arrow_col, lw=1.5)
    ax.annotate("", xy=(9.6, 6.2), xytext=(9.5, 6.2),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.5))
    ax.text(9.1, 6.5, "SQL / TCP (Port 3306)", ha='center', va='center',
            color=arrow_col, fontsize=7.5, fontweight='bold')

    # App Server <--> Cloud APIs (Secure Outbound HTTPS)
    ax.plot([8.6 + depth, 9.1, 9.1, 9.6], [3.2, 3.2, 2.2, 2.2], color=arrow_col, lw=1.5)
    ax.annotate("", xy=(9.6, 2.2), xytext=(9.5, 2.2),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.5))
    ax.text(9.1, 2.5, "Outbound HTTPS / SMTP\n(Ports 443 / 587)", ha='center', va='center',
            color=arrow_col, fontsize=7.5, fontweight='bold')

    ax.set_xlim(0, 13.5)
    ax.set_ylim(0, 8.5)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\deployment_diagram_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.2, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_deployment_diagram('light')
render_deployment_diagram('dark')
