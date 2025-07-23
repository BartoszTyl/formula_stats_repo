import math
import matplotlib.pyplot as plt


# Set plots to dark background
plt.style.use('dark_background')

# Seaborn boxplot styling
SNS_BOXPLOT_STYLE = {
    "whiskerprops": dict(color="white"),
    "boxprops": dict(edgecolor="white"),
    "medianprops": dict(color="grey", linewidth=2),
    "capprops": dict(color="white"),
    "flierprops": dict(marker='o', markerfacecolor='lightgrey', markersize=5, linestyle='none'),
    "width": 0.6,
    "dodge": False
}


def format_lap_time(ms: int) -> str:
    """Format time in milliseconds to m:ss:mmm"""
    # Convert milliseconds to seconds
    minutes = ms // 60000  # 1 minute = 60,000 milliseconds
    seconds = (ms % 60000) // 1000  # Remaining seconds after minutes
    milliseconds = ms % 1000  # Remaining milliseconds after seconds
    
    # Format the lap time as mm:ss:ms
    formatted_time = f"{int(minutes):01}:{int(seconds):02}:{int(milliseconds):03}"
    
    return formatted_time


    
def drs_to_boolean(drs_value) -> bool:
    """Convert DRS value to boolean"""
    
    return drs_value in [10, 12, 14]
 
    


def add_watermark(
        fig,
        watermark_text: str = "FORMULA STATS",
        alpha: int = 0.35,
        fontsize: int = None,
        rotation: int = None,
        y_position: float = 0.48
    ):
    """Add FORMULA STATS watermark to plots"""

    # Get the figure width and height in pixels
    fig_width_px = fig.get_figwidth() * fig.dpi
    fig_height_px = fig.get_figheight() * fig.dpi
    
    if fontsize is None:
        diagonal_length = math.sqrt(fig_width_px**2 + fig_height_px**2)
        dynamic_fontsize = diagonal_length * 0.023
    
    if rotation is None:
        rotation_angle = math.degrees(math.atan2(fig_height_px, fig_width_px))
    
    
    fig.text(
        0.5, y_position,
        watermark_text,
        fontsize=dynamic_fontsize,
        color='gray',
        alpha=alpha,
        ha='center',
        va='center',
        weight='bold',
        rotation=rotation_angle,
        transform=fig.transFigure
    )
    return fig



