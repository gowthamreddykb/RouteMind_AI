import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_balanced_card(ax, x, y, w, h, stage_num, title, items, bg, border, title_bg, text_col, sub_col, tag_col):
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    th = 0.50
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.2, edgecolor=border, facecolor=title_bg)
    ax.add_patch(tbox)
    
    badge = patches.Circle((x + 0.35, y + h - th/2), 0.18, facecolor=tag_col, edgecolor=border, lw=1)
    ax.add_patch(badge)
    ax.text(x + 0.35, y + h - th/2, str(stage_num), ha='center', va='center',
            color='#ffffff', fontsize=8.2, fontweight='bold', fontfamily='sans-serif')

    ax.text(x + 0.65, y + h - th/2, title, ha='left', va='center',
            color=text_col, fontsize=8.8, fontweight='bold', fontfamily='sans-serif')
    ax.plot([x, x + w], [y + h - th, y + h - th], color=border, lw=1.0)

    cy = y + h - th - 0.22
    for item in items:
        ax.text(x + 0.18, cy, item, ha='left', va='center', color=sub_col, fontsize=7.5, fontfamily='sans-serif')
        cy -= 0.24

def render_balanced_testing_pipeline(theme='dark'):
    fig, ax = plt.subplots(figsize=(15, 8.8), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        title_bg = '#1e293b'
        border_col = '#3e4046'
        text_col = '#f8fafc'
        sub_col = '#cbd5e1'
        arrow_col = '#94a3b8'
        c_test = '#38bdf8'   # Cyan
        c_ml = '#a855f7'     # Purple
        c_env = '#f59e0b'    # Amber
        c_deploy = '#3b82f6' # Blue
        c_ops = '#10b981'    # Green
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        title_bg = '#e2e8f0'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        sub_col = '#475569'
        arrow_col = '#475569'
        c_test = '#0284c7'
        c_ml = '#9333ea'
        c_env = '#d97706'
        c_deploy = '#2563eb'
        c_ops = '#059669'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    w = 3.3
    h = 2.4

    # 4 columns:
    # Col 1: x = 0.6
    # Col 2: x = 4.3
    # Col 3: x = 8.0
    # Col 4: x = 11.7
    
    # Row 1 (y = 4.8): 1 -> 2 -> 3 -> 4
    # Row 2 (y = 1.0): 8 <- 7 <- 6 <- 5 (perfect 4x2 grid, NO empty corner!)

    # 1. Unit & Integration Tests (Col 1, Row 1)
    draw_balanced_card(ax, 0.6, 4.8, w, h, 1, "Unit & Integration Tests",
                       ["• Pytest test suite execution",
                        "• Password hashing & token tests",
                        "• Database CRUD & model methods",
                        "• REST endpoint responses (200 OK)",
                        "• Session cookie persistence"],
                       box_bg, border_col, title_bg, text_col, sub_col, c_test)

    # 2. Security & Role Tests (Col 2, Row 1)
    draw_balanced_card(ax, 4.3, 4.8, w, h, 2, "Security & Role Tests",
                       ["• @role_required decorator checks",
                        "• Dispatcher blocked from admin views",
                        "• HTTP 403 Forbidden validation",
                        "• CSRF token attack mitigation",
                        "• OTP 10-minute expiration limits"],
                       box_bg, border_col, title_bg, text_col, sub_col, c_test)

    # 3. ML Model Validation (Col 3, Row 1)
    draw_balanced_card(ax, 8.0, 4.8, w, h, 3, "ML Model Validation",
                       ["• Accuracy & F1-score balance",
                        "• ROC-AUC curves on test datasets",
                        "• Sub-50ms in-memory prediction",
                        "• CatBoost MAE delay evaluation",
                        "• Feature preprocessing parity"],
                       box_bg, border_col, title_bg, text_col, sub_col, c_ml)

    # 4. AI & Mail Integration (Col 4, Row 1 - Top Right)
    draw_balanced_card(ax, 11.7, 4.8, w, h, 4, "AI & Mail Integration",
                       ["• Groq / Gemini API context tests",
                        "• Anti-hallucination verification",
                        "• Markdown link rendering",
                        "• Gmail SMTP TLS dispatch checks",
                        "• Delivery log database commits"],
                       box_bg, border_col, title_bg, text_col, sub_col, c_ml)

    # Row 1 Arrows: 1 -> 2 -> 3 -> 4
    ax.annotate("", xy=(4.3, 6.0), xytext=(3.9, 6.0), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.annotate("", xy=(8.0, 6.0), xytext=(7.6, 6.0), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.annotate("", xy=(11.7, 6.0), xytext=(11.3, 6.0), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # Clean straight downward arrow from 4 directly into 5 (Top Right to Bottom Right!)
    ax.annotate("", xy=(13.35, 3.4), xytext=(13.35, 4.8), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.6))

    # 5. Environment & Secrets (Col 4, Row 2 - Bottom Right: Fills the gap!)
    draw_balanced_card(ax, 11.7, 1.0, w, h, 5, "Environment & Secrets",
                       ["• Production .env configuration",
                        "• Database URI & Secret Keys",
                        "• SMTP & Groq API tokens secured",
                        "• Joblib model artifacts verified",
                        "• Strict file permissions set"],
                       box_bg, border_col, title_bg, text_col, sub_col, c_env)

    # 6. Database Migration (Col 3, Row 2)
    draw_balanced_card(ax, 8.0, 1.0, w, h, 6, "Database Migration",
                       ["• Alembic / Flask-Migrate schema sync",
                        "• 12 relational tables verified",
                        "• Foreign key constraints checked",
                        "• Indexing on search columns",
                        "• Seed master data committed"],
                       box_bg, border_col, title_bg, text_col, sub_col, c_deploy)

    # 7. Cloud WSGI Hosting (Col 2, Row 2)
    draw_balanced_card(ax, 4.3, 1.0, w, h, 7, "Cloud WSGI Hosting",
                       ["• Zoho Catalyst / AppSail platform",
                        "• Multi-worker WSGI daemon",
                        "• Production HTTPS SSL certificate",
                        "• Health check endpoint (/health)",
                        "• Connection pool management"],
                       box_bg, border_col, title_bg, text_col, sub_col, c_deploy)

    # 8. Maintenance & Monitoring (Col 1, Row 2 - Bottom Left)
    draw_balanced_card(ax, 0.6, 1.0, w, h, 8, "Maintenance & Drift",
                       ["• Automated audit log inspection",
                        "• Model prediction drift detection",
                        "• Scheduled pipeline retraining",
                        "• Database vacuum & indexing",
                        "• Zero-downtime rolling updates"],
                       box_bg, border_col, title_bg, text_col, sub_col, c_ops)

    # Row 2 Arrows: 5 -> 6 -> 7 -> 8 (Right to Left)
    ax.annotate("", xy=(11.3, 2.2), xytext=(11.7, 2.2), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.annotate("", xy=(7.6, 2.2), xytext=(8.0, 2.2), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.annotate("", xy=(3.9, 2.2), xytext=(4.3, 2.2), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    # Bottom Tagline
    banner = patches.FancyBboxPatch((0.6, 0.18), 14.4, 0.52, boxstyle="round,pad=0,rounding_size=0.06",
                                   linewidth=1.1, edgecolor=border_col, facecolor=title_bg)
    ax.add_patch(banner)
    ax.text(7.8, 0.44, "Continuous Verification: Comprehensive automated testing and cloud deployment ensure 99.9% uptime and sub-second predictions.",
            ha='center', va='center', color=c_ops, fontsize=8.2, fontweight='bold', fontfamily='sans-serif')

    ax.set_xlim(0, 15.6)
    ax.set_ylim(0.0, 7.6)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\testing_pipeline_balanced_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated balanced diagram: {out}")

render_balanced_testing_pipeline('light')
render_balanced_testing_pipeline('dark')
