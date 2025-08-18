
class FileManager:
    """Fixed version of FileManager with proper file saving."""
    
    def __init__(self, workdir: str):
        self.workdir = workdir
        
    def save_lammps_input(self, content: str, filename: str = "input.lammps") -> str:
        """Save LAMMPS input file with relaxed validation."""
        
        import os        
        # Checking for critical keywords
        required_keywords = ['units', 'boundary']  
        missing = [kw for kw in required_keywords if kw not in content.lower()]

        filepath = os.path.join(self.workdir, filename)
        
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                
                # Results message
                result = f"✅ LAMMPS input saved: {filename} ({size} bytes)\n"
                result += f"📂 Location: {filepath}\n"
                
                if missing:
                    result += f"⚠️  Note: Missing optional keywords: {missing}\n"
                else:
                    result += "✅ LAMMPS input validation passed\n"

                try:
                    files = os.listdir(self.workdir)
                    result += f"📁 Files in workdir: {files}"
                except:
                    pass
                
                return result
            else:
                return f"Error: File {filename} was not created at {filepath}"
                
        except Exception as e:
            return f"Error saving LAMMPS input: {str(e)}\n📂 Attempted path: {filepath}"

    
    def save_potential_file(self, content: str, potential_type: str, filename: str = None) -> str:
        """Save potential file with type-specific validation."""
        import os
        
        # Auto-detect filename based on potential type
        if not filename:
            if potential_type.lower() == 'sw' or 'stillinger' in content.lower():
                filename = "Si.sw"
            elif potential_type.lower() == 'eam':
                filename = "potential.eam"
            elif potential_type.lower() == 'tersoff':
                filename = "potential.tersoff"
            else:
                filename = f"potential.{potential_type}"
        
        filepath = os.path.join(self.workdir, filename)
        
        try:
            with open(filepath, 'w') as f:
                f.write(content)
            
            size = os.path.getsize(filepath)
            
            # Validate potential file content
            validation = self._validate_potential_file(content, potential_type)
            
            return f"✅ Potential file saved: {filename} ({size} bytes)\n{validation}"
            
        except Exception as e:
            return f"❌ Error saving potential file: {str(e)}"
    
    def save_structure_file(self, content: str, format_type: str, filename: str = None) -> str:
        """Save structure file (from atomsk or other sources)."""
        import os
        
        if not filename:
            if format_type.lower() == 'lammps' or format_type.lower() == 'lmp':
                filename = "structure.lmp"
            elif format_type.lower() == 'xyz':
                filename = "structure.xyz"
            elif format_type.lower() == 'cfg':
                filename = "structure.cfg"
            else:
                filename = f"structure.{format_type}"
        
        filepath = os.path.join(self.workdir, filename)
        
        try:
            with open(filepath, 'w') as f:
                f.write(content)
            
            size = os.path.getsize(filepath)
            
            # Count atoms if possible
            atom_count = self._count_atoms_in_structure(content, format_type)
            
            return f"✅ Structure file saved: {filename} ({size} bytes, ~{atom_count} atoms)"
            
        except Exception as e:
            return f"❌ Error saving structure file: {str(e)}"
    

    def _validate_potential_file(self, content: str, potential_type: str) -> str:
        """Validate potential file content."""
        if potential_type.lower() == 'sw':
            if not any(param in content for param in ['2.0951', 'epsilon', 'sigma']):
                return "⚠️  Warning: SW potential may be incomplete"
        elif potential_type.lower() == 'eam':
            if 'comment' not in content.lower() and '#' not in content:
                return "⚠️  Warning: EAM potential may be incomplete"
        
        return "Potential file validation passed"
    
    def _count_atoms_in_structure(self, content: str, format_type: str) -> str:
        """Estimate atom count in structure file."""
        lines = content.split('\n')
        
        if format_type.lower() == 'lammps':
            for line in lines:
                if 'atoms' in line:
                    try:
                        return line.split()[0]
                    except:
                        pass
        elif format_type.lower() == 'xyz':
            try:
                return lines[0].strip()
            except:
                pass
        
        return "unknown"
    
    def list_files(self) -> str:
        """List all files in working directory with details."""
        import os
        
        if not os.path.exists(self.workdir):
            return f"Working directory {self.workdir} does not exist"
        
        files = []
        for item in os.listdir(self.workdir):
            filepath = os.path.join(self.workdir, item)
            if os.path.isfile(filepath):
                size = os.path.getsize(filepath)
                files.append(f"  📄 {item} ({size} bytes)")
            elif os.path.isdir(filepath):
                files.append(f"  📁 {item}/")
        
        if not files:
            return f"Working directory {self.workdir} is empty"
        
        return f"Files in {self.workdir}:\n" + "\n".join(files)

class StructureCreator:
    """Handles crystal structure creation with atomsk."""
    import os
    def __init__(self, workdir: str):
        self.workdir = workdir
    
    def create_crystal_structure(self, crystal_type: str, lattice_param: float, 
                               element: str, size: str, output_format: str = "lammps") -> str:
        """Create crystal structure using atomsk."""
        import subprocess
        import os
        
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
                timeout=60
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
                return f"❌ Atomsk failed: {error_msg}"
                
        except subprocess.TimeoutExpired:
            return "❌ Atomsk command timed out"
        except FileNotFoundError:
            return "❌ Atomsk not found. Please install atomsk first."
        except Exception as e:
            return f"❌ Error running atomsk: {str(e)}"
    
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
    
    
    def run_lammps_local(self, input_file: str = "input.lammps", remote_dir: str = "lammps_run_test") -> str:
        """Run LAMMPS on Carbon HPC."""
        import subprocess
        
        # Command to run LAMMPS in carbon HPC
        lammps_cmd = f'lmp -in < {input_file}"'

        try:
            result = subprocess.run(
                lammps_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=6000  # this is important to set high in case we have long calculations so that the agentic system will not timeout before completion
            )
            
            output = f"LAMMPS execution completed (exit code: {result.returncode})\n"
            
            if result.stdout:
                output += f"STDOUT:\n{result.stdout[-1000:]}\n"  # Last 1000 chars
            
            if result.stderr:
                output += f"STDERR:\n{result.stderr[-1000:]}\n"
            
            return output
            
        except subprocess.TimeoutExpired:
            return "LAMMPS execution timed out"
        except Exception as e:
            return f"LAMMPS execution error: {str(e)}"
    

    def run_all_lammps_displacements_local(self, remote_dir: str = "lammps_run_test") -> str:
        """Run LAMMPS in all disp-* directories on HPC."""
        import subprocess
        try:

            lammps_cmd = f'''
                for d in disp-*; do \
                if [ -d \\\"$d\\\" ]; then \
                    cd \\\"$d\\\"; \
                    lmp -in in.lmp > lammps.out; \
                    cd ..; \
                fi; \
                done"'''

            result = subprocess.run(
                lammps_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=7200
            )
            
            return f"""LAMMPS Batch Run:
    EXIT CODE: {result.returncode}
    STDOUT:
    {result.stdout[-1000:]}

    STDERR:
    {result.stderr[-1000:]}
    """ if result.returncode == 0 else f"Error:\n{result.stderr}"
        
        except Exception as e:
            return f"Exception during remote LAMMPS batch run: {e}"