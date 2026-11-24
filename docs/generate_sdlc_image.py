import matplotlib.pyplot as plt

def render_sdlc(bg_color, box_color, border_color, text_color, arrow_color, output_path, transparent=False):
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=300)
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    row1 = ["1. Planning", "2. Requirements", "3. System Design", "4. Coding"]
    row2 = ["5. Testing", "6. Deployment", "7. Maintenance"]

    box_width = 1.7
    box_height = 0.55
    
    # 4 items in row 1
    x_row1 = [1.25, 3.45, 5.65, 7.85]
    # 3 items in row 2 (centered under 2, 3, 4)
    x_row2 = [2.35, 4.55, 6.75]
    
    y_row1 = 0.72
    y_row2 = 0.26

    box_style = dict(boxstyle="round,pad=0.55,rounding_size=0.18", 
                     fc=box_color, ec=border_color, lw=1.2)

    # Draw Row 1
    for i, (text, x) in enumerate(zip(row1, x_row1)):
        ax.text(x, y_row1, text, ha="center", va="center", color=text_color, 
                fontsize=11.5, fontweight="bold", fontfamily="sans-serif",
                bbox=box_style)
        if i < len(row1) - 1:
            ax.annotate("", xy=(x_row1[i+1] - box_width/2 - 0.08, y_row1), 
                        xytext=(x + box_width/2 + 0.08, y_row1),
                        arrowprops=dict(arrowstyle="-|>", color=arrow_color, lw=1.8, mutation_scale=13))

    # Connector from Row 1 (4. Coding) to Row 2 (5. Testing)
    ax.annotate("", xy=(x_row2[0], y_row2 + box_height/2 + 0.08),
                xytext=(x_row1[3], y_row1 - box_height/2 - 0.08),
                arrowprops=dict(arrowstyle="-|>", color=arrow_color, lw=1.8, 
                                connectionstyle="arc3,rad=-0.22", mutation_scale=13))

    # Draw Row 2
    for i, (text, x) in enumerate(zip(row2, x_row2)):
        ax.text(x, y_row2, text, ha="center", va="center", color=text_color, 
                fontsize=11.5, fontweight="bold", fontfamily="sans-serif",
                bbox=box_style)
        if i < len(row2) - 1:
            ax.annotate("", xy=(x_row2[i+1] - box_width/2 - 0.08, y_row2), 
                        xytext=(x + box_width/2 + 0.08, y_row2),
                        arrowprops=dict(arrowstyle="-|>", color=arrow_color, lw=1.8, mutation_scale=13))

    ax.set_xlim(0, 9.1)
    ax.set_ylim(0, 1.0)
    ax.axis('off')

    plt.tight_layout()
    plt.savefig(output_path, facecolor=fig.get_facecolor() if not transparent else 'none', 
                transparent=transparent, edgecolor='none', bbox_inches='tight', pad_inches=0.15)
    plt.close()
    print(f"Generated: {output_path}")

# 1. Dark theme matching user's uploaded screenshot
render_sdlc(bg_color='#18191c', box_color='#2b2d31', border_color='#3f4147', 
            text_color='#ffffff', arrow_color='#9ca3af', 
            output_path=r'C:\gowtham_mithraz\RouteMind_AI\docs\sdlc_2rows_dark.png')

# 2. Document light theme for white document pages
render_sdlc(bg_color='#ffffff', box_color='#f3f4f6', border_color='#d1d5db', 
            text_color='#111827', arrow_color='#4b5563', 
            output_path=r'C:\gowtham_mithraz\RouteMind_AI\docs\sdlc_2rows_light.png')
