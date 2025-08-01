import os
import subprocess
import numpy as np
import shutil
import glob
from pathlib import Path
from typing import Optional, Dict, List
from ase.io import read, write
from phonopy import Phonopy
from phonopy.interface.vasp import read_vasp, write_vasp


class PhonopyManager:
    def __init__(self, workdir: str):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        os.chdir(self.workdir)
    
    # Step 1: Convert the structure file from atomsk to POSCAR format
    def create_poscar_from_lmp(self, lmp_filename: str = "au_structure.lmp") -> str:
        lmp_path = self.workdir / lmp_filename
        poscar_path = self.workdir / "POSCAR"
        
        if not lmp_path.exists():
            return f"lmp structure file not found: {lmp_path}"
        
        try:
            atoms = read(str(lmp_path), format='lammps-data')
            write(str(poscar_path), atoms, format='vasp')
            return f"POSCAR created from {lmp_filename} in {self.workdir}"
        except Exception as e:
            return f"Failed to convert lmp to POSCAR: {str(e)}"

    # Step 2: Create displacement YAML file using phonopy and the existing POSCAR
    def create_displacement_yaml(self, dim: str = "3 3 3") -> str:
        """Create displaced structures using phonopy."""
        try:
            result = subprocess.run(
                f"phonopy --dim=\"{dim}\" -d",
                shell=True, cwd=self.workdir, capture_output=True, text=True
            )
            if result.returncode != 0:
                return f"Phonopy error:\n{result.stderr}"
            return f"Displacement structures generated in {self.workdir} and saved as 'disp-*' directories"
        except Exception as e:
            return f"Exception during displacement generation: {str(e)}"

    # Step 3: Create displaced structures using phonopy and saves as POSCARs
    def create_displacement_files(self) -> str:
        """Create displaced structures using phonopy."""
        try:
            result = subprocess.run(
                f"phonopy -d --nosym --cell=phonopy_disp.yaml",
                shell=True, cwd=self.workdir, capture_output=True, text=True
            )
            if result.returncode != 0:
                return f"Phonopy error:\n{result.stderr}"
            return f"Displacement structures generated in {self.workdir}"
        except Exception as e:
            return f"Exception during displacement generation: {str(e)}"

    def _detect_potential_type(self, potential_file: str) -> Dict[str, str]:
        """Detect potential type and return appropriate LAMMPS commands."""
        potential_path = Path(potential_file)
        filename = potential_path.name.lower()
        
        # Read first few lines to analyze content
        try:
            with open(potential_file, 'r') as f:
                content = f.read(500).lower()  # Read first 500 chars
        except:
            content = ""
        
        potential_config = {}
        
        # EAM potentials
        if any(ext in filename for ext in ['.eam', '.alloy', '.fs']):
            if '.fs' in filename or 'setfl' in content:
                potential_config['pair_style'] = 'eam/fs'
            elif '.alloy' in filename or 'funcfl' in content:
                potential_config['pair_style'] = 'eam/alloy'
            else:
                potential_config['pair_style'] = 'eam'
        
        # MEAM potentials
        elif any(ext in filename for ext in ['.meam', '.library']):
            potential_config['pair_style'] = 'meam'
            potential_config['meam_library'] = True
        
        # Tersoff potentials
        elif 'tersoff' in filename or any(ext in filename for ext in ['.tersoff']):
            potential_config['pair_style'] = 'tersoff'
        
        # Stillinger-Weber
        elif 'sw' in filename or 'stillinger' in filename:
            potential_config['pair_style'] = 'sw'
        
        # ReaxFF
        elif 'reax' in filename or any(ext in filename for ext in ['.ff']):
            potential_config['pair_style'] = 'reax/c'
        
        # AIREBO/REBO
        elif any(term in filename for term in ['airebo', 'rebo']):
            potential_config['pair_style'] = 'airebo'
        
        # Default to LJ or user-defined
        else:
            potential_config['pair_style'] = 'unknown'
        
        return potential_config

    def _get_elements_from_structure(self, atoms) -> List[str]:
        """Extract unique elements from the structure."""
        return list(set(atoms.get_chemical_symbols()))

    def _generate_pair_coeff_line(self, potential_config: Dict[str, str], 
                                 elements: List[str], potential_filename: str) -> str:
        """Generate appropriate pair_coeff line based on potential type."""
        pair_style = potential_config['pair_style']
        
        if pair_style in ['eam/alloy', 'eam/fs']:
            if len(elements) == 1:
                return f"pair_coeff * * {potential_filename} {elements[0]}"
            else:
                elements_str = ' '.join(elements)
                return f"pair_coeff * * {potential_filename} {elements_str}"
            
        if pair_style in ['eam']:
                return f"pair_coeff * * {potential_filename}"

        
        elif pair_style == 'meam':
            if potential_config.get('meam_library'):
                # MEAM typically requires library file
                return f"pair_coeff * * library.meam {' '.join(elements)} {potential_filename} {' '.join(elements)}"
            else:
                return f"pair_coeff * * {potential_filename} {' '.join(elements)}"
        
        elif pair_style in ['tersoff', 'sw']:
            return f"pair_coeff * * {potential_filename} {' '.join(elements)}"
        
        elif pair_style == 'reax/c':
            return f"pair_coeff * * {potential_filename}"
        
        elif pair_style == 'airebo':
            return f"pair_coeff * * {potential_filename} {' '.join(elements)}"
        
        else:
            # Generic fallback
            return f"pair_coeff * * {potential_filename} {' '.join(elements)}"

    def _generate_lammps_input(self, potential_config: Dict[str, str], 
                              elements: List[str], potential_filename: str) -> str:
        """Generate LAMMPS input file content."""
        pair_style = potential_config['pair_style']
        pair_coeff = self._generate_pair_coeff_line(potential_config, elements, potential_filename)
        
        # Base input template
        input_content = f"""# LAMMPS input for phonon calculation
units metal
atom_style atomic
boundary p p p
read_data structure.lmp

# Potential settings
pair_style {pair_style}
{pair_coeff}

# Neighbor settings
neighbor 2.0 bin
neigh_modify delay 0 every 1 check yes

# Force calculation
compute forces all property/atom fx fy fz
dump forces all custom 1 forces.dump id type x y z fx fy fz

# Run single point calculation
run 0

# Output final forces
write_dump all custom forces.dat id type x y z fx fy fz modify sort id
"""

        # Add special settings for certain potential types
        if pair_style == 'reax/c':
            input_content = input_content.replace(
                "# Potential settings",
                """# Potential settings
fix qeq all qeq/reax 1 0.0 10.0 1.0e-6 reax/c"""
            )
        
        elif pair_style == 'airebo':
            input_content = input_content.replace(
                "# Neighbor settings",
                """# Special settings for AIREBO
mass * 12.01  # Carbon mass - adjust as needed

# Neighbor settings"""
            )

        return input_content

    def create_lammps_input_for_displacements(self, potential_file: str) -> str:
        """
        Convert each displaced POSCAR to LAMMPS format and prepare input files.
        Automatically detects potential type and generates appropriate input.
        """
        if not os.path.exists(potential_file):
            return f"Potential file not found: {potential_file}"
        
        # Get potential configuration
        potential_config = self._detect_potential_type(potential_file)
        potential_filename = Path(potential_file).name
        
        # Find displaced POSCAR files
        poscars = sorted(glob.glob("POSCAR-*"))
        if not poscars:
            return "No displaced POSCAR files found (POSCAR-*)"
        
        # Read one structure to get elements
        try:
            sample_atoms = read(poscars[0], format='vasp')
            elements = self._get_elements_from_structure(sample_atoms)
        except Exception as e:
            return f"Failed to read sample structure: {str(e)}"
        
        results = []
        
        for i, poscar in enumerate(poscars):
            try:
                # Read and convert structure
                atoms = read(poscar, format='vasp')
                
                # Create displacement directory
                disp_dir = f"disp-{i+1:03d}"
                os.makedirs(disp_dir, exist_ok=True)
                
                # Write LAMMPS structure file
                write(f"{disp_dir}/structure.lmp", atoms, format='lammps-data')
                
                # Copy potential file to displacement directory
                shutil.copy2(potential_file, f"{disp_dir}/{potential_filename}")
                
                # Generate and write LAMMPS input file
                input_content = self._generate_lammps_input(
                    potential_config, elements, potential_filename
                )
                
                with open(f"{disp_dir}/in.lmp", "w") as f:
                    f.write(input_content)
                
                results.append(f"Created {disp_dir}")
                
            except Exception as e:
                results.append(f"Failed to process {poscar}: {str(e)}")
        
        summary = f"""
LAMMPS displacement setup completed:
- Detected potential type: {potential_config['pair_style']}
- Elements found: {', '.join(elements)}
- Processed {len(poscars)} displacement structures
- Results: {len([r for r in results if 'Created' in r])} successful, {len([r for r in results if 'Failed' in r])} failed

Potential file '{potential_filename}' copied to each displacement directory.
"""
        
        if any('Failed' in r for r in results):
            summary += "\nErrors:\n" + "\n".join([r for r in results if 'Failed' in r])
        
        return summary

    def collect_forces_from_displacements(self) -> str:
        import glob
        import subprocess

        try:

            files = glob.glob("disp-*/forces.dat")
            cmd = ["phonopy", "--lammps", "-f"] + files
            result = subprocess.run(cmd, cwd=self.workdir, capture_output=True, text=True)
            if result.returncode != 0:
                return f"Phonopy error:\n{result.stderr}"
            return f"FORCE_SETS generated in {self.workdir}"
        
        except Exception as e:            
            return f"Exception during FORCE_SETS generation: {str(e)}"


    # Step 4: Generate band.conf and plot phonon dispersion
    def generate_band_conf_and_plot(self, npoints: int = 101) -> str:
            """
            Generate band.conf file and create phonon dispersion plot using phonopy.
            Automatically determines k-point paths based on crystal structure.
            """
            if not os.path.exists("FORCE_SETS"):
                return "FORCE_SETS file not found. Run collect_forces_from_displacements first."
            
            if not os.path.exists("POSCAR"):
                return "POSCAR file not found."
            
            try:
                # Read structure to determine crystal system and elements
                unitcell = read_vasp("POSCAR")
                
                # Get unique elements
                elements = list(set(unitcell.get_chemical_symbols()))
                elements.sort()
                
                # Determine supercell matrix
                supercell_matrix = [3, 3, 3]  # Default
                if os.path.exists("phonopy_disp.yaml"):
                    try:
                        import yaml
                        with open("phonopy_disp.yaml", 'r') as f:
                            disp_data = yaml.safe_load(f)
                        
                        raw_matrix = disp_data.get('supercell_matrix', [3, 3, 3])
                        print(f"Raw supercell_matrix from YAML: {raw_matrix}")
                        
                        # Handle different formats
                        if isinstance(raw_matrix, list):
                            if len(raw_matrix) == 3 and all(isinstance(x, (int, float)) for x in raw_matrix):
                                # Simple list: [3, 3, 3]
                                supercell_matrix = [int(x) for x in raw_matrix]
                            elif len(raw_matrix) == 3 and all(isinstance(x, list) for x in raw_matrix):
                                # Nested list: [[3,0,0],[0,3,0],[0,0,3]] - extract diagonal
                                supercell_matrix = [int(raw_matrix[i][i]) for i in range(3)]
                            else:
                                # Try to flatten and take first 3
                                flat = []
                                def flatten(lst):
                                    for item in lst:
                                        if isinstance(item, list):
                                            flatten(item)
                                        else:
                                            flat.append(item)
                                flatten(raw_matrix)
                                supercell_matrix = [int(x) for x in flat[:3] if isinstance(x, (int, float))]
                                if len(supercell_matrix) != 3:
                                    supercell_matrix = [3, 3, 3]
                        
                    except Exception as e:
                        print(f"Warning: Could not read supercell matrix from YAML: {e}")
                        supercell_matrix = [3, 3, 3]

                print(f"Using supercell matrix: {supercell_matrix}")

                # Analyze crystal structure to determine appropriate k-point path
                cell = unitcell.get_cell()

                # Get lattice parameters (a, b, c, alpha, beta, gamma)
                try:
                    # Try modern ASE method
                    lattice_params = unitcell.cell.cellpar()
                except AttributeError:
                    # Fallback: calculate manually from cell matrix
                    import numpy as np
                    
                    a = np.linalg.norm(cell[0])
                    b = np.linalg.norm(cell[1]) 
                    c = np.linalg.norm(cell[2])
                    
                    # Calculate angles
                    alpha = np.arccos(np.dot(cell[1], cell[2]) / (b * c)) * 180 / np.pi
                    beta = np.arccos(np.dot(cell[0], cell[2]) / (a * c)) * 180 / np.pi
                    gamma = np.arccos(np.dot(cell[0], cell[1]) / (a * b)) * 180 / np.pi
                    
                    lattice_params = [a, b, c, alpha, beta, gamma]

                print(f"Lattice parameters: a={lattice_params[0]:.3f}, b={lattice_params[1]:.3f}, c={lattice_params[2]:.3f}")
                print(f"Angles: α={lattice_params[3]:.1f}°, β={lattice_params[4]:.1f}°, γ={lattice_params[5]:.1f}°")
                
                crystal_system = self._determine_crystal_system(lattice_params)
                kpoint_path, path_labels = self._get_kpoint_path(crystal_system, lattice_params)
                
                # Create band.conf file
                band_conf_content = f"""# Phonopy band structure configuration
                # Auto-generated for {crystal_system} crystal system

                ATOM_NAME = {' '.join(elements)}
                DIM = {supercell_matrix[0]} {supercell_matrix[1]} {supercell_matrix[2]}
                BAND_POINTS = {npoints}

                # High-symmetry k-point path for {crystal_system} system
                BAND = {kpoint_path}
                BAND_LABELS = {' '.join(path_labels)}

                # Optional: Force constants file
                FORCE_SETS = READ

                # Output settings
                BAND_FORMAT = gnuplot
                """
                
                # Write band.conf file
                with open("band.conf", "w") as f:
                    f.write(band_conf_content)
                
                # Run phonopy to generate band structure
                result = subprocess.run(
                    "phonopy -p -s band.conf",
                    shell=True, cwd=self.workdir, capture_output=True, text=True
                )

                print(f"Phonopy stdout: {result.stdout}")
                print(f"Phonopy stderr: {result.stderr}")
                print(f"Return code: {result.returncode}")

                if result.returncode != 0:
                    # Also print the band.conf content for debugging
                    with open("band.conf", "r") as f:
                        print("Generated band.conf content:")
                        print(f.read())
                    return f"Phonopy band calculation failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
                
                # if result.returncode != 0:
                #     return f"Phonopy band calculation failed:\n{result.stderr}"
                
                # Run phonopy plotting
                plot_result = subprocess.run(
                    "phonopy-bandplot --gnuplot band.dat",
                    shell=True, cwd=self.workdir, capture_output=True, text=True
                )
                
                summary = f"""✅ Phonon band structure generated successfully:

    Crystal Analysis:
    - Crystal system: {crystal_system}
    - Elements: {', '.join(elements)}
    - Supercell matrix: {supercell_matrix}
    - K-point path: {' → '.join(path_labels)}

    Generated files:
    - band.conf (configuration file)
    - band.dat (band structure data)
    - band.pdf (dispersion plot)
    - band.yaml (detailed data)

    K-point path details:
    {kpoint_path}

    Plot generated using: phonopy -p -s band.conf"""
                
                if plot_result.returncode == 0:
                    summary += "\n- phonopy-bandplot executed successfully"
                else:
                    summary += f"\nNote: phonopy-bandplot failed, but band.pdf should still be available"
                
                return summary
                
            except Exception as e:
                return f"Failed to generate band structure: {str(e)}"

    def _determine_crystal_system(self, lattice_params) -> str:
        """Determine crystal system from lattice parameters."""
        a, b, c, alpha, beta, gamma = lattice_params
        
        # Tolerance for floating point comparison
        tol = 1e-3
        
        # Check angles
        angles_90 = [abs(angle - 90.0) < tol for angle in [alpha, beta, gamma]]
        all_90 = all(angles_90)
        
        # Check lengths
        a_eq_b = abs(a - b) < tol
        b_eq_c = abs(b - c) < tol
        a_eq_c = abs(a - c) < tol
        all_equal = a_eq_b and b_eq_c
        
        if all_equal and all_90:
            return "cubic"
        elif a_eq_b and all_90:
            return "tetragonal"
        elif all_90:
            return "orthorhombic"
        elif a_eq_b and abs(gamma - 120.0) < tol and angles_90[0] and angles_90[1]:
            return "hexagonal"
        elif a_eq_b and a_eq_c and abs(alpha - beta) < tol and abs(beta - gamma) < tol:
            if abs(alpha - 90.0) < tol:
                return "cubic"
            else:
                return "rhombohedral"
        elif angles_90[0] and abs(gamma - 90.0) > tol:
            return "monoclinic"
        else:
            return "triclinic"

    def _get_kpoint_path(self, crystal_system: str, lattice_params) -> tuple:
        """Get appropriate k-point path for crystal system."""
        
        if crystal_system == "cubic":
            # Standard cubic path: Γ-X-M-Γ-R-X|M-R
            kpath = "0.0 0.0 0.0  0.5 0.0 0.0  0.5 0.5 0.0  0.0 0.0 0.0  0.5 0.5 0.5"
            labels = ["G", "X", "M", "G", "R"]
            
        elif crystal_system == "tetragonal":
            # Tetragonal path: Γ-X-M-Γ-Z-R-A-Z
            kpath = "0.0 0.0 0.0  0.5 0.0 0.0  0.5 0.5 0.0  0.0 0.0 0.0  0.0 0.0 0.5  0.5 0.0 0.5  0.5 0.5 0.5  0.0 0.0 0.5"
            labels = ["G", "X", "M", "G", "Z", "R", "A", "Z"]
            
        elif crystal_system == "hexagonal":
            # Hexagonal path: Γ-M-K-Γ-A-L-H-A 
            kpath = "0.0 0.0 0.0  0.5 0.0 0.0  0.333 0.333 0.0  0.0 0.0 0.0  0.0 0.0 0.5  0.5 0.0 0.5  0.333 0.333 0.5  0.0 0.0 0.5"
            labels = ["G", "M", "K", "G", "A", "L", "H", "A"]
            
        elif crystal_system == "orthorhombic":
            # Orthorhombic path: Γ-X-S-Y-Γ-Z-U-R-T-Z
            kpath = "0.0 0.0 0.0  0.5 0.0 0.0  0.5 0.5 0.0  0.0 0.5 0.0  0.0 0.0 0.0  0.0 0.0 0.5  0.5 0.0 0.5  0.5 0.5 0.5  0.0 0.5 0.5  0.0 0.0 0.5"
            labels = ["G", "X", "S", "Y", "G", "Z", "U", "R", "T", "Z"]
            
        elif crystal_system == "rhombohedral":
            # Rhombohedral path: Γ-L-B1|B-Z-Γ-X
            kpath = "0.0 0.0 0.0  0.5 0.5 0.0  0.5 0.0 0.5  0.0 0.0 0.5  0.0 0.0 0.0  0.5 0.0 0.0"
            labels = ["G", "L", "B", "Z", "G", "X"]
            
        else:
            # Default path for monoclinic/triclinic or unknown systems
            kpath = "0.0 0.0 0.0  0.5 0.0 0.0  0.5 0.5 0.0  0.0 0.5 0.0  0.0 0.0 0.0  0.0 0.0 0.5"
            labels = ["G", "X", "S", "Y", "G", "Z"]
        
        return kpath, labels
    
    def run_atomsk(command: str) -> str:
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return str(e)

    def run_phonopy(command: str) -> str:
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            success = result.returncode == 0
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()

            if success:
                return stdout if stdout else "[Phonopy]: No output returned."

            # Optional: Save error log to a file
            error_log_path = os.path.join(os.getcwd(), "phonopy_error.log")
            with open(error_log_path, 'w') as f:
                f.write(f"Command: {command}\n\nSTDERR:\n{stderr}\n\nSTDOUT:\n{stdout}\n")

            # Return a detailed error message
            return f"[Phonopy Error]: Command failed.\nReturn code: {result.returncode}\n\nSTDERR:\n{stderr}\n\nFull log saved to: {error_log_path}"

        except Exception as e:
            return f"[Phonopy Exception]: {str(e)}"

    def save_band_conf(self, content: str, path: str = "band.conf") -> str:
        with open(path, "w") as f:
            f.write(content.strip() + "\n")
        return f"band.conf saved to: {os.path.abspath(path)}"