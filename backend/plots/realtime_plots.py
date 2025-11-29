"""
Realtime plotting module for OpenFOAM simulations.
Parses OpenFOAM field files and extracts data for visualization.
"""

import re
import numpy as np
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Union, Any

# Configure logger
logger = logging.getLogger("FOAMFlask")


class OpenFOAMFieldParser:
    """Parse OpenFOAM field files and extract data."""

    def __init__(self, case_dir: Union[str, Path]) -> None:
        self.case_dir = Path(case_dir)

    def get_time_directories(self) -> List[str]:
        """Get all time directories sorted numerically."""
        time_dirs = []
        try:
            for item in self.case_dir.iterdir():
                if item.is_dir():
                    try:
                        # Check if directory name is a number
                        float(item.name)
                        time_dirs.append(item.name)
                    except ValueError:
                        continue
        except OSError as e:
            logger.error(f"Error listing directories in {self.case_dir}: {e}")
            return []

        return sorted(time_dirs, key=float)

    def parse_scalar_field(self, field_path: Path) -> Optional[float]:
        """Parse a scalar field file and return average value."""
        try:
            # Use Path.read_text for simpler reading
            content = field_path.read_text(encoding="utf-8")

            # Handle nonuniform field first (since 'nonuniform' contains 'uniform')
            if "nonuniform" in content:
                # Match multi-line nonuniform lists between parentheses
                match = re.search(
                    r"internalField\s+nonuniform\s+[^\n]*\(\s*([\s\S]*?)\s*\);",
                    content,
                    re.DOTALL,
                )
                if not match:
                    return None

                field_data = match.group(1)
                # Extract all numbers inside the parentheses
                numbers = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", field_data)
                values = [float(n) for n in numbers]
                return float(np.mean(values)) if values else None

            # Handle uniform field
            if re.search(r"internalField\s+uniform\b", content):
                match = re.search(r"internalField\s+uniform\s+([^;]+);", content)
                if match:
                    return float(match.group(1).strip())
                return None

            return None

        except Exception as e:
            logger.error(f"Error parsing scalar field {field_path}: {e}")
            return None

    def parse_vector_field(self, field_path: Path) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Parse a vector field file and return average components."""
        try:
            content = field_path.read_text(encoding="utf-8")

            # Handle nonuniform first
            if "nonuniform" in content:
                match = re.search(
                    r"internalField\s+nonuniform\s+[^\n]*\(\s*([\s\S]*?)\s*\);",
                    content,
                    re.DOTALL,
                )
                if not match:
                    return None, None, None

                field_data = match.group(1)
                vectors = re.findall(
                    r"\(\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+"
                    r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+"
                    r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*\)",
                    field_data,
                )
                if not vectors:
                    return None, None, None

                x_vals = [float(v[0]) for v in vectors]
                y_vals = [float(v[1]) for v in vectors]
                z_vals = [float(v[2]) for v in vectors]
                return float(np.mean(x_vals)), float(np.mean(y_vals)), float(np.mean(z_vals))

            # Handle uniform field
            if re.search(r"internalField\s+uniform\b", content):
                match = re.search(
                    r"internalField\s+uniform\s+(\([^;]+\));",
                    content,
                    re.DOTALL,
                )
                if not match:
                    return None, None, None

                vec_str = match.group(1)
                vec_match = re.search(
                    r"\(\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+"
                    r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+"
                    r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*\)",
                    vec_str,
                )
                if vec_match:
                    return (
                        float(vec_match.group(1)),
                        float(vec_match.group(2)),
                        float(vec_match.group(3)),
                    )
                return None, None, None

            return None, None, None

        except Exception as e:
            logger.error(f"Error parsing vector field {field_path}: {e}")
            return None, None, None


    def get_latest_time_data(self) -> Optional[Dict[str, Any]]:
        """Get data from the latest time directory."""
        time_dirs = self.get_time_directories()
        if not time_dirs:
            return None

        latest_time = time_dirs[-1]
        time_path = self.case_dir / latest_time

        data: Dict[str, Any] = {"time": float(latest_time)}

        # Parse common scalar fields
        scalar_fields = [
            "p",
            "nut",
            "nuTilda",
            "k",
            "epsilon",
            "omega",
            "T",
            "alpha.water",
        ]
        for field in scalar_fields:
            field_path = time_path / field
            if field_path.exists():
                value = self.parse_scalar_field(field_path)
                if value is not None:
                    data[field] = value

        # Parse velocity field
        u_field_path = time_path / "U"
        if u_field_path.exists():
            ux, uy, uz = self.parse_vector_field(u_field_path)
            if ux is not None and uy is not None and uz is not None:
                data["Ux"] = ux
                data["Uy"] = uy
                data["Uz"] = uz
                data["U_mag"] = float(np.sqrt(ux**2 + uy**2 + uz**2))

        return data

    def get_all_time_series_data(self, max_points: int = 100) -> Dict[str, List[float]]:
        """Get time series data for all available fields."""
        time_dirs = self.get_time_directories()
        if not time_dirs:
            return {}

        # Limit to last max_points time steps
        time_dirs = time_dirs[-max_points:]

        # Initialize data structure
        data: Dict[str, List[float]] = {"time": []}

        for time_dir in time_dirs:
            time_path = self.case_dir / time_dir
            time_val = float(time_dir)
            data["time"].append(time_val)

            # Parse scalar fields
            scalar_fields = [
                "p",
                "nut",
                "nuTilda",
                "k",
                "epsilon",
                "omega",
                "T",
                "alpha.water",
            ]
            for field in scalar_fields:
                field_path = time_path / field
                if field_path.exists():
                    if field not in data:
                        data[field] = []
                    value = self.parse_scalar_field(field_path)
                    data[field].append(value if value is not None else 0.0)

            # Parse velocity field
            u_field_path = time_path / "U"
            if u_field_path.exists():
                ux, uy, uz = self.parse_vector_field(u_field_path)
                if ux is not None and uy is not None and uz is not None:
                    if "Ux" not in data:
                        data["Ux"] = []
                        data["Uy"] = []
                        data["Uz"] = []
                        data["U_mag"] = []
                    data["Ux"].append(ux)
                    data["Uy"].append(uy)
                    data["Uz"].append(uz)
                    data["U_mag"].append(float(np.sqrt(ux**2 + uy**2 + uz**2)))

        return data

    def calculate_pressure_coefficient(
        self, p_field: Optional[float], p_inf: float = 101325, rho: float = 1.225, u_inf: float = 1.0
    ) -> Optional[float]:
        """Calculate pressure coefficient Cp = (p - p_inf) / (0.5 * rho * u_inf^2)."""
        if p_field is None:
            return None
        q_inf = 0.5 * rho * u_inf**2
        return (p_field - p_inf) / q_inf if q_inf != 0 else 0.0

    def get_residuals_from_log(self, log_file: str = "log.foamRun") -> Dict[str, List[float]]:
        """Parse residuals from OpenFOAM log file."""
        log_path = self.case_dir / log_file
        if not log_path.exists():
            return {}

        residuals: Dict[str, List[float]] = {
            "time": [],
            "Ux": [],
            "Uy": [],
            "Uz": [],
            "p": [],
            "k": [],
            "epsilon": [],
            "omega": [],
        }

        try:
            # Using standard open because we are iterating line by line
            with log_path.open("r", encoding="utf-8") as f:
                for line in f:
                    # Parse time
                    time_match = re.search(
                        r"Time\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", line
                    )
                    if time_match:
                        current_time = float(time_match.group(1))
                        residuals["time"].append(current_time)

                    # Parse residuals
                    for field in ["Ux", "Uy", "Uz", "p", "k", "epsilon", "omega"]:
                        residual_match = re.search(
                            rf"{field}.*Initial residual\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)",
                            line,
                        )
                        if residual_match and residuals["time"]:
                            residuals[field].append(float(residual_match.group(1)))

        except Exception as e:
            logger.error(f"Error parsing log file: {e}")

        return residuals


def get_available_fields(case_dir: str) -> List[str]:
    """Get list of available fields in the latest time directory."""
    parser = OpenFOAMFieldParser(case_dir)
    time_dirs = parser.get_time_directories()
    if not time_dirs:
        return []

    latest_time = time_dirs[-1]
    time_path = Path(case_dir) / latest_time

    fields = []
    try:
        for item in time_path.iterdir():
            if item.is_file() and not item.name.startswith("."):
                fields.append(item.name)
    except OSError as e:
        logger.error(f"Error listing fields in {time_path}: {e}")
        return []

    return sorted(fields)
