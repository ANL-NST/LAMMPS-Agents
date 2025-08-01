class HPCManager:
    """Handles HPC operations (upload, run, download)."""
    
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.username = "avriza"
        self.jump_host = "mega.cnm.anl.gov"
        self.target_host = "carbon.cnm.anl.gov"


    def upload_files(self, files: str = "*", remote_dir: str = "lammps_run_test") -> str:
        """Upload files to HPC, looking in workdir."""
        import os
        import subprocess
        
        try:
            if files == "*":
                # Upload all files in workdir
                files_to_upload = []
                if os.path.exists(self.workdir):
                    for file in os.listdir(self.workdir):
                        filepath = os.path.join(self.workdir, file)
                        if os.path.isdir(filepath) or os.path.isfile(filepath):
                            files_to_upload.append(filepath)

                if not files_to_upload:
                    return f"No files found in {self.workdir}"
                    
            else:
                file_list = [f.strip() for f in files.split(',')] 
                files_to_upload = []
                
                for filename in file_list:
                    if filename:
                        filepath = os.path.join(self.workdir, filename)
                        
                        if os.path.exists(filepath):
                            files_to_upload.append(filepath)
                            print(f"Found: {filepath}")
                        else:
                            print(f"Missing: {filepath}")
                            available = [f for f in os.listdir(self.workdir) 
                                    if os.path.exists(os.path.join(self.workdir, f))]
                            return f"File not found: {filename}\nAvailable files in {self.workdir}: {available}"
            
            if not files_to_upload:
                return "No valid files to upload"
            
            # Remove duplicates (in case same file appears multiple times)
            files_to_upload = list(set(files_to_upload))
            
            # Upload all files in one command
            upload_cmd = ["scp", "-rv"] + files_to_upload + [f"carbon:/home/{self.username}/{remote_dir}/"]
            print(f"Executing: {' '.join(upload_cmd)}")  # Debug line
            
            result = subprocess.run(upload_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                file_names = [os.path.basename(f) for f in files_to_upload]
                return f"Successfully uploaded {len(files_to_upload)} files: {', '.join(file_names)}"
            else:
                return f"Upload failed: {result.stderr}"
                
        except Exception as e:
            return f"Upload failed: {str(e)}"

    def run_lammps(self, input_file: str = "input.lammps", remote_dir: str = "lammps_run_test") -> str:
        """Run LAMMPS on Carbon HPC."""
        import subprocess
        import os
        
        # Command to run LAMMPS in carbon HPC
        lammps_cmd = f'ssh carbon "cd ~/{remote_dir} && module load lammps && lmp_serial < {input_file}"'

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
    
        try:
            lammps_binary = "/Users/umakornu/Documents/Work/LAMMPS/mylammps/build/lmp"

            result = subprocess.run(
                f"{lammps_binary} -in {input_file}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=1000
            )

            if result.returncode == 0:
            # Call the results-to-pdf extraction function
                # extract_status = extract_lammps_results_to_pdf(log_path, output_pdf)
                return f"Simulation completed successfully."
            else:
                return f"[LAMMPS Error]:\n{result.stderr}"
        except Exception as e:
            return f"[LAMMPS Exception]: {str(e)}"

    def download_results(self, remote_dir: str = "lammps_run_test", 
                        file_pattern: str = "*.dump *.log *.data") -> str:
        """Download results from Carbon HPC."""
        import subprocess
        
        # remote_path = f"{self.username}@{self.target_host}:~/{remote_dir}/"
        
        download_cmd = f"scp -rq carbon:/home/avriza/{remote_dir}/* ."
        #scp -rq carbon:/home/avriza/<workdir> .
        try:
            result = subprocess.run(
                download_cmd,
                shell=True,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=800 
            )
            
            if result.returncode == 0:
                return f"Results downloaded successfully"
            else:
                return f"Download failed: {result.stderr}"
                
        except Exception as e:
            return f"Download error: {str(e)}"
        

    def run_all_lammps_displacements(self, remote_dir: str = "lammps_run_test") -> str:
        """Run LAMMPS in all disp-* directories on HPC."""
        import subprocess
        try:

            lammps_cmd = f'''ssh carbon "cd ~/{remote_dir} && module load lammps && \
                for d in disp-*; do \
                if [ -d \\\"$d\\\" ]; then \
                    cd \\\"$d\\\"; \
                    lmp_serial -in in.lmp > lammps.out; \
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