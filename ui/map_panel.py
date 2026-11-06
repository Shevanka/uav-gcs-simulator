"""Flight Path 2D Map and Real-Time Charts Panel for GCS Dashboard."""

from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional, Tuple

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FlightMapCanvas(QWidget):
    """Embeds Matplotlib canvas for 2D Flight Path Tracking and Altitude/Battery Strip Charts."""

    def __init__(self, max_history: int = 300, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.max_history = max_history

        # Data buffers
        self.latitudes: Deque[float] = deque(maxlen=max_history)
        self.longitudes: Deque[float] = deque(maxlen=max_history)
        self.altitudes: Deque[float] = deque(maxlen=max_history)
        self.batteries: Deque[float] = deque(maxlen=max_history)
        self.time_indices: Deque[int] = deque(maxlen=max_history)
        self._step_counter = 0

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Matplotlib Figure with 2 Subplots (Top: GPS Map, Bottom: Altitude/Battery)
        self.fig = Figure(figsize=(6, 6), facecolor="#181825")
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet("background-color: transparent;")

        # Subplot 1: 2D GPS Map
        self.ax_map = self.fig.add_subplot(2, 1, 1)
        self._style_axis(self.ax_map, "UAV GPS 2D FLIGHT PATH", "Longitude (°)", "Latitude (°)")

        # Subplot 2: Altitude & Battery
        self.ax_alt = self.fig.add_subplot(2, 1, 2)
        self._style_axis(self.ax_alt, "ALTITUDE & BATTERY HISTORY", "Simulation Steps", "Altitude (m)")
        self.ax_bat = self.ax_alt.twinx()
        self.ax_bat.set_ylabel("Battery (%)", color="#a6e3a1", fontsize=9)
        self.ax_bat.tick_params(colors="#a6e3a1", labelsize=8)

        self.fig.tight_layout(pad=2.0)
        layout.addWidget(self.canvas)

    def _style_axis(self, ax, title: str, xlabel: str, ylabel: str) -> None:
        """Apply dark theme styling to a matplotlib axis."""
        ax.set_facecolor("#2b2b3d")
        ax.set_title(title, color="#cdd6f4", fontsize=10, fontweight="bold", pad=8)
        ax.set_xlabel(xlabel, color="#bac2de", fontsize=9)
        ax.set_ylabel(ylabel, color="#89b4fa", fontsize=9)
        ax.tick_params(colors="#bac2de", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#45475a")
        ax.grid(True, linestyle="--", alpha=0.3, color="#585b70")

    def add_telemetry_point(
        self,
        latitude: float,
        longitude: float,
        altitude: float,
        battery: float,
        heading: float,
    ) -> None:
        """Append new telemetry coordinates and redraw plots."""
        self._step_counter += 1
        self.latitudes.append(latitude)
        self.longitudes.append(longitude)
        self.altitudes.append(altitude)
        self.batteries.append(battery)
        self.time_indices.append(self._step_counter)

        self._render_map(heading)
        self._render_charts()
        self.canvas.draw_idle()

    def _render_map(self, heading: float) -> None:
        """Render 2D top-down flight path and UAV marker."""
        self.ax_map.clear()
        self._style_axis(self.ax_map, "UAV GPS 2D FLIGHT PATH", "Longitude (°)", "Latitude (°)")

        if len(self.longitudes) > 1:
            # Trajectory Line
            self.ax_map.plot(
                list(self.longitudes),
                list(self.latitudes),
                color="#89b4fa",
                linewidth=1.8,
                label="Flight Path",
            )
            # Start Point
            self.ax_map.scatter(
                [self.longitudes[0]],
                [self.latitudes[0]],
                color="#a6e3a1",
                s=40,
                marker="o",
                label="Start",
                zorder=5,
            )

        if self.longitudes:
            # Current UAV Position
            curr_lon = self.longitudes[-1]
            curr_lat = self.latitudes[-1]
            self.ax_map.scatter(
                [curr_lon],
                [curr_lat],
                color="#f38ba8",
                s=70,
                marker="^",
                label="UAV Current",
                zorder=6,
            )

            # Keep reasonable zoom bounds around drone
            margin = 0.003
            self.ax_map.set_xlim(curr_lon - margin, curr_lon + margin)
            self.ax_map.set_ylim(curr_lat - margin, curr_lat + margin)
            self.ax_map.ticklabel_format(useOffset=False, style="plain")

    def _render_charts(self) -> None:
        """Render altitude and battery progression."""
        self.ax_alt.clear()
        self.ax_bat.clear()
        self._style_axis(self.ax_alt, "ALTITUDE & BATTERY HISTORY", "Simulation Steps", "Altitude (m)")
        self.ax_bat.set_ylabel("Battery (%)", color="#a6e3a1", fontsize=9)
        self.ax_bat.tick_params(colors="#a6e3a1", labelsize=8)

        if len(self.time_indices) > 0:
            times = list(self.time_indices)
            alts = list(self.altitudes)
            bats = list(self.batteries)

            # Altitude (Sky Blue)
            self.ax_alt.plot(times, alts, color="#89b4fa", linewidth=1.5, label="Altitude (m)")
            self.ax_alt.set_ylim(0, max(50.0, max(alts) * 1.2))

            # Battery (Soft Green)
            self.ax_bat.plot(times, bats, color="#a6e3a1", linewidth=1.5, linestyle=":", label="Battery (%)")
            self.ax_bat.set_ylim(0, 105)

    def clear_data(self) -> None:
        """Clear flight data history."""
        self.latitudes.clear()
        self.longitudes.clear()
        self.altitudes.clear()
        self.batteries.clear()
        self.time_indices.clear()
        self._step_counter = 0
        self.ax_map.clear()
        self.ax_alt.clear()
        self.ax_bat.clear()
        self._style_axis(self.ax_map, "UAV GPS 2D FLIGHT PATH", "Longitude (°)", "Latitude (°)")
        self._style_axis(self.ax_alt, "ALTITUDE & BATTERY HISTORY", "Simulation Steps", "Altitude (m)")
        self.canvas.draw_idle()
