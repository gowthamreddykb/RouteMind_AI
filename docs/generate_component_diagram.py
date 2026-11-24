import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_component(ax, x, y, w, h, title, subtext="", bg='#24252a', border='#4a4c54', text_col='#ffffff', icon_col='#3b82f6'):
    # Main component box
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    # UML Component decoration on top right (two small protruding tabs)
    tab_w = 0.35
    tab_h = 0.12
    t1 = patches.Rectangle((x + w - 0.45, y + h - 0.22), tab_w, tab_h, facecolor=icon_col, edgecolor=border, lw=0.8)
    t2 = patches.Rectangle((x + w - 0.45, y + h - 0.38), tab_w, tab_h, facecolor=icon_col, edgecolor=border, lw=0.8)
    ax.add_patch(t1)
    ax.add_patch(t2)
    
    # Title
    ax.text(x + 0.15, y + h - 0.28, title, ha='left', va='center',
            color=text_col, fontsize=9.5, fontweight='bold', fontfamily='sans-serif')
    
    # Subtext / technologies
    if subtext:
        ax.text(x + 0.15, y + 0.25, subtext, ha='left', va='center',
                color='#9ca3af' if text_col=='#ffffff' else '#4b5563', fontsize=7.5, fontfamily='monospace')

def render_component_diagram(theme='dark'):
    fig, ax = plt.subplots(figsize=(13, 9), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        subgraph_bg = '#1c1d21'
        border_col = '#3e4046'
        subgraph_border = '#33353b'
        text_col = '#f3f4f6'
        sub_text_col = '#9ca3af'
        arrow_col = '#8b929e'
        comp_tab = '#38bdf8' # sky blue
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        subgraph_bg = '#f1f5f9'
        border_col = '#cbd5e1'
        subgraph_border = '#94a3b8'
        text_col = '#0f172a'
        sub_text_col = '#475569'
        arrow_col = '#475569'
        comp_tab = '#0284c7'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    # Subgraph Packages (3 main clusters)
    # 1. UI Layer (Top)
    ui_box = patches.FancyBboxPatch((0.5, 6.2), 12.0, 2.3, boxstyle="round,pad=0,rounding_size=0.12",
                                   linewidth=1.2, edgecolor=subgraph_border, facecolor=subgraph_bg, linestyle='--')
    ax.add_patch(ui_box)
    ax.text(0.8, 8.2, "Presentation Layer (Client Browser)", color=sub_text_col, fontsize=9.5, fontweight='bold')

    # UI Components
    draw_component(ax, 0.8, 6.5, 3.5, 1.4, "Web UI Component", "HTML5, CSS3, Bootstrap 5\nJinja2 Templates, Responsive UI",
                   bg=box_bg, border=border_col, text_col=text_col, icon_col=comp_tab)
    draw_component(ax, 4.7, 6.5, 3.6, 1.4, "Chart Analytics Component", "Chart.js Visualizations\nRisk & KPI Telemetry Charts",
                   bg=box_bg, border=border_col, text_col=text_col, icon_col=comp_tab)
    draw_component(ax, 8.7, 6.5, 3.5, 1.4, "AI Copilot UI Component", "JavaScript Asynchronous Chat\nDrawer & Context Prompts",
                   bg=box_bg, border=border_col, text_col=text_col, icon_col=comp_tab)

    # 2. Application Logic Layer (Middle)
    app_box = patches.FancyBboxPatch((0.5, 3.2), 12.0, 2.4, boxstyle="round,pad=0,rounding_size=0.12",
                                    linewidth=1.2, edgecolor=subgraph_border, facecolor=subgraph_bg, linestyle='--')
    ax.add_patch(app_box)
    ax.text(0.8, 5.3, "Application Server Layer (Flask Backend)", color=sub_text_col, fontsize=9.5, fontweight='bold')

    # Middle Components
    draw_component(ax, 0.8, 3.5, 3.5, 1.4, "Routing & Auth Component", "Flask Blueprints, Flask-Login\nCSRF Token Verification, RBAC",
                   bg=box_bg, border=border_col, text_col=text_col, icon_col=comp_tab)
    draw_component(ax, 4.7, 3.5, 3.6, 1.4, "Business Logic Services", "Shipment, Exception &\nEscalation Management Engines",
                   bg=box_bg, border=border_col, text_col=text_col, icon_col=comp_tab)
    draw_component(ax, 8.7, 3.5, 3.5, 1.4, "Generative AI Connector", "Groq / Gemini API Adapter\nDatabase Context Grounding",
                   bg=box_bg, border=border_col, text_col=text_col, icon_col=comp_tab)

    # 3. Persistence & ML Engines (Bottom)
    data_box = patches.FancyBboxPatch((0.5, 0.3), 12.0, 2.3, boxstyle="round,pad=0,rounding_size=0.12",
                                     linewidth=1.2, edgecolor=subgraph_border, facecolor=subgraph_bg, linestyle='--')
    ax.add_patch(data_box)
    ax.text(0.8, 2.3, "Data & Machine Learning Tier", color=sub_text_col, fontsize=9.5, fontweight='bold')

    draw_component(ax, 0.8, 0.6, 3.5, 1.4, "Data Persistence Component", "SQLAlchemy ORM Layer\nMySQL / SQLite (12 Tables)",
                   bg=box_bg, border=border_col, text_col=text_col, icon_col=comp_tab)
    draw_component(ax, 4.7, 0.6, 3.6, 1.4, "ML Predictive Engine", "XGBoost, CatBoost, LogReg\nStage 1 & Stage 2 Inference",
                   bg=box_bg, border=border_col, text_col=text_col, icon_col=comp_tab)
    draw_component(ax, 8.7, 0.6, 3.5, 1.4, "Model Registry & Explainability", "Serialized .joblib Pipelines\nSHAP Risk Factor Analysis",
                   bg=box_bg, border=border_col, text_col=text_col, icon_col=comp_tab)

    # Inter-component Connectors
    # UI -> Routing
    ax.annotate("", xy=(2.55, 4.9), xytext=(2.55, 6.5),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.4))
    # Chart -> Logic
    ax.annotate("", xy=(6.5, 4.9), xytext=(6.5, 6.5),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.4))
    # Copilot UI -> AI Connector
    ax.annotate("", xy=(10.45, 4.9), xytext=(10.45, 6.5),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.4))

    # Routing <-> Logic
    ax.annotate("", xy=(4.7, 4.2), xytext=(4.3, 4.2),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.4))
    # Logic <-> AI Connector
    ax.annotate("", xy=(8.7, 4.2), xytext=(8.3, 4.2),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.4))

    # Logic -> Persistence
    ax.annotate("", xy=(2.55, 2.0), xytext=(4.7, 3.5),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.4))
    # Logic -> ML Engine
    ax.annotate("", xy=(6.5, 2.0), xytext=(6.5, 3.5),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.4))
    # ML Engine <-> Registry
    ax.annotate("", xy=(8.7, 1.3), xytext=(8.3, 1.3),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.4))
    # AI Connector -> Persistence (DB Context queries)
    ax.annotate("", xy=(4.3, 1.3), xytext=(8.7, 3.5),
                arrowprops=dict(arrowstyle="<|-|>", color=arrow_col, lw=1.4))

    ax.set_xlim(0, 13.0)
    ax.set_ylim(0, 9.0)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\component_diagram_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.2, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_component_diagram('light')
render_component_diagram('dark')
