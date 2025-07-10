import os
import subprocess

class StructureCreator:
    """Handles crystal structure creation using Atomsk software."""

    def __init__(self, workdir: str):
        self.workdir = workdir
    
    def create_crystal_structure(self, crystal_type: str, lattice_param: float, 
                               element: str, size: str, output_format: str = "lammps") -> str:
        """Create crystal structure using atomsk."""

        # Determine output filename
        if output_format.lower() == "lammps":
            output_file = f"{element.lower()}_structure.lmp"
        else:
            output_file = f"{element.lower()}_structure.{output_format}"
        
        # Build atomsk command
        size_parts = size.split()
        cmd = [
            'atomsk', 
            '--create', crystal_type, str(lattice_param), element,
            '-duplicate'] + size_parts + [output_file]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=1200
            )
            
            output_path = os.path.join(self.workdir, output_file)
            
            if result.returncode == 0 and os.path.exists(output_path):
                size_bytes = os.path.getsize(output_path)
                
                # Count atoms
                atom_count = self._count_atoms_in_lammps_file(output_path)
                
                return f"✅ Crystal structure created successfully:\n" \
                       f"  📄 File: {output_file} ({size_bytes} bytes)\n" \
                       f"  🔬 Structure: {crystal_type} {element}\n" \
                       f"  📏 Lattice parameter: {lattice_param} Å\n" \
                       f"  📦 Size: {size}\n" \
                       f"  ⚛️  Atoms: {atom_count}"
            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                return f"Atomsk failed: {error_msg}"
                
        except subprocess.TimeoutExpired:
            return "Atomsk command timed out"
        except FileNotFoundError:
            return "Atomsk not found. Please install atomsk first."
        except Exception as e:
            return f"Error running atomsk: {str(e)}"
    
    def _count_atoms_in_lammps_file(self, filepath: str) -> str:
        """Count atoms in LAMMPS data file."""
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    if 'atoms' in line:
                        return line.split()[0]
        except:
            pass
        return "unknown"
    
    def create_random_alloy_structure(self, crystal_type: str, lattice_param: float,
                                  base_element: str, alloy_element: str,
                                  size: str, alloy_fraction: float,
                                  output_filename: str = None,
                                  shape_filter: bool = False,
                                  cylinder_axis: str = "Z", cylinder_radius: float = 40.0) -> str:
        """ Use this function when tasked to calculate properties of an alloy structure.
            Creates a random alloy by substituting a fraction of base_element atoms with alloy_element,
            optionally shaping the structure.
            Uses atomsk to create the .lmp file."""
        
        if output_filename is None:
            output_filename = f"{base_element.lower()}_{int(alloy_fraction*100)}{alloy_element.lower()}_alloy.lmp"

        base_file = "base_structure.cfg"
        shaped_file = "shaped_structure.cfg"

        size_parts = size.split()
        create_cmd = [
            'atomsk', '--create', crystal_type, str(lattice_param), base_element,
            '-duplicate'] + size_parts + [base_file]

        try:
            subprocess.run(create_cmd, cwd=self.workdir, check=True, capture_output=True, text=True)

            # Optional shaping: cylindrical clipping
            if shape_filter:
                clip_cmd = [
                    'atomsk', base_file,
                    '-select', 'out', 'cylinder', cylinder_axis,
                    '0.5*box', '0.5*box', str(cylinder_radius),
                    '-remove-atom', 'select', shaped_file
                ]
                subprocess.run(clip_cmd, cwd=self.workdir, check=True, capture_output=True, text=True)
                input_file = shaped_file
            else:
                input_file = base_file

            # Substitution
            substitution_percentage = f"{int(alloy_fraction * 100)}%"
            alloy_cmd = [
                'atomsk', input_file,
                '-select', 'random', substitution_percentage, base_element,
                '-substitute', base_element, alloy_element,
                output_filename
            ]

            result = subprocess.run(
                alloy_cmd,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=1200
            )

            output_path = os.path.join(self.workdir, output_filename)
            if result.returncode == 0 and os.path.exists(output_path):
                atom_count = self._count_atoms_in_lammps_file(output_path)
                return f"✅ Alloy structure created:\n" \
                    f"  File: {output_filename}\n" \
                    f"  {base_element}/{alloy_element} fraction: {1 - alloy_fraction:.2f}/{alloy_fraction:.2f}\n" \
                    f"  Shape filtering: {'Applied' if shape_filter else 'None'}\n" \
                    f"  Atoms: {atom_count}"
            else:
                return f"Atomsk alloy creation failed: {result.stderr or 'Unknown error'}"
        except subprocess.TimeoutExpired:
            return "Alloy creation timed out"
        except FileNotFoundError:
            return "Atomsk not found. Please install Atomsk."
        except subprocess.CalledProcessError as e:
            return f"Atomsk error: {e.stderr or str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"


    def create_quasirandom_alloy_structure(self, crystal_type: str, lattice_param: float,
                                  base_element: str, alloy_element: str,
                                  size: str, alloy_fraction: float,
                                  output_filename: str = None,
                                  shape_filter: bool = False,
                                  cylinder_axis: str = "Z", cylinder_radius: float = 40.0) -> str:
        """ Use this function when tasked to calculate properties of an alloy structure.
            Creates a quasi-random alloy by substituting a fraction of base_element atoms with alloy_element,
            optionally shaping the structure.
            Uses https://axelvandewalle.github.io/www-avdw/atat/ to create the .lmp file."""
        
        if output_filename is None:
            output_filename = f"{base_element.lower()}_{int(alloy_fraction*100)}{alloy_element.lower()}_alloy.lmp"

        base_file = "base_structure.cfg"
        shaped_file = "shaped_structure.cfg"

        size_parts = size.split()
        create_cmd = [
            'atomsk', '--create', crystal_type, str(lattice_param), base_element,
            '-duplicate'] + size_parts + [base_file]

        try:
            subprocess.run(create_cmd, cwd=self.workdir, check=True, capture_output=True, text=True)

            # Optional shaping: cylindrical clipping
            if shape_filter:
                clip_cmd = [
                    'atomsk', base_file,
                    '-select', 'out', 'cylinder', cylinder_axis,
                    '0.5*box', '0.5*box', str(cylinder_radius),
                    '-remove-atom', 'select', shaped_file
                ]
                subprocess.run(clip_cmd, cwd=self.workdir, check=True, capture_output=True, text=True)
                input_file = shaped_file
            else:
                input_file = base_file

            # Substitution
            substitution_percentage = f"{int(alloy_fraction * 100)}%"
            alloy_cmd = [
                'atomsk', input_file,
                '-select', 'random', substitution_percentage, base_element,
                '-substitute', base_element, alloy_element,
                output_filename
            ]

            result = subprocess.run(
                alloy_cmd,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=1200
            )

            output_path = os.path.join(self.workdir, output_filename)
            if result.returncode == 0 and os.path.exists(output_path):
                atom_count = self._count_atoms_in_lammps_file(output_path)
                return f"✅ Alloy structure created:\n" \
                    f"  File: {output_filename}\n" \
                    f"  {base_element}/{alloy_element} fraction: {1 - alloy_fraction:.2f}/{alloy_fraction:.2f}\n" \
                    f"  Shape filtering: {'Applied' if shape_filter else 'None'}\n" \
                    f"  Atoms: {atom_count}"
            else:
                return f"Atomsk alloy creation failed: {result.stderr or 'Unknown error'}"
        except subprocess.TimeoutExpired:
            return "Alloy creation timed out"
        except FileNotFoundError:
            return "Atomsk not found. Please install Atomsk."
        except subprocess.CalledProcessError as e:
            return f"Atomsk error: {e.stderr or str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

# The initial structure should always be minimized


# better way to create alloy structures: https://axelvandewalle.github.io/www-avdw/atat/ (https://www.sciencedirect.com/science/article/pii/S0364591613000540)
# should also add some checks for structure quality assessment