"""
Realtime plotting module for OpenFOAM simulations.
Parses OpenFOAM field files and extracts data for visualization.
"""

import os
import re
import numpy as np
from pathlib import Path


class OpenFOAMFieldParser:
    """Parse OpenFOAM field files and extract data."""

    def __init__(self, case_dir):
        self.case_dir = Path(case_dir)

    def get_time_directories(self):
        """Get all time directories sorted numerically."""
        time_dirs = []
        for item in self.case_dir.iterdir():
            if item.is_dir():
                try:
                    # Check if directory name is a number
                    float(item.name)
                    time_dirs.append(item.name)
                except ValueError:
                    continue
        return sorted(time_dirs, key=float)

    def parse_scalar_field(self, field_path):
        """Parse a scalar field file and return average value."""
        try:
            with open(field_path, "r") as f:
                content = f.read()

            # Find internalField section
            internal_match = re.search(
                r"internalField\s+(?:uniform\s+)?([^;]+);", content, re.DOTALL
            )
            if not internal_match:
                return None

            field_data = internal_match.group(1).strip()

            # Handle uniform field
            if "uniform" in content:
                try:
                    return float(field_data)
                except ValueError:
                    return None

            # Handle nonuniform field
            if "nonuniform" in content:
                # Extract numbers from the list
                numbers = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", field_data)
                values = [float(n) for n in numbers]
                return np.mean(values) if values else None

            return None

        except Exception as e:
            print(f"Error parsing scalar field {field_path}: {e}")
            return None

    def parse_vector_field(self, field_path):
        """Parse a vector field file and return average components."""
        try:
            with open(field_path, "r") as f:
                content = f.read()

            # Find internalField section
            internal_match = re.search(
                r"internalField\s+(?:uniform\s+)?([^;]+);", content, re.DOTALL
            )
            if not internal_match:
                return None, None, None

            field_data = internal_match.group(1).strip()

            # Handle uniform field
            if "uniform" in content:
                # Extract vector components
                vec_match = re.search(
                    r"\(\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*\)",
                    field_data,
                )
                if vec_match:
                    return (
                        float(vec_match.group(1)),
                        float(vec_match.group(2)),
                        float(vec_match.group(3)),
                    )
                return None, None, None

            # Handle nonuniform field
            if "nonuniform" in content:
                # Extract all vectors
                vectors = re.findall(
                    r"\(\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*\)",
                    field_data,
                )
                if vectors:
                    x_vals = [float(v[0]) for v in vectors]
                    y_vals = [float(v[1]) for v in vectors]
                    z_vals = [float(v[2]) for v in vectors]
                    return np.mean(x_vals), np.mean(y_vals), np.mean(z_vals)

            return None, None, None

        except Exception as e:
            print(f"Error parsing vector field {field_path}: {e}")
            return None, None, None

    def get_latest_time_data(self):
        """Get data from the latest time directory."""
        time_dirs = self.get_time_directories()
        if not time_dirs:
            return None

        latest_time = time_dirs[-1]
        time_path = self.case_dir / latest_time

        data = {"time": float(latest_time)}

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
            if ux is not None:
                data["Ux"] = ux
                data["Uy"] = uy
                data["Uz"] = uz
                data["U_mag"] = np.sqrt(ux**2 + uy**2 + uz**2)

        return data

    def get_all_time_series_data(self, max_points=100):
        """Get time series data for all available fields."""
        time_dirs = self.get_time_directories()
        if not time_dirs:
            return {}

        # Limit to last max_points time steps
        time_dirs = time_dirs[-max_points:]

        # Initialize data structure
        data = {"time": []}

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
                    data[field].append(value if value is not None else 0)

            # Parse velocity field
            u_field_path = time_path / "U"
            if u_field_path.exists():
                ux, uy, uz = self.parse_vector_field(u_field_path)
                if ux is not None:
                    if "Ux" not in data:
                        data["Ux"] = []
                        data["Uy"] = []
                        data["Uz"] = []
                        data["U_mag"] = []
                    data["Ux"].append(ux)
                    data["Uy"].append(uy)
                    data["Uz"].append(uz)
                    data["U_mag"].append(np.sqrt(ux**2 + uy**2 + uz**2))

        return data

    def calculate_pressure_coefficient(
        self, p_field, p_inf=101325, rho=1.225, u_inf=1.0
    ):
        """Calculate pressure coefficient Cp = (p - p_inf) / (0.5 * rho * u_inf^2)."""
        if p_field is None:
            return None
        q_inf = 0.5 * rho * u_inf**2
        return (p_field - p_inf) / q_inf if q_inf != 0 else 0

    def get_residuals_from_log(self, log_file="log.foamRun"):
        """Parse residuals from OpenFOAM log file."""
        log_path = self.case_dir / log_file
        if not log_path.exists():
            return {}

        residuals = {
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
            with open(log_path, "r") as f:
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
            print(f"Error parsing log file: {e}")

        return residuals


def get_available_fields(case_dir):
    """Get list of available fields in the latest time directory."""
    parser = OpenFOAMFieldParser(case_dir)
    time_dirs = parser.get_time_directories()
    if not time_dirs:
        return []

    latest_time = time_dirs[-1]
    time_path = Path(case_dir) / latest_time

    fields = []
    for item in time_path.iterdir():
        if item.is_file() and not item.name.startswith("."):
            fields.append(item.name)

    return sorted(fields)
