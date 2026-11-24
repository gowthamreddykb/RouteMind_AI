import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_card(ax, x, y, w, h, title, subtitle, items, bg, border, title_bg, text_col, sub_col, tag_col):
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                 linewidth=1.2, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    
    th = 0.52
    tbox = patches.FancyBboxPatch((x, y + h - th), w, th, boxstyle="round,pad=0,rounding_size=0.08",
                                  linewidth=1.2, edgecolor=border, facecolor=title_bg)
    ax.add_patch(tbox)
    
    ax.text(x + 0.15, y + h - th/2, title, ha='left', va='center',
            color=text_col, fontsize=9.2, fontweight='bold', fontfamily='sans-serif')
    
    badge = patches.FancyBboxPatch((x + w - 0.95, y + h - th + 0.10), 0.82, 0.30,
                                  boxstyle="round,pad=0,rounding_size=0.04",
                                  linewidth=0.8, edgecolor=border, facecolor=tag_col)
    ax.add_patch(badge)
    ax.text(x + w - 0.54, y + h - th/2, subtitle, ha='center', va='center',
            color='#ffffff', fontsize=7.2, fontweight='bold', fontfamily='sans-serif')
    
    ax.plot([x, x + w], [y + h - th, y + h - th], color=border, lw=1.0)

    cy = y + h - th - 0.24
    for item in items:
        ax.text(x + 0.20, cy, item, ha='left', va='center', color=sub_col, fontsize=7.8, fontfamily='sans-serif')
        cy -= 0.25

def render_genai_diagram(theme='dark'):
    fig, ax = plt.subplots(figsize=(15, 9.5), dpi=300)
    
    if theme == 'dark':
        bg_main = '#16171a'
        box_bg = '#222327'
        title_bg = '#1e293b'
        border_col = '#3e4046'
        text_col = '#f8fafc'
        sub_col = '#cbd5e1'
        arrow_col = '#94a3b8'
        c_user = '#38bdf8'
        c_db = '#34d399'
        c_llm = '#a855f7'
        c_out = '#f59e0b'
        c_human = '#10b981'
    else:
        bg_main = '#ffffff'
        box_bg = '#f8fafc'
        title_bg = '#e2e8f0'
        border_col = '#cbd5e1'
        text_col = '#0f172a'
        sub_col = '#475569'
        arrow_col = '#475569'
        c_user = '#0284c7'
        c_db = '#059669'
        c_llm = '#9333ea'
        c_out = '#d97706'
        c_human = '#059669'

    fig.patch.set_facecolor(bg_main)
    ax.set_facecolor(bg_main)

    w = 3.4
    h = 2.4

    # Row 1 (Top, y = 6.4): User Input -> DB Grounding Context -> LLM Engine
    draw_card(ax, 0.6, 6.4, w, h, "1. User Input", "QUERY",
              ["• Operator asks natural language question",
               "  (e.g., 'Which shipments are delayed today?')",
               "• Or clicks 'Auto-Draft Carrier SLA Notice'",
               "• Received via secure REST API endpoint"],
              box_bg, border_col, title_bg, text_col, sub_col, c_user)

    draw_card(ax, 5.8, 6.4, w, h, "2. Database Grounding", "CONTEXT",
              ["• Queries live MySQL / SQLite database",
               "• Extracts active shipments, risk tiers,",
               "  delay probabilities & open exceptions",
               "• Formats data into verified JSON payload"],
              box_bg, border_col, title_bg, text_col, sub_col, c_db)

    draw_card(ax, 11.0, 6.4, w, h, "3. LLM Reasoning Engine", "GROQ / GEMINI",
              ["• Connects to Groq / Gemini API",
               "• Strict Anti-Hallucination system prompt",
               "• Grounded purely in database JSON context",
               "• Formats responses in clean Markdown"],
              box_bg, border_col, title_bg, text_col, sub_col, c_llm)

    # Horizontal Top Arrows
    ax.annotate("", xy=(5.8, 7.6), xytext=(4.0, 7.6), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.text(4.9, 7.85, "SQL Lookup", ha='center', va='center', color=sub_col, fontsize=7.8, fontweight='bold')

    ax.annotate("", xy=(11.0, 7.6), xytext=(9.2, 7.6), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))
    ax.text(10.1, 7.85, "Prompt + Data", ha='center', va='center', color=sub_col, fontsize=7.8, fontweight='bold')

    # Row 2 (Middle, y = 3.2): Two Output Channels
    # Channel A: Interactive Chat Copilot (Left, x = 1.8)
    draw_card(ax, 1.8, 3.2, 4.8, 2.3, "Output A: AI Copilot Chat Response", "CONVERSATION",
              ["• Answers user questions directly inside web chat drawer",
               "• Provides actionable root-cause recommendations",
               "• Generates direct clickable links to /shipments/<number>",
               "• Persists chat history in chat_messages table"],
              box_bg, border_col, title_bg, text_col, sub_col, c_out)

    # Channel B: Automated Email Draft (Right, x = 8.4)
    draw_card(ax, 8.4, 3.2, 4.8, 2.3, "Output B: Automated SLA Notice Draft", "EMAIL DRAFT",
              ["• Generates professional carrier breach warning emails",
               "• Includes tracking code, container ID, and delay days",
               "• Stored as DRAFT in communications table",
               "• Ready for mandatory human review and sign-off"],
              box_bg, border_col, title_bg, text_col, sub_col, c_out)

    # Connect LLM (Top Right) to Both Channels
    ax.plot([12.7, 12.7, 10.8], [6.4, 5.8, 5.5], color=arrow_col, lw=1.4)
    ax.plot([12.7, 4.2], [5.8, 5.8], color=arrow_col, lw=1.4)
    ax.annotate("", xy=(4.2, 5.5), xytext=(4.2, 5.8), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4))
    ax.annotate("", xy=(10.8, 5.5), xytext=(10.8, 5.8), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.4))

    # Row 3 (Bottom, y = 0.5): Human-in-the-Loop & SMTP Dispatch
    hitl_box = patches.FancyBboxPatch((0.6, 0.5), 13.8, 1.8, boxstyle="round,pad=0,rounding_size=0.08",
                                     linewidth=1.2, edgecolor=border_col, facecolor=box_bg)
    ax.add_patch(hitl_box)
    th_hitl = 0.45
    tbox_hitl = patches.FancyBboxPatch((0.6, 0.5 + 1.8 - th_hitl), 13.8, th_hitl, boxstyle="round,pad=0,rounding_size=0.08",
                                       linewidth=1.2, edgecolor=border_col, facecolor=title_bg)
    ax.add_patch(tbox_hitl)
    ax.text(0.8, 0.5 + 1.8 - th_hitl/2, "4. Human-in-the-Loop Control & SMTP Delivery", ha='left', va='center',
            color=text_col, fontsize=9.2, fontweight='bold', fontfamily='sans-serif')
    ax.text(1.0, 1.25, "• Mandatory Human Review: Dispatchers can review, modify, or cancel any AI-generated communication draft before sending.",
            color=sub_col, fontsize=8.2, fontfamily='sans-serif')
    ax.text(1.0, 0.85, "• Secure Delivery: Upon manual operator approval, email is dispatched via Gmail SMTP, and delivery status is logged in communication_logs.",
            color=sub_col, fontsize=8.2, fontfamily='sans-serif')

    # Arrow from Channel B down to Human Review
    ax.annotate("", xy=(10.8, 2.3), xytext=(10.8, 3.2), arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5))

    ax.set_xlim(0, 15.0)
    ax.set_ylim(0.2, 9.2)
    ax.axis('off')

    plt.tight_layout()
    out = rf'C:\gowtham_mithraz\RouteMind_AI\docs\genai_communications_arch_{theme}.png'
    plt.savefig(out, facecolor=bg_main, bbox_inches='tight', pad_inches=0.15, dpi=300)
    plt.close()
    print(f"Generated: {out}")

render_genai_diagram('light')
render_genai_diagram('dark')
