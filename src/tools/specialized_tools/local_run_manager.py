class LocalRunManager:
    """Handles HPC operations (upload, run, download)."""
    
    def __init__(self, workdir: str):
        self.workdir = workdir


    def run_lammps_local(self, input_file: str = "input.lammps", remote_dir: str = "lammps_run_test") -> str:
        """Run LAMMPS locally."""
        import subprocess
        import os

        # Ensure remote_dir is not appended twice
        if remote_dir in self.workdir:
            full_path = os.path.join(self.workdir, input_file)
        else:
            full_path = os.path.join(self.workdir, remote_dir, input_file)

        full_path = os.path.abspath(full_path)
        print(f"Full path to input file: {full_path}")  # Debug: Print the full path

        # Check if the file exists
        if not os.path.exists(full_path):
            return f"Error: Input file '{full_path}' does not exist."

        # Local LAMMPS command
        lammps_cmd = f"lmp -in {full_path}"
        print(f"Executing command: {lammps_cmd}")  # Debug: Print the command

        try:
            result = subprocess.run(
                lammps_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=6000
            )

            output = f"LAMMPS execution completed (exit code: {result.returncode})\n"
            if result.stdout:
                output += f"STDOUT:\n{result.stdout[-1000:]}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr[-1000:]}\n"
            return output

        except subprocess.TimeoutExpired:
            return "LAMMPS execution timed out"
        except Exception as e:
            return f"LAMMPS execution error: {str(e)}"

    # def run_lammps_local(self, input_file: str = "input.lammps", remote_dir: str = "lammps_run_test") -> str:
    #     """Run LAMMPS on Carbon HPC."""
    #     import subprocess
        
    #     # Command to run LAMMPS in carbon HPC
    #     # lammps_cmd = f'lmp -in < {input_file}"'
    #     import os
    #     lammps_cmd = f"lmp -in {os.path.join(remote_dir, input_file)}"

    #     try:
    #         result = subprocess.run(
    #             lammps_cmd,
    #             shell=True,
    #             capture_output=True,
    #             text=True,
    #             timeout=6000  # this is important to set high in case we have long calculations so that the agentic system will not timeout before completion
    #         )
            
    #         output = f"LAMMPS execution completed (exit code: {result.returncode})\n"
            
    #         if result.stdout:
    #             output += f"STDOUT:\n{result.stdout[-1000:]}\n"  # Last 1000 chars
            
    #         if result.stderr:
    #             output += f"STDERR:\n{result.stderr[-1000:]}\n"
            
    #         return output
            
    #     except subprocess.TimeoutExpired:
    #         return "LAMMPS execution timed out"
    #     except Exception as e:
    #         return f"LAMMPS execution error: {str(e)}"
    

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