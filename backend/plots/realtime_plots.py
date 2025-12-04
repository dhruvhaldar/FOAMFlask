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

    def _resolve_variable(self, content: str, var_name: str) -> Optional[str]:
        """
        Attempt to resolve a variable definition within the file content.
        Looks for patterns like 'varName value;'
        """
        # Remove the leading $ if present
        clean_var = var_name.lstrip('$')
        
        # specific fix for the U file provided which uses #calc
        # We can't easily parse #calc in Python, so we might need to look for simple definitions
        # or just return None to trigger the fallback to 0.0
        
        # Regex to find "variable value;"
        # We look for the variable name at the start of a line or after whitespace
        pattern = re.compile(rf"(?:^|\s){re.escape(clean_var)}\s+([^;]+);")
        match = pattern.search(content)
        
        if match:
            value_str = match.group(1).strip()
            
            # If the value is another variable, recurse (simple depth limit could be added)
            if value_str.startswith('$'):
                return self._resolve_variable(content, value_str)
            
            # If it's a #calc, we cannot evaluate it safely in Python. 
            # We return None so the parser falls back to 0.0
            if "#calc" in value_str:
                logger.warning(f"Skipping #calc macro for variable {clean_var}")
                return None
                
            return value_str
            
        return None

    def parse_scalar_field(self, field_path: Path) -> Optional[float]:
        """Parse a scalar field file and return average value."""
        try:
            content = field_path.read_text(encoding="utf-8")

            # Handle nonuniform field first
            if "nonuniform" in content:
                match = re.search(
                    r"internalField\s+nonuniform\s+[^\n]*\(\s*([\s\S]*?)\s*\);",
                    content,
                    re.DOTALL,
                )
                if not match:
                    return None

                field_data = match.group(1)
                numbers = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", field_data)
                values = [float(n) for n in numbers]
                return float(np.mean(values)) if values else None

            # Handle uniform field
            if re.search(r"internalField\s+uniform\b", content):
                # Check for variable substitution (e.g. uniform $pOut)
                var_match = re.search(r"internalField\s+uniform\s+(\$[a-zA-Z0-9_]+);", content)
                if var_match:
                    var_name = var_match.group(1)
                    resolved_value = self._resolve_variable(content, var_name)
                    if resolved_value:
                        try:
                            return float(resolved_value)
                        except ValueError:
                            pass
                
                # Standard number match
                match = re.search(r"internalField\s+uniform\s+([^;]+);", content)
                if match:
                    try:
                        return float(match.group(1).strip())
                    except ValueError:
                        return None
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
                # Check for variable substitution (e.g. uniform $Uinlet)
                var_match = re.search(r"internalField\s+uniform\s+(\$[a-zA-Z0-9_]+);", content)
                if var_match:
                    # If we find a variable, try to resolve it, but for vectors like $Uinlet
                    # which might be #calc, we often can't parse the value. 
                    # Returning 0,0,0 is better than None to keep array lengths consistent.
                    return 0.0, 0.0, 0.0

                # Standard vector match (x y z)
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
            "p", "nut", "nuTilda", "k", "epsilon", "omega", "T", "alpha.water",
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
            # Use 0.0 if None to ensure data is returned
            data["Ux"] = ux if ux is not None else 0.0
            data["Uy"] = uy if uy is not None else 0.0
            data["Uz"] = uz if uz is not None else 0.0
            if ux is not None and uy is not None and uz is not None:
                data["U_mag"] = float(np.sqrt(ux**2 + uy**2 + uz**2))
            else:
                data["U_mag"] = 0.0

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
            
            # Always append time
            data["time"].append(time_val)

            # Parse scalar fields
            scalar_fields = [
                "p", "nut", "nuTilda", "k", "epsilon", "omega", "T", "alpha.water",
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
                # Initialize arrays if they don't exist
                if "Ux" not in data:
                    data["Ux"] = []
                    data["Uy"] = []
                    data["Uz"] = []
                    data["U_mag"] = []
                
                ux, uy, uz = self.parse_vector_field(u_field_path)
                
                # CRITICAL FIX: Always append something, even if parsing failed (None)
                # This keeps the array lengths aligned with data["time"]
                val_x = ux if ux is not None else 0.0
                val_y = uy if uy is not None else 0.0
                val_z = uz if uz is not None else 0.0
                
                data["Ux"].append(val_x)
                data["Uy"].append(val_y)
                data["Uz"].append(val_z)
                data["U_mag"].append(float(np.sqrt(val_x**2 + val_y**2 + val_z**2)))
            else:
                # If U file doesn't exist but we already have U data from other steps,
                # we must append 0s to keep alignment.
                if "Ux" in data:
                    data["Ux"].append(0.0)
                    data["Uy"].append(0.0)
                    data["Uz"].append(0.0)
                    data["U_mag"].append(0.0)

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
            with log_path.open("r", encoding="utf-8") as f:
                for line in f:
                    time_match = re.search(
                        r"Time\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", line
                    )
                    if time_match:
                        current_time = float(time_match.group(1))
                        residuals["time"].append(current_time)

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
