import matplotlib.pyplot as plt

def render_diagrams():
    # 1. Clean version (No curved arrow across rows, just clean sequence arrows)
    fig, ax = plt.subplots(figsize=(10, 3.8), dpi=300)
    fig.patch.set_facecolor('#18191c')
    ax.set_facecolor('#18191c')

    row1 = ["1. Planning", "2. Requirements", "3. System Design", "4. Coding"]
    row2 = ["5. Testing", "6. Deployment", "7. Maintenance"]

    box_width = 1.7
    box_height = 0.55
    
    # Coordinates
    x_row1 = [1.25, 3.45, 5.65, 7.85]
    # Center the 3 boxes in row 2 nicely
    x_row2 = [2.35, 4.55, 6.75]
    
    y_row1 = 0.72
    y_row2 = 0.28

    box_style = dict(boxstyle="round,pad=0.55,rounding_size=0.18", 
                     fc="#2b2d31", ec="#3f4147", lw=1.2)

    # Row 1
    for i, (text, x) in enumerate(zip(row1, x_row1)):
        ax.text(x, y_row1, text, ha="center", va="center", color="#ffffff", 
                fontsize=11.5, fontweight="bold", fontfamily="sans-serif",
                bbox=box_style)
        if i < len(row1) - 1:
            ax.annotate("", xy=(x_row1[i+1] - box_width/2 - 0.08, y_row1), 
                        xytext=(x + box_width/2 + 0.08, y_row1),
                        arrowprops=dict(arrowstyle="-|>", color="#9ca3af", lw=1.8, mutation_scale=13))

    # Row 2
    for i, (text, x) in enumerate(zip(row2, x_row2)):
        ax.text(x, y_row2, text, ha="center", va="center", color="#ffffff", 
                fontsize=11.5, fontweight="bold", fontfamily="sans-serif",
                bbox=box_style)
        if i < len(row2) - 1:
            ax.annotate("", xy=(x_row2[i+1] - box_width/2 - 0.08, y_row2), 
                        xytext=(x + box_width/2 + 0.08, y_row2),
                        arrowprops=dict(arrowstyle="-|>", color="#9ca3af", lw=1.8, mutation_scale=13))

    ax.set_xlim(0, 9.1)
    ax.set_ylim(0, 1.0)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(r'C:\gowtham_mithraz\RouteMind_AI\docs\sdlc_clean_no_curve_dark.png', 
                facecolor='#18191c', bbox_inches='tight', pad_inches=0.15)
    plt.savefig(r'C:\gowtham_mithraz\RouteMind_AI\docs\sdlc_clean_no_curve_light.png', 
                facecolor='#ffffff', bbox_inches='tight', pad_inches=0.15)
    plt.close()

    # 2. Version with clean 90-degree elbow step connector from 4. Coding -> 5. Testing
    fig, ax = plt.subplots(figsize=(10, 4.0), dpi=300)
    fig.patch.set_facecolor('#18191c')
    ax.set_facecolor('#18191c')

    # Row 1
    for i, (text, x) in enumerate(zip(row1, x_row1)):
        ax.text(x, y_row1, text, ha="center", va="center", color="#ffffff", 
                fontsize=11.5, fontweight="bold", fontfamily="sans-serif",
                bbox=box_style)
        if i < len(row1) - 1:
            ax.annotate("", xy=(x_row1[i+1] - box_width/2 - 0.08, y_row1), 
                        xytext=(x + box_width/2 + 0.08, y_row1),
                        arrowprops=dict(arrowstyle="-|>", color="#9ca3af", lw=1.8, mutation_scale=13))

    # Row 2
    for i, (text, x) in enumerate(zip(row2, x_row2)):
        ax.text(x, y_row2, text, ha="center", va="center", color="#ffffff", 
                fontsize=11.5, fontweight="bold", fontfamily="sans-serif",
                bbox=box_style)
        if i < len(row2) - 1:
            ax.annotate("", xy=(x_row2[i+1] - box_width/2 - 0.08, y_row2), 
                        xytext=(x + box_width/2 + 0.08, y_row2),
                        arrowprops=dict(arrowstyle="-|>", color="#9ca3af", lw=1.8, mutation_scale=13))

    # Clean elbow connector: from 4. Coding down to y_mid, left to 5. Testing, then down into 5. Testing
    # Path: (x_row1[3], y_row1 - 0.28) -> down -> left -> into top of 5. Testing
    ax.annotate("", xy=(x_row2[0], y_row2 + 0.28),
                xytext=(x_row1[3], y_row1 - 0.28),
                arrowprops=dict(arrowstyle="-|>", color="#9ca3af", lw=1.8,
                                connectionstyle="angle,angleA=0,angleB=90,rad=0", mutation_scale=13))

    ax.set_xlim(0, 9.1)
    ax.set_ylim(0, 1.0)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(r'C:\gowtham_mithraz\RouteMind_AI\docs\sdlc_step_arrow_dark.png', 
                facecolor='#18191c', bbox_inches='tight', pad_inches=0.15)
    plt.savefig(r'C:\gowtham_mithraz\RouteMind_AI\docs\sdlc_step_arrow_light.png', 
                facecolor='#ffffff', bbox_inches='tight', pad_inches=0.15)
    plt.close()

render_diagrams()
print("All generated successfully!")
