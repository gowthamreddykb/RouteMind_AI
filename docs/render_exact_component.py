import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_block(ax, x, y, w, h, title, subtext, bg='#24252a', border='#4a4c54', text_col='#ffffff', sub_col='#9ca3af', fontsize=9):
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    ax.text(x + w/2, y + h*0.62, title, ha='center', va='center',
            color=text_col, fontsize=fontsize, fontweight='bold', fontfamily='sans-serif')
    if subtext:
        ax.text(x + w/2, y + h*0.32, subtext, ha='center', va='center',
                color=sub_col, fontsize=fontsize-1.2, fontfamily='sans-serif')

def render_exact_component_flow(theme='dark'):
    fig, ax = plt.subplots(figsize=(10, 11), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        layer_bg = '#1c1d21'
        border_col = '#3e4046'
        layer_border = '#33353b'
        text_col = '#f3f4f6'
        sub_col = '#cbd5e1'
        arrow_col = '#8b929e'
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        layer_bg = '#f1f5f9'
        border_col = '#cbd5e1'
        layer_border = '#94a3b8'
        text_col = '#0f172a'
        sub_col = '#475569'
        arrow_col = '#475569'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    # 1. Top Layer: Presentation Layer
    p_box = patches.FancyBboxPatch((0.5, 8.4), 9.0, 1.8, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.2, edgecolor=layer_border, facecolor=layer_bg)
    ax.add_patch(p_box)
    ax.text(0.7, 9.9, "Presentation Layer (Client Browser)", color=sub_col, fontsize=9.5, fontweight='bold')

    # Top 3 components
    draw_block(ax, 0.7, 8.6, 2.7, 1.1, "[AI Copilot UI Component]", "Asynchronous Chat Drawer", box_bg, border_col, text_col, sub_col)
    draw_block(ax, 3.65, 8.6, 2.7, 1.1, "[Web UI Component]", "HTML5 / CSS3 / Bootstrap 5", box_bg, border_col, text_col, sub_col)
    draw_block(ax, 6.6, 8.6, 2.7, 1.1, "[Chart Analytics Component]", "Chart.js KPI Visualizations", box_bg, border_col, text_col, sub_col)

    # 2. Middle Layer: Application Server Layer
    s_box = patches.FancyBboxPatch((2.4, 3.8), 5.0, 4.1, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.2, edgecolor=layer_border, facecolor=layer_bg)
    ax.add_patch(s_box)
    ax.text(2.6, 7.6, "Application Server Layer (Flask Backend)", color=sub_col, fontsize=9.5, fontweight='bold')

    draw_block(ax, 3.6, 6.3, 2.8, 1.0, "[Routing & Auth Component]", "Flask Blueprints & RBAC", box_bg, border_col, text_col, sub_col)
    draw_block(ax, 4.2, 4.9, 3.0, 1.0, "[Business Logic Services]", "Shipments & Exceptions Engine", box_bg, border_col, text_col, sub_col)
    draw_block(ax, 2.6, 4.0, 2.6, 1.0, "[Generative AI Connector]", "Groq / Gemini API Adapter", box_bg, border_col, text_col, sub_col)

    # 3. Bottom Layer: Data & Machine Learning Tier
    d_box = patches.FancyBboxPatch((1.8, 0.4), 7.2, 3.0, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.2, edgecolor=layer_border, facecolor=layer_bg)
    ax.add_patch(d_box)
    ax.text(2.0, 3.1, "Data & Machine Learning Tier", color=sub_col, fontsize=9.5, fontweight='bold')

    draw_block(ax, 2.0, 1.7, 3.2, 1.0, "[Data Persistence Component]", "SQLAlchemy ORM & MySQL / SQLite", box_bg, border_col, text_col, sub_col)
    draw_block(ax, 5.5, 1.7, 3.2, 1.0, "[ML Predictive Engine]", "XGBoost & CatBoost Pipelines", box_bg, border_col, text_col, sub_col)
    draw_block(ax, 5.4, 0.55, 3.3, 0.95, "[Model Registry & XAI]", "Joblib Artifacts & SHAP Analysis", box_bg, border_col, text_col, sub_col)

    # Connecting Lines matching user diagram:
    # Copilot UI -> Generative AI Connector
    ax.plot([2.0, 2.0, 3.5], [8.6, 4.9, 4.9], color=arrow_col, lw=1.2)
    ax.annotate("", xy=(3.5, 4.9), xytext=(3.4, 4.9), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.2))

    # Web UI -> Routing & Auth
    ax.plot([5.0, 5.0], [8.6, 7.3], color=arrow_col, lw=1.2)
    ax.annotate("", xy=(5.0, 7.3), xytext=(5.0, 7.4), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.2))

    # Chart Analytics -> Business Logic
    ax.plot([8.0, 8.0, 7.2], [8.6, 5.4, 5.4], color=arrow_col, lw=1.2)
    ax.annotate("", xy=(7.2, 5.4), xytext=(7.3, 5.4), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.2))

    # Routing & Auth -> Business Logic
    ax.plot([5.0, 5.0, 5.7, 5.7], [6.3, 6.0, 6.0, 5.9], color=arrow_col, lw=1.2)
    ax.annotate("", xy=(5.7, 5.9), xytext=(5.7, 6.0), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.2))

    # Business Logic -> Generative AI Connector
    ax.plot([5.7, 5.7, 3.9, 3.9], [4.9, 4.7, 4.7, 5.0], color=arrow_col, lw=1.2)
    ax.annotate("", xy=(3.9, 5.0), xytext=(3.9, 4.9), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.2))

    # Business Logic -> ML Predictive Engine
    ax.plot([7.1, 7.1], [4.9, 2.7], color=arrow_col, lw=1.2)
    ax.annotate("", xy=(7.1, 2.7), xytext=(7.1, 2.8), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.2))

    # Generative AI Connector -> Data Persistence
    ax.plot([3.1, 3.1], [4.0, 2.7], color=arrow_col, lw=1.2)
    ax.annotate("", xy=(3.1, 2.7), xytext=(3.1, 2.8), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.2))

    # ML Predictive Engine -> Model Registry
    ax.plot([7.1, 7.1], [1.7, 1.5], color=arrow_col, lw=1.2)
    ax.annotate("", xy=(7.1, 1.5), xytext=(7.1, 1.6), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.2))

    ax.set_xlim(0, 10.0)
    ax.set_ylim(0, 10.5)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\component_diagram_exact_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()

render_exact_component_flow('dark')
render_exact_component_flow('light')
print("High-res rendered successfully!")
