import math
import matplotlib.pyplot as plt


# Set the default style for all Matplotlib plots to 'dark_background'.
# This gives charts a dark theme with light-colored text and lines.
plt.style.use('dark_background')

# A dictionary defining a consistent visual style for Seaborn boxplots.
# This ensures all boxplots have the same appearance (e.g., white whiskers, grey median line)
# to match the 'dark_background' theme.
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
    """Formats a duration from milliseconds to a "m:ss.mmm" string.

    This is useful for displaying lap times in a standard, human-readable format.

    Args:
        ms (int): The time duration in milliseconds.

    Returns:
        str: The formatted time string (e.g., "1:23.456").
    """
    # Isolate the total minutes from the milliseconds.
    minutes = ms // 60000
    # Calculate the remaining seconds after the minutes are removed.
    seconds = (ms % 60000) // 1000
    # Calculate the remaining milliseconds.
    milliseconds = ms % 1000
    
    # Construct the final formatted string with appropriate padding.
    formatted_time = f"{int(minutes):01}:{int(seconds):02}:{int(milliseconds):03}"
    
    return formatted_time


    
def drs_to_boolean(drs_value) -> bool:
    """Converts a DRS (Drag Reduction System) status code to a boolean.

    In F1 data, DRS activation is often represented by specific numerical codes.
    This function checks if the given value corresponds to an active DRS state.

    Args:
        drs_value: The numerical DRS status code from the data.

    Returns:
        bool: True if DRS was active (codes 10, 12, or 14), False otherwise.
    """
    # The values 10, 12, and 14 are known to represent an enabled DRS.
    return drs_value in [10, 12, 14]
 
    
def add_watermark(
        fig,
        watermark_text: str = "FORMULA STATS",
        alpha: float = 0.35,
        fontsize: int = None,
        rotation: int = None,
        y_position: float = 0.48
    ):
    """Adds a dynamic, centered watermark to a Matplotlib figure.

    The watermark's font size and rotation are calculated automatically based on the
    figure's dimensions to ensure it fits well on any plot size.

    Args:
        fig: The Matplotlib figure object to add the watermark to.
        watermark_text (str): The text for the watermark.
        alpha (float): The transparency of the watermark text (0.0 to 1.0).
        fontsize (int): The font size. If None, it's calculated dynamically.
        rotation (int): The rotation angle. If None, it's calculated dynamically.
        y_position (float): The vertical position of the watermark (0.0 to 1.0).

    Returns:
        The Matplotlib figure object with the watermark added.
    """
    # Get the figure width and height in pixels to calculate proportions.
    fig_width_px = fig.get_figwidth() * fig.dpi
    fig_height_px = fig.get_figheight() * fig.dpi
    
    # If fontsize is not specified, calculate it based on the figure's diagonal length.
    if fontsize is None:
        diagonal_length = math.sqrt(fig_width_px**2 + fig_height_px**2)
        dynamic_fontsize = diagonal_length * 0.023
    
    # If rotation is not specified, calculate an angle that aligns with the figure's diagonal.
    if rotation is None:
        rotation_angle = math.degrees(math.atan2(fig_height_px, fig_width_px))
    
    # Add the text to the figure with the specified or calculated properties.
    fig.text(
        x=0.5,  # Horizontally centered
        y=y_position,
        s=watermark_text,
        fontsize=dynamic_fontsize,
        color='gray',
        alpha=alpha,
        ha='center',
        va='center',
        weight='bold',
        rotation=rotation_angle,
        transform=fig.transFigure  # Coordinates are relative to the figure.
    )
    return fig


def plot_name(name):
    """A decorator factory that "tags" a function with a given name.

    This allows methods to be marked as "plot methods," which can then be
    discovered automatically by the `register_plots` class decorator.

    Args:
        name (str): The unique name to assign to the decorated function.

    Returns:
        A decorator function.
    """
    def decorator(func):
        # Attach the provided name as an attribute to the function object.
        func.plot_name = name
        return func
    return decorator


def register_plots(cls):
    """A class decorator that automatically finds and registers plot methods.

    It inspects a class for any method that has been decorated with `@plot_name`
    and populates a `PLOT_METHODS` list on the class with the names of those methods.
    This avoids the need to manually maintain a list of available plots.

    Args:
        cls: The class to be decorated.

    Returns:
        The modified class with the `PLOT_METHODS` attribute.
    """
    # Initialize an empty list on the class to store the plot names.
    cls.PLOT_METHODS = []
    
    # Iterate over all attributes (methods, variables, etc.) of the class.
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        
        # Check if the attribute is a callable method and has the 'plot_name' tag.
        if callable(attr) and hasattr(attr, 'plot_name'):
            # If it is a plot method, add its registered name to the list.
            cls.PLOT_METHODS.append(attr.plot_name)
            
    return cls