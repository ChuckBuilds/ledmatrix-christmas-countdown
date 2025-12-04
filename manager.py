"""
Christmas Countdown Plugin for LEDMatrix

Displays a countdown to Christmas with a stylized Christmas tree logo
and festive text. Shows "MERRY CHRISTMAS" on and after Christmas Day.

Features:
- Stylized Christmas tree logo (image or programmatic fallback)
- Adaptive text: "N DAYS UNTIL CHRISTMAS" or "N DAYS UNTIL XMAS" on smaller displays
- Traditional holiday colors (green tree, red text)
- Automatic "MERRY CHRISTMAS" message on/after Dec 25

API Version: 1.0.0
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from PIL import Image, ImageDraw

from src.plugin_system.base_plugin import BasePlugin

logger = logging.getLogger(__name__)


class ChristmasCountdownPlugin(BasePlugin):
    """
    Christmas countdown plugin that displays days until Christmas.
    
    Configuration options:
        enabled (bool): Enable/disable plugin
        display_duration (number): Seconds to display (default: 15)
        tree_size (number, optional): Tree logo size in pixels (auto-calculated)
        text_color (array): RGB text color [R, G, B] (default: [255, 0, 0])
        tree_color (array): RGB tree color [R, G, B] (default: [0, 128, 0])
    """
    
    def __init__(self, plugin_id: str, config: Dict[str, Any],
                 display_manager, cache_manager, plugin_manager):
        """Initialize the Christmas countdown plugin."""
        super().__init__(plugin_id, config, display_manager, cache_manager, plugin_manager)
        
        # Parse colors - convert to integers in case they come from JSON as strings
        def _parse_color(name, default):
            raw = config.get(name, default)
            try:
                return tuple(int(c) for c in raw)
            except (ValueError, TypeError):
                try:
                    return tuple(raw)
                except TypeError:
                    return raw
        
        self.text_color = _parse_color('text_color', [255, 0, 0])  # Red
        self.tree_color = _parse_color('tree_color', [0, 128, 0])  # Green
        self.tree_size = config.get('tree_size')  # None = auto-calculate
        
        # State
        self.days_until_christmas = 0
        self.is_christmas = False
        self.tree_image = None
        self.last_calculated_date = None
        self.last_displayed_message = None  # Track last displayed to prevent unnecessary redraws
        
        # Load tree image if available
        self._load_tree_image()
        
        self.logger.info("Christmas countdown plugin initialized")
    
    def _load_tree_image(self) -> None:
        """Load Christmas tree image from assets directory."""
        try:
            plugin_dir = Path(__file__).parent
            tree_path = plugin_dir / "assets" / "christmas_tree.png"
            
            if tree_path.exists():
                self.tree_image = Image.open(tree_path)
                self.logger.info(f"Loaded Christmas tree image from {tree_path}")
            else:
                self.logger.debug("Christmas tree image not found, will use programmatic drawing")
                self.tree_image = None
        except Exception as e:
            self.logger.warning(f"Error loading tree image: {e}, will use programmatic drawing")
            self.tree_image = None
    
    def _calculate_days_until_christmas(self) -> Tuple[int, bool]:
        """
        Calculate days until Christmas.
        
        Returns:
            Tuple of (days_until, is_christmas_day)
            - If before Christmas: (positive days, False)
            - If on Christmas: (0, True)
            - If after Christmas: (negative days, False)
        """
        today = date.today()
        current_year = today.year
        
        # Christmas for current year
        christmas_this_year = date(current_year, 12, 25)
        
        # If we've passed this year's Christmas, calculate for next year
        if today > christmas_this_year:
            christmas_this_year = date(current_year + 1, 12, 25)
        
        # Calculate difference
        days_diff = (christmas_this_year - today).days
        is_christmas = (today.month == 12 and today.day == 25)
        
        return days_diff, is_christmas
    
    def _draw_tree_programmatic(self, width: int, height: int, color: Tuple[int, int, int]) -> Image.Image:
        """
        Draw a fun, detailed Christmas tree programmatically.
        
        Args:
            width: Width of the tree area
            height: Height of the tree area
            color: RGB color for the tree
            
        Returns:
            PIL Image with transparent background
        """
        # Create image with transparent background
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        center_x = width // 2
        base_y = height - max(3, height // 8)  # Leave room for trunk
        
        # Draw tree layers (triangles from bottom to top) - more layers for bigger tree
        layer_count = max(4, height // 8)  # More layers for taller trees
        for i in range(layer_count):
            layer_y = base_y - (i * height // (layer_count + 2))
            layer_width = width - (i * width // (layer_count + 3))
            layer_width = max(6, layer_width)  # Minimum width
            
            # Triangle points
            top_x = center_x
            top_y = layer_y - layer_width // 2
            left_x = center_x - layer_width // 2
            left_y = layer_y
            right_x = center_x + layer_width // 2
            right_y = layer_y
            
            # Draw filled triangle
            draw.polygon(
                [(top_x, top_y), (left_x, left_y), (right_x, right_y)],
                fill=color
            )
            
            # Add some texture/decoration to layers (smaller triangles for depth)
            if i > 0 and layer_width > 8:
                # Add some highlights
                highlight_color = tuple(min(255, c + 20) for c in color)
                small_triangle_size = layer_width // 4
                for offset in [-small_triangle_size // 2, small_triangle_size // 2]:
                    if abs(offset) < layer_width // 2 - 2:
                        draw.polygon(
                            [(center_x + offset, layer_y - small_triangle_size),
                             (center_x + offset - small_triangle_size // 2, layer_y),
                             (center_x + offset + small_triangle_size // 2, layer_y)],
                            fill=highlight_color
                        )
        
        # Draw trunk (rectangle at bottom center)
        trunk_width = max(3, width // 6)
        trunk_height = max(4, height // 6)
        trunk_x = center_x - trunk_width // 2
        trunk_y = height - trunk_height
        trunk_color = (101, 67, 33)  # Brown
        
        draw.rectangle(
            [trunk_x, trunk_y, trunk_x + trunk_width, height],
            fill=trunk_color
        )
        
        # Add a star on top (yellow, more detailed)
        star_size = max(3, min(width // 8, height // 10))
        star_y = top_y - star_size - 1
        star_color = (255, 255, 0)  # Yellow
        
        # Draw star as a filled circle with points
        draw.ellipse(
            [center_x - star_size, star_y - star_size,
             center_x + star_size, star_y + star_size],
            fill=star_color
        )
        
        # Add ornaments (red circles) on various layers
        if width >= 16 and height >= 20:
            ornament_color = (255, 0, 0)  # Red
            ornament_size = max(1, min(width // 16, 3))
            
            # Add ornaments on different layers
            for layer_idx in [1, 2, 3]:
                if layer_idx < layer_count:
                    layer_y = base_y - (layer_idx * height // (layer_count + 2))
                    layer_width = width - (layer_idx * width // (layer_count + 3))
                    
                    # Left ornament
                    if layer_width > 12:
                        left_orn_x = center_x - layer_width // 3
                        draw.ellipse(
                            [left_orn_x - ornament_size, layer_y - ornament_size,
                             left_orn_x + ornament_size, layer_y + ornament_size],
                            fill=ornament_color
                        )
                    
                    # Right ornament (alternating layers)
                    if layer_idx % 2 == 0 and layer_width > 12:
                        right_orn_x = center_x + layer_width // 3
                        draw.ellipse(
                            [right_orn_x - ornament_size, layer_y - ornament_size,
                             right_orn_x + ornament_size, layer_y + ornament_size],
                            fill=ornament_color
                        )
        
        return img
    
    def _get_tree_image(self, width: int, height: int) -> Optional[Image.Image]:
        """
        Get Christmas tree image at specified dimensions.
        
        Args:
            width: Desired width in pixels
            height: Desired height in pixels
            
        Returns:
            PIL Image at specified dimensions
        """
        if self.tree_image:
            # Resize existing image to fit the dimensions
            return self.tree_image.resize((width, height), Image.LANCZOS)
        else:
            # Draw programmatically with new dimensions
            return self._draw_tree_programmatic(width, height, self.tree_color)
    
    def update(self) -> None:
        """
        Update countdown calculation.
        
        Called periodically to recalculate days until Christmas.
        """
        try:
            days, is_christmas = self._calculate_days_until_christmas()
            self.days_until_christmas = days
            self.is_christmas = is_christmas
            
            # Only log when the day changes
            today = date.today()
            if self.last_calculated_date != today:
                if is_christmas:
                    self.logger.info("Merry Christmas!")
                else:
                    self.logger.info(f"Days until Christmas: {days}")
                self.last_calculated_date = today
                
        except Exception as e:
            self.logger.error(f"Error updating countdown: {e}")
    
    def display(self, force_clear: bool = False) -> None:
        """
        Display the Christmas countdown with split-screen layout.
        Tree on left, stacked text on right.
        
        Args:
            force_clear: If True, clear display before rendering
        """
        try:
            # Ensure update() has been called
            if not hasattr(self, 'days_until_christmas'):
                self.update()
            
            # Get display dimensions
            width = self.display_manager.width
            height = self.display_manager.height
            
            # Determine if display is "small" (use XMAS instead of CHRISTMAS)
            is_small_display = width < 64
            
            # Determine text to display
            if self.is_christmas or self.days_until_christmas == 0:
                message = "MERRY CHRISTMAS"
            else:
                if is_small_display:
                    message = f"{self.days_until_christmas} DAYS UNTIL XMAS"
                else:
                    message = f"{self.days_until_christmas} DAYS UNTIL CHRISTMAS"
            
            # Check if we need to redraw (prevent blinking)
            # Only redraw if the message changed or force_clear is True
            if not force_clear and self.last_displayed_message == message:
                return  # No change, skip redraw
            
            # Clear display
            self.display_manager.clear()
            
            # Split display in half: tree on left, text on right
            left_half_width = width // 2
            right_half_width = width - left_half_width
            right_half_x = left_half_width
            
            # Calculate tree dimensions (use most of left half, leave small margin)
            tree_margin = 2
            tree_width = left_half_width - (2 * tree_margin)
            tree_height = height - (2 * tree_margin)
            tree_x = tree_margin
            tree_y = tree_margin
            
            # Get tree image (bigger and more fun!)
            tree_img = self._get_tree_image(tree_width, tree_height)
            
            # Draw tree on left side
            if tree_img:
                # Paste tree onto display (handle RGBA with alpha channel)
                if tree_img.mode == 'RGBA':
                    self.display_manager.image.paste(tree_img, (tree_x, tree_y), tree_img)
                else:
                    self.display_manager.image.paste(tree_img, (tree_x, tree_y))
            
            # Stack text on right side
            # Split message into words/lines for stacking
            if self.is_christmas or self.days_until_christmas == 0:
                # "MERRY CHRISTMAS" - split into two lines
                lines = ["MERRY", "CHRISTMAS"]
            else:
                # Countdown message - split intelligently
                if is_small_display:
                    # "N DAYS UNTIL XMAS"
                    parts = message.split()
                    if len(parts) >= 4:
                        lines = [
                            f"{self.days_until_christmas}",
                            "DAYS",
                            "UNTIL",
                            "XMAS"
                        ]
                    else:
                        lines = [message]
                else:
                    # "N DAYS UNTIL CHRISTMAS"
                    parts = message.split()
                    if len(parts) >= 4:
                        lines = [
                            f"{self.days_until_christmas}",
                            "DAYS",
                            "UNTIL",
                            "CHRISTMAS"
                        ]
                    else:
                        lines = [message]
            
            # Calculate text positioning on right side (centered vertically)
            num_lines = len(lines)
            line_height = 8 if is_small_display else 10
            total_text_height = num_lines * line_height
            start_y = (height - total_text_height) // 2
            
            # Draw each line of text, centered horizontally in right half
            for i, line in enumerate(lines):
                text_y = start_y + (i * line_height)
                # Calculate center point of right half for centering
                right_half_center_x = right_half_x + (right_half_width // 2)
                self.display_manager.draw_text(
                    line,
                    x=right_half_center_x,
                    y=text_y,
                    color=self.text_color,
                    small_font=is_small_display,
                    centered=True
                )
            
            # Update the physical display
            self.display_manager.update_display()
            
            # Track what we displayed to prevent unnecessary redraws
            self.last_displayed_message = message
            self.logger.debug(f"Displayed: {message}")
            
        except Exception as e:
            self.logger.error(f"Error displaying countdown: {e}", exc_info=True)
            # Show error message on display
            try:
                self.display_manager.clear()
                self.display_manager.draw_text(
                    "Countdown Error",
                    x=5, y=15,
                    color=(255, 0, 0)
                )
                self.display_manager.update_display()
            except:
                pass  # If display fails, don't crash
    
    def validate_config(self) -> bool:
        """Validate plugin configuration."""
        # Call parent validation first
        if not super().validate_config():
            return False
        
        # Validate colors
        for color_name, color_value in [
            ("text_color", self.text_color),
            ("tree_color", self.tree_color)
        ]:
            if not isinstance(color_value, tuple) or len(color_value) != 3:
                self.logger.error(f"Invalid {color_name}: must be RGB tuple")
                return False
            try:
                # Convert to integers and validate range
                color_ints = [int(c) for c in color_value]
                if not all(0 <= c <= 255 for c in color_ints):
                    self.logger.error(f"Invalid {color_name}: values must be 0-255")
                    return False
            except (ValueError, TypeError):
                self.logger.error(f"Invalid {color_name}: values must be numeric")
                return False
        
        # Validate tree_size if provided
        if self.tree_size is not None:
            if not isinstance(self.tree_size, (int, float)) or self.tree_size <= 0:
                self.logger.error("tree_size must be a positive number")
                return False
        
        return True
    
    def get_info(self) -> Dict[str, Any]:
        """Return plugin info for web UI."""
        info = super().get_info()
        info.update({
            'days_until_christmas': getattr(self, 'days_until_christmas', None),
            'is_christmas': getattr(self, 'is_christmas', False),
            'text_color': self.text_color,
            'tree_color': self.tree_color,
            'tree_size': self.tree_size
        })
        return info

