import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_auth_node(ax, x, y, w, h, text, bg, border, text_col, radius=0.08, fontsize=8.8):
    rect = patches.FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    ax.text(x, y, text, ha='center', va='center', color=text_col,
            fontsize=fontsize, fontweight='bold', fontfamily='sans-serif', multialignment='center')

def draw_auth_decision(ax, x, y, size, text, bg, border, text_col, fontsize=8.0):
    d = size / 2
    poly = patches.Polygon([[x, y + d], [x + d*1.3, y], [x, y - d], [x - d*1.3, y]],
                           closed=True, linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(poly)
    ax.text(x, y, text, ha='center', va='center', color=text_col,
            fontsize=fontsize, fontweight='bold', fontfamily='sans-serif', multialignment='center')

def render_auth_diagram(theme='dark'):
    fig, ax = plt.subplots(figsize=(14, 9), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        border_col = '#3e4046'
        text_col = '#f8fafc'
        sub_col = '#94a3b8'
        arrow_col = '#cbd5e1'
        decision_bg = '#1e293b'
        start_col = '#10b981' # Green
        error_col = '#ef4444' # Red
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        sub_col = '#475569'
        arrow_col = '#334155'
        decision_bg = '#e2e8f0'
        start_col = '#059669'
        error_col = '#dc2626'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    # Left Track: Standard Login (x = 3.5)
    # Right Track: Forgot Password & Email OTP (x = 10.5)

    # Track 1 Header
    ax.text(3.5, 8.4, "Standard Login Workflow", ha='center', va='center', color=sub_col, fontsize=11, fontweight='bold')
    # Track 2 Header
    ax.text(10.5, 8.4, "Forgot Password & OTP Workflow", ha='center', va='center', color=sub_col, fontsize=11, fontweight='bold')

    # 1. Login Track
    # Start circle
    c1 = patches.Circle((3.5, 7.8), 0.22, facecolor=start_col, edgecolor=border_col, lw=1.2)
    ax.add_patch(c1)
    ax.text(3.5, 7.8, "Start", ha='center', va='center', color='#ffffff', fontsize=7.5, fontweight='bold')

    ax.annotate("", xy=(3.5, 6.9), xytext=(3.5, 7.55), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    draw_auth_node(ax, 3.5, 6.4, 3.8, 0.9, "User Enters Email & Password\non /login Form", box_bg, border_col, text_col)

    ax.annotate("", xy=(3.5, 5.4), xytext=(3.5, 5.95), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    draw_auth_decision(ax, 3.5, 4.7, 1.3, "Valid\nPassword?", decision_bg, border_col, text_col)

    # Valid -> Yes (Down)
    ax.annotate("", xy=(3.5, 3.5), xytext=(3.5, 4.05), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.text(3.8, 3.8, "[Yes]", color=start_col, fontsize=8.5, fontweight='bold')
    draw_auth_node(ax, 3.5, 2.9, 4.0, 1.0, "Create Secure Session Cookie\n& Redirect to Control Tower", box_bg, border_col, text_col)

    # Valid -> No (Left)
    ax.plot([2.65, 1.0, 1.0], [4.7, 4.7, 3.4], color=error_col, lw=1.3)
    ax.annotate("", xy=(1.0, 3.4), xytext=(1.0, 3.5), arrowprops=dict(arrowstyle="-|>", color=error_col, lw=1.3))
    ax.text(1.8, 4.9, "[No: Invalid]", color=error_col, fontsize=8.0, fontweight='bold')
    draw_auth_node(ax, 1.0, 2.9, 1.8, 0.9, "Show Error:\nInvalid Login", box_bg, error_col, text_col, fontsize=8.0)

    # Login End
    ax.annotate("", xy=(3.5, 1.6), xytext=(3.5, 2.4), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    c1_end = patches.Circle((3.5, 1.2), 0.28, facecolor='none', edgecolor=start_col, lw=1.6)
    c1_inner = patches.Circle((3.5, 1.2), 0.18, facecolor=start_col, edgecolor='none')
    ax.add_patch(c1_end)
    ax.add_patch(c1_inner)
    ax.text(3.5, 0.7, "Logged In", ha='center', va='center', color=text_col, fontsize=9.0, fontweight='bold')

    # Divider line
    ax.plot([7.0, 7.0], [0.8, 8.5], color=border_col, linestyle='--', lw=1.2)

    # 2. OTP & Forgot Password Track
    c2 = patches.Circle((10.5, 7.8), 0.22, facecolor=start_col, edgecolor=border_col, lw=1.2)
    ax.add_patch(c2)
    ax.text(10.5, 7.8, "Start", ha='center', va='center', color='#ffffff', fontsize=7.5, fontweight='bold')

    ax.annotate("", xy=(10.5, 6.9), xytext=(10.5, 7.55), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    draw_auth_node(ax, 10.5, 6.4, 4.2, 0.9, "User Enters Registered Email\non /forgot-password", box_bg, border_col, text_col)

    ax.annotate("", xy=(10.5, 5.4), xytext=(10.5, 5.95), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    draw_auth_node(ax, 10.5, 4.9, 4.2, 0.9, "Generate 6-Digit Secret OTP\n& Send via Gmail SMTP", box_bg, border_col, text_col)

    ax.annotate("", xy=(10.5, 3.9), xytext=(10.5, 4.45), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    draw_auth_decision(ax, 10.5, 3.2, 1.3, "Valid OTP\n< 10 Mins?", decision_bg, border_col, text_col)

    # Valid OTP -> Yes (Down)
    ax.annotate("", xy=(10.5, 2.0), xytext=(10.5, 2.55), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.text(10.8, 2.3, "[Yes]", color=start_col, fontsize=8.5, fontweight='bold')
    draw_auth_node(ax, 10.5, 1.5, 4.2, 0.9, "User Enters New Password\n(Hash & Update Database)", box_bg, border_col, text_col)

    # Valid OTP -> No (Right)
    ax.plot([11.35, 13.0, 13.0], [3.2, 3.2, 2.0], color=error_col, lw=1.3)
    ax.annotate("", xy=(13.0, 2.0), xytext=(13.0, 2.1), arrowprops=dict(arrowstyle="-|>", color=error_col, lw=1.3))
    ax.text(12.2, 3.4, "[No: Expired]", color=error_col, fontsize=8.0, fontweight='bold')
    draw_auth_node(ax, 13.0, 1.5, 1.8, 0.9, "Show Error:\nInvalid OTP", box_bg, error_col, text_col, fontsize=8.0)

    # OTP Reset End
    ax.annotate("", xy=(10.5, 0.5), xytext=(10.5, 1.05), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    c2_end = patches.Circle((10.5, 0.2), 0.28, facecolor='none', edgecolor=start_col, lw=1.6)
    c2_inner = patches.Circle((10.5, 0.2), 0.18, facecolor=start_col, edgecolor='none')
    ax.add_patch(c2_end)
    ax.add_patch(c2_inner)
    ax.text(10.5, -0.3, "Password Reset Complete", ha='center', va='center', color=text_col, fontsize=9.0, fontweight='bold')

    ax.set_xlim(-0.2, 14.5)
    ax.set_ylim(-0.8, 8.8)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\auth_workflow_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_auth_diagram('light')
render_auth_diagram('dark')
