# src/tools/validation_tools.py
import os
from typing import Tuple, Optional


class ValidationManager:
    """Manager for validation operations and workflow status checking."""
    
    def __init__(self, workdir: str, potential_manager=None):
        """
        Initialize ValidationManager.
        
        Args:
            workdir: Working directory path
            potential_manager: Reference to potential manager (optional, can be set later)
        """
        self.workdir = workdir
        self.potential_manager = potential_manager
        self.validation_methods = {}
        
        # Register default validation methods
        self._register_default_methods()
    
    def _register_default_methods(self):
        """Register default validation methods."""
        self.register_validation_method('potential_file', self.validate_potential_file)
        self.register_validation_method('workflow_status', self.check_workflow_status)
        self.register_validation_method('download_success', self.verify_download_success)
    
    def set_potential_manager(self, potential_manager):
        """Set the potential manager reference after initialization."""
        self.potential_manager = potential_manager
    
    def register_validation_method(self, name: str, method):
        """Register a new validation method."""
        self.validation_methods[name] = method
    
    def validate(self, name: str, *args, **kwargs):
        """Run a registered validation method."""
        if name in self.validation_methods:
            return self.validation_methods[name](*args, **kwargs)
        else:
            raise ValueError(f"Validation method '{name}' is not registered.")

    def check_workflow_status(self) -> Tuple[bool, str]:
        """
        Check if workflow can continue based on potential file and structure file status.
        Auto-detects and validates existing potential files and LAMMPS structure files.
        Returns: (can_continue, status_message)
        """
        # Check if potential manager exists
        if not self.potential_manager:
            return False, "❌ Potential manager not initialized"
                
        # Initialize attributes if they don't exist
        if not hasattr(self.potential_manager, 'potential_validated'):
            self.potential_manager.potential_validated = False
        if not hasattr(self.potential_manager, 'last_potential_file'):
            self.potential_manager.last_potential_file = None
        if not hasattr(self.potential_manager, 'structure_validated'):
            self.potential_manager.structure_validated = False
        if not hasattr(self.potential_manager, 'last_structure_file'):
            self.potential_manager.last_structure_file = None
                
        # If not validated yet, try to auto-detect existing files
        if not self.potential_manager.potential_validated or not self.potential_manager.structure_validated:
            potential_extensions = ['.eam', '.eam.alloy', '.eam.fs', '.sw', '.meam']
            structure_extensions = ['.lmp']
            
            found_potential_files = []
            found_structure_files = []
                        
            if os.path.exists(self.workdir):
                for file in os.listdir(self.workdir):
                    # Check for potential files
                    if any(file.endswith(ext) for ext in potential_extensions):
                        found_potential_files.append(file)
                    # Check for structure files
                    elif any(file.endswith(ext) for ext in structure_extensions):
                        found_structure_files.append(file)
                        
                # Validate potential files if not already validated
                potential_status = ""
                if not self.potential_manager.potential_validated:
                    if found_potential_files:
                        # Try to validate first found potential file
                        first_potential = found_potential_files[0]
                        full_potential_path = os.path.join(self.workdir, first_potential)
                                        
                        # Auto-detect element from filename
                        element = self._auto_detect_element(first_potential)
                                        
                        # Validate the file
                        is_valid, validation_msg = self.validate_potential_file(first_potential, element)
                                        
                        if is_valid:
                            # Auto-update status
                            self.potential_manager.potential_validated = True
                            self.potential_manager.last_potential_file = full_potential_path
                            potential_status = f"✅ Potential: {first_potential} ({validation_msg})"
                        else:
                            potential_status = f"❌ Potential: {first_potential} validation failed: {validation_msg}"
                    else:
                        potential_status = "❌ No potential files found"
                else:
                    potential_status = "✅ Potential: already validated"
                
                # Validate structure files if not already validated
                structure_status = ""
                if not self.potential_manager.structure_validated:
                    if found_structure_files:
                        # Try to validate first found structure file
                        first_structure = found_structure_files[0]
                        full_structure_path = os.path.join(self.workdir, first_structure)
                        
                        # Basic validation for structure file (check if file exists and is readable)
                        try:
                            with open(full_structure_path, 'r') as f:
                                # Read first few lines to check if it's a valid LAMMPS structure
                                lines = f.readlines()[:10]
                                if lines:
                                    self.potential_manager.structure_validated = True
                                    self.potential_manager.last_structure_file = full_structure_path
                                    structure_status = f"✅ Structure: {first_structure} (valid LAMMPS format)"
                                else:
                                    structure_status = f"❌ Structure: {first_structure} appears to be empty"
                        except Exception as e:
                            structure_status = f"❌ Structure: {first_structure} read error: {str(e)}"
                    else:
                        structure_status = "❌ No structure files (.lmp) found"
                else:
                    structure_status = "✅ Structure: already validated"
                
                # Determine overall workflow status
                can_continue = (self.potential_manager.potential_validated and 
                            self.potential_manager.structure_validated)
                
                if can_continue:
                    return True, f"✅ Workflow ready: {potential_status} | {structure_status}"
                else:
                    return False, f"❌ WORKFLOW HALTED: {potential_status} | {structure_status}"
            else:
                return False, "❌ Working directory does not exist"
                
        # If already validated, verify both files still exist
        files_exist = True
        status_parts = []
        
        if self.potential_manager.last_potential_file:
            if os.path.exists(self.potential_manager.last_potential_file):
                status_parts.append("✅ Potential file available")
            else:
                # File was deleted, reset status
                self.potential_manager.potential_validated = False
                self.potential_manager.last_potential_file = None
                files_exist = False
                status_parts.append("❌ Potential file no longer exists")
        
        if self.potential_manager.last_structure_file:
            if os.path.exists(self.potential_manager.last_structure_file):
                status_parts.append("✅ Structure file available")
            else:
                # File was deleted, reset status
                self.potential_manager.structure_validated = False
                self.potential_manager.last_structure_file = None
                files_exist = False
                status_parts.append("❌ Structure file no longer exists")
                
        if files_exist:
            return True, "✅ Workflow can continue - " + " | ".join(status_parts)
        else:
            return False, "❌ WORKFLOW HALTED: " + " | ".join(status_parts)
    
    
    def _auto_detect_element(self, filename: str) -> str:
        """Auto-detect element from filename."""
        filename_lower = filename.lower()
        
        element_map = {
            'si': 'Si', 'ti': 'Ti', 'au': 'Au', 'cu': 'Cu', 'al': 'Al',
            'ni': 'Ni', 'fe': 'Fe', 'cr': 'Cr', 'co': 'Co', 'mn': 'Mn',
            'w': 'W', 'mo': 'Mo', 'nb': 'Nb', 'ta': 'Ta', 'zr': 'Zr',
            'ag': 'Ag', 'pt': 'Pt', 'pd': 'Pd', 'mg': 'Mg', 'ca': 'Ca'
        }
        
        for elem_key, elem_name in element_map.items():
            if elem_key in filename_lower:
                return elem_name
        
        return "Unknown"
    
    def validate_potential_file(self, filepath: str, element: str) -> Tuple[bool, str]:
        """
        Validate if a potential file is correct for the given element.
        Returns: (is_valid, error_message)
        """
        # Handle both absolute and relative paths
        if not os.path.isabs(filepath):
            full_path = os.path.join(self.workdir, filepath)
        else:
            full_path = filepath
        
        if not os.path.exists(full_path):
            return False, f"Potential file not found: {filepath} (checked: {full_path})"
        
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            
            # Reset file pointer and read lines
            with open(full_path, 'r') as f:
                lines = f.readlines()
            
            # ====== GENERAL VALIDATION FOR ALL FILES ======
            
            # Check for dummy/placeholder indicators (applies to ALL file types)
            dummy_indicators = [
                "dummy", "placeholder", "demonstration", "example",
                "# ... more data ...", "dummy values", "dummy header",
                "TODO", "FIXME", "replace with actual"
            ]
            
            content_lower = content.lower()
            for indicator in dummy_indicators:
                if indicator in content_lower:
                    return False, f"Dummy/placeholder content detected: '{indicator}' found in file"
            
            # Minimum file size check (applies to ALL file types)
            if len(lines) < 3:
                return False, "Potential file too short - missing basic content"
            
            # ====== FORMAT-SPECIFIC VALIDATION ======
            
            if filepath.endswith('.sw'):
                return self._validate_sw_potential(lines, filepath)
            elif any(filepath.endswith(ext) for ext in ['.eam', '.eam.alloy', '.eam.fs']):
                return self._validate_eam_potential(lines, filepath)
            elif filepath.endswith('.meam'):
                return self._validate_meam_potential(lines, filepath)
            else:
                return self._validate_general_potential(lines, filepath)
                
        except Exception as e:
            return False, f"Error reading potential file: {str(e)}"
    
    def _validate_sw_potential(self, lines: list, filepath: str) -> Tuple[bool, str]:
        """Validate Stillinger-Weber potential."""
        if len(lines) < 5:
            return False, "SW file too short - missing parameters"
        
        # Look for SW parameter structure
        sw_keywords = ['epsilon', 'sigma', 'a', 'lambda', 'gamma', 'costheta0', 'A', 'B', 'Si']
        found_keywords = 0
        param_lines = 0
        
        for line in lines:
            line_lower = line.lower()
            # Count parameter-like lines (numbers)
            if line.strip() and not line.strip().startswith('#'):
                try:
                    float(line.strip().split()[0])
                    param_lines += 1
                except (ValueError, IndexError):
                    pass
            
            # Count SW-related keywords
            for keyword in sw_keywords:
                if keyword.lower() in line_lower:
                    found_keywords += 1
                    break
        
        if param_lines < 1:
            return False, f"SW file missing parameters - only {param_lines} parameter lines found"
        
        return True, f"SW potential file validation passed - {len(lines)} lines, {param_lines} parameters"
    
    def _validate_eam_potential(self, lines: list, filepath: str) -> Tuple[bool, str]:
        """Validate EAM potential."""
        if filepath.endswith('.eam'):
            if len(lines) < 3:
                return False, "Missing header lines for funcfl format"
            
            try:
                header_parts = lines[1].strip().split()
                if len(header_parts) < 4:
                    return False, "Invalid funcfl header format"
                
                atomic_num = float(header_parts[0])
                mass = float(header_parts[1])
                lattice_const = float(header_parts[2])
                
                # Sanity checks for realistic values
                if atomic_num <= 0 or atomic_num > 118:
                    return False, f"Invalid atomic number: {atomic_num}"
                if mass <= 0 or mass > 300:
                    return False, f"Invalid atomic mass: {mass}"
                if lattice_const <= 0 or lattice_const > 10:
                    return False, f"Invalid lattice constant: {lattice_const}"
                        
            except (ValueError, IndexError):
                return False, "Invalid numeric values in header"
            
            # Validate tabulation parameters
            try:
                params = lines[2].strip().split()
                if len(params) < 5:
                    return False, "Missing tabulation parameters"
                
                nrho, drho, nr, dr, rcutoff = map(float, params[:5])
                if nrho <= 0 or nr <= 0 or rcutoff <= 0:
                    return False, "Invalid tabulation parameters"
                if nrho < 100 or nr < 100:
                    return False, f"Too few tabulation points: nrho={nrho}, nr={nr}"
                        
            except (ValueError, IndexError):
                return False, "Invalid tabulation parameters"
        
        # Check for sufficient numeric data (for all EAM types)
        numeric_lines = 0
        for line in lines:
            if line.strip() and not line.strip().startswith('#'):
                try:
                    float(line.strip().split()[0])
                    numeric_lines += 1
                except (ValueError, IndexError):
                    continue
        
        if numeric_lines < 200:
            return False, f"Insufficient numeric data lines: {numeric_lines} (EAM needs >200)"
        
        return True, f"EAM potential file validation passed - {numeric_lines} data lines found"
    
    def _validate_meam_potential(self, lines: list, filepath: str) -> Tuple[bool, str]:
        """Validate MEAM potential."""
        if len(lines) < 10:
            return False, "MEAM file too short"
        
        # Look for MEAM keywords
        meam_keywords = ['rc', 'delr', 'augt1', 'gsmooth_factor', 'beta']
        found_keywords = 0
        
        for line in lines[:20]:  # Check first 20 lines
            line_lower = line.lower()
            for keyword in meam_keywords:
                if keyword in line_lower:
                    found_keywords += 1
                    break
        
        if found_keywords < 2:
            return False, "MEAM file missing expected parameters"
        
        return True, f"MEAM potential file validation passed - {len(lines)} lines"
    
    def _validate_general_potential(self, lines: list, filepath: str) -> Tuple[bool, str]:
        """Validate general potential format."""
        if len(lines) < 10:
            return False, "Unknown format file too short"
        
        # Check for reasonable amount of data
        data_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
        if len(data_lines) < 10:
            return False, "Insufficient data content"
        
        return True, f"General potential file validation passed - {len(lines)} lines"
    
    @staticmethod
    def verify_download_success(filepath: str, expected_element: str) -> str:
        """Verify that a file was actually downloaded and contains real data."""
        if not os.path.exists(filepath):
            return f"❌ DOWNLOAD FAILED: File does not exist: {filepath}"
        
        file_size = os.path.getsize(filepath)
        if file_size < 1000:  # Real EAM files are typically several KB
            return f"❌ DOWNLOAD FAILED: File too small ({file_size} bytes) - likely empty or dummy content"
        
        # Read content and check for dummy indicators
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            dummy_keywords = [
                "dummy", "placeholder", "demonstration", "example",
                "# ... more data ...", "dummy values", "dummy header",
                "TODO", "FIXME", "replace with actual", "obtained from", "please verify"
            ]
            
            content_lower = content.lower()
            for keyword in dummy_keywords:
                if keyword in content_lower:
                    return f"❌ DUMMY CONTENT DETECTED: Found '{keyword}' - this is not a real potential file"
            
            # Check for realistic data density
            lines = content.split('\n')
            data_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
            
            if len(data_lines) < 100:
                return f"❌ INSUFFICIENT DATA: Only {len(data_lines)} data lines (need >100 for real potential)"
            
            return f"✅ DOWNLOAD VERIFIED: Real potential file detected ({file_size} bytes, {len(data_lines)} data lines)"
            
        except Exception as e:
            return f"❌ VERIFICATION ERROR: Could not read file: {str(e)}"