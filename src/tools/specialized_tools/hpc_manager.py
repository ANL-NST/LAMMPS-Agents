import os
class HPCManager:
    """Handles HPC operations (upload, run, download)."""
    
    def __init__(self, workdir: str):
        self.workdir = workdir
        # self.username = "avriza"
        # self.jump_host = "mega.cnm.anl.gov"
        # self.target_host = "carbon.cnm.anl.gov"


    # def upload_files(self, files: str = "*", remote_dir: str = "lammps_run_test") -> str:
    #     """Upload files to HPC, looking in workdir."""
    #     import os
    #     import subprocess
        
    #     try:
    #         if files == "*":
    #             # Upload all files in workdir
    #             files_to_upload = []
    #             if os.path.exists(self.workdir):
    #                 for file in os.listdir(self.workdir):
    #                     filepath = os.path.join(self.workdir, file)
    #                     if os.path.isdir(filepath) or os.path.isfile(filepath):
    #                         files_to_upload.append(filepath)

    #             if not files_to_upload:
    #                 return f"No files found in {self.workdir}"
                    
    #         else:
    #             file_list = [f.strip() for f in files.split(',')] 
    #             files_to_upload = []
                
    #             for filename in file_list:
    #                 if filename:
    #                     filepath = os.path.join(self.workdir, filename)
                        
    #                     if os.path.exists(filepath):
    #                         files_to_upload.append(filepath)
    #                         print(f"Found: {filepath}")
    #                     else:
    #                         print(f"Missing: {filepath}")
    #                         available = [f for f in os.listdir(self.workdir) 
    #                                 if os.path.exists(os.path.join(self.workdir, f))]
    #                         return f"File not found: {filename}\nAvailable files in {self.workdir}: {available}"
            
    #         if not files_to_upload:
    #             return "No valid files to upload"
            
    #         # Remove duplicates (in case same file appears multiple times)
    #         files_to_upload = list(set(files_to_upload))
            
    #         # Upload all files in one command
    #         upload_cmd = ["scp", "-rv"] + files_to_upload + [f"carbon:/home/{self.username}/{remote_dir}/"]
    #         print(f"Executing: {' '.join(upload_cmd)}")  # Debug line
            
    #         result = subprocess.run(upload_cmd, capture_output=True, text=True)
            
    #         if result.returncode == 0:
    #             file_names = [os.path.basename(f) for f in files_to_upload]
    #             return f"Successfully uploaded {len(files_to_upload)} files: {', '.join(file_names)}"
    #         else:
    #             return f"Upload failed: {result.stderr}"
                
    #     except Exception as e:
    #         return f"Upload failed: {str(e)}"


    def upload_files(self, files: str = "*", remote_dir: str = "lammps_run_test", batch_size: int = 50, include_dirs: bool = True) -> str:
        """Upload files and directories, with support for both."""
        import os
        import subprocess
        import glob
        
        try:
            if files == "*":
                # Upload all files and directories in workdir
                items_to_upload = []
                if os.path.exists(self.workdir):
                    for item in os.listdir(self.workdir):
                        itempath = os.path.join(self.workdir, item)
                        if os.path.exists(itempath):
                            items_to_upload.append(itempath)
                
                if not items_to_upload:
                    return f"No items found in {self.workdir}"
            
            else:
                file_list = [f.strip() for f in files.split(',')]
                items_to_upload = []
                
                for filename in file_list:
                    if filename:
                        # Check if filename contains wildcards
                        if '*' in filename or '?' in filename or '[' in filename:
                            # Handle glob pattern
                            pattern = os.path.join(self.workdir, filename)
                            matching_items = glob.glob(pattern)
                            
                            if matching_items:
                                # Include both files and directories
                                valid_items = []
                                files_count = 0
                                dirs_count = 0
                                
                                for item in matching_items:
                                    if os.path.exists(item):
                                        if os.path.isfile(item):
                                            valid_items.append(item)
                                            files_count += 1
                                        elif os.path.isdir(item) and include_dirs:
                                            valid_items.append(item)
                                            dirs_count += 1
                                
                                if valid_items:
                                    items_to_upload.extend(valid_items)
                                    print(f"Found {len(valid_items)} items matching pattern '{filename}': {files_count} files, {dirs_count} directories")
                                else:
                                    print(f"No valid items found for pattern: {filename}")
                            else:
                                available = [f for f in os.listdir(self.workdir) if f.startswith(filename.replace('*', ''))][:10]
                                return f"No items found matching pattern: {filename}\nSample available items: {available}"
                        
                        else:
                            # Handle literal filename/dirname
                            itempath = os.path.join(self.workdir, filename)
                            
                            if os.path.exists(itempath):
                                if os.path.isfile(itempath) or (os.path.isdir(itempath) and include_dirs):
                                    items_to_upload.append(itempath)
                                    print(f"Found: {itempath} ({'file' if os.path.isfile(itempath) else 'directory'})")
                                else:
                                    return f"Item exists but is not a file or directory: {filename}"
                            else:
                                print(f"Missing: {itempath}")
                                return f"Item not found: {filename}"
            
            if not items_to_upload:
                return "No valid items to upload"
            
            # Remove duplicates
            items_to_upload = list(set(items_to_upload))
            
            # Count files vs directories
            files_count = sum(1 for item in items_to_upload if os.path.isfile(item))
            dirs_count = sum(1 for item in items_to_upload if os.path.isdir(item))
            
            # Upload in batches to avoid command line length limits
            total_items = len(items_to_upload)
            uploaded_count = 0
            failed_batches = []
            
            print(f"Uploading {total_items} items ({files_count} files, {dirs_count} directories) in batches of {batch_size}")
            
            for i in range(0, total_items, batch_size):
                batch = items_to_upload[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (total_items + batch_size - 1) // batch_size
                
                print(f"Uploading batch {batch_num}/{total_batches} ({len(batch)} items)")
                
                # Upload this batch (scp -r handles both files and directories)
                upload_cmd = ["scp", "-rv"] + batch + [f"carbon:/home/{self.username}/{remote_dir}/"]
                
                result = subprocess.run(upload_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    uploaded_count += len(batch)
                    print(f"Batch {batch_num} uploaded successfully")
                else:
                    failed_batches.append(batch_num)
                    print(f"Batch {batch_num} failed: {result.stderr}")
                    
                    # Try uploading items in this batch individually
                    print(f"Retrying batch {batch_num} items individually...")
                    individual_success = 0
                    for item in batch:
                        single_cmd = ["scp", "-rv", item, f"carbon:/home/{self.username}/{remote_dir}/"]
                        single_result = subprocess.run(single_cmd, capture_output=True, text=True, timeout=120)
                        if single_result.returncode == 0:
                            individual_success += 1
                            print(f"  Successfully uploaded: {os.path.basename(item)}")
                        else:
                            print(f"  Failed to upload: {os.path.basename(item)}")
                    
                    if individual_success > 0:
                        uploaded_count += individual_success
                        print(f"Recovered {individual_success}/{len(batch)} items from batch {batch_num}")
            
            if failed_batches:
                return f"Uploaded {uploaded_count}/{total_items} items. Some batches had issues: {failed_batches}"
            else:
                return f"Successfully uploaded all {uploaded_count} items ({files_count} files, {dirs_count} directories) in {total_batches} batches"
        
        except Exception as e:
            return f"Upload failed: {str(e) }"
        

    # def run_lammps(self, input_file: str = "input.lammps", remote_dir: str = "lammps_run_test") -> str:
    #     """Run LAMMPS on Carbon HPC."""
    #     import subprocess
        
    #     # Command to run LAMMPS in carbon HPC
    #     lammps_cmd = f'ssh carbon "cd ~/{remote_dir} && module load lammps && lmp_serial < {input_file}"'

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
    

    # def download_results(self, remote_dir: str = "lammps_run_test") -> str:
    #     """Download results from Carbon HPC."""
    #     import subprocess
        
    #     # remote_path = f"{self.username}@{self.target_host}:~/{remote_dir}/"
        
    #     download_cmd = f"scp -rq carbon:/home/avriza/{remote_dir}/* ."
    #     #scp -rq carbon:/home/avriza/<workdir> .
    #     try:
    #         result = subprocess.run(
    #             download_cmd,
    #             shell=True,
    #             cwd=self.workdir,
    #             capture_output=True,
    #             text=True,
    #             timeout=800 
    #         )
            
    #         if result.returncode == 0:
    #             return f"Results downloaded successfully"
    #         else:
    #             return f"Download failed: {result.stderr}"
                
    #     except Exception as e:
    #         return f"Download error: {str(e)}"
        

    # def download_results(self, remote_dir: str = "lammps_run_test", 
    #                     file_pattern: str = "*") -> str:
    #     """Download results from Carbon HPC."""
    #     import subprocess
    #     import os
        
    #     try:
    #         if not os.path.exists(self.workdir):
    #             os.makedirs(self.workdir)
            
    #         if file_pattern.strip() == "*":
    #             download_cmd = f"rsync -av carbon:/home/avriza/{remote_dir}/ ."
    #             print("Using rsync for full directory download (includes all subdirectories)...")
    #         else:
    #             patterns = file_pattern.split()
    #             include_args = ""
    #             for pattern in patterns:
    #                 include_args += f"--include='{pattern}' "
    #             download_cmd = f"rsync -av --include='*/' {include_args}--exclude='*' carbon:/home/avriza/{remote_dir}/ ."
    #             print(f"Using rsync with patterns: {file_pattern} (includes matching directories)")
            
    #         result = subprocess.run(
    #             download_cmd,
    #             shell=True,
    #             cwd=self.workdir,
    #             capture_output=True,
    #             text=True,
    #             timeout=6000  
    #         )
            
    #         if result.returncode == 0:
    #             return f"Results downloaded successfully with rsync (includes directories and files)"
            
    #         print("Rsync failed, falling back to scp (recursive for directories)...")
            
    #         if file_pattern.strip() == "*":
    #             download_cmd = f"scp -rq carbon:/home/avriza/{remote_dir}/* ."
    #         # else:
    #         #     patterns = file_pattern.split()
    #         #     if len(patterns) == 1:
    #         #         download_cmd = f"scp -rq carbon:/home/avriza/{remote_dir}/{patterns[0]} ."
    #         #     else:
    #         #         success_count = 0
    #         #         total_patterns = len(patterns)
                    
    #         #         for pattern in patterns:
    #         #             pattern_cmd = f"scp -rq carbon:/home/avriza/{remote_dir}/{pattern} ."
    #         #             pattern_result = subprocess.run(
    #         #                 pattern_cmd,
    #         #                 shell=True,
    #         #                 cwd=self.workdir,
    #         #                 capture_output=True,
    #         #                 text=True,
    #         #                 timeout=6000
    #         #             )
    #         #             if pattern_result.returncode == 0:
    #         #                 success_count += 1
    #         #                 print(f"Downloaded items (files/dirs) matching: {pattern}")
                    
    #         #         if success_count > 0:
    #         #             return f"Downloaded items for {success_count}/{total_patterns} patterns (includes directories)"
    #         #         else:
    #         #             return f"No items found matching any patterns: {file_pattern}"
            
    #         result = subprocess.run(
    #             download_cmd,
    #             shell=True,
    #             cwd=self.workdir,
    #             capture_output=True,
    #             text=True,
    #             timeout=800
    #         )
            
    #         if result.returncode == 0:
    #             return f"Results downloaded successfully with scp (includes directories and files)"
    #         else:
    #             return f"Download failed: {result.stderr}"
                
        # except subprocess.TimeoutExpired:
        #     return "Download timed out - try with smaller file patterns"
        # except Exception as e:
        #     return f"Download error: {str(e)}"


    # def run_all_lammps_displacements(self, remote_dir: str = "lammps_run_test") -> str:
    #     """Run LAMMPS in all disp-* directories on HPC."""
    #     import subprocess
    #     try:

    #         lammps_cmd = f'''ssh carbon "cd ~/{remote_dir} && module load lammps && \
    #             for d in disp-*; do \
    #             if [ -d \\\"$d\\\" ]; then \
    #                 cd \\\"$d\\\"; \
    #                 lmp_serial -in in.lmp > lammps.out; \
    #                 cd ..; \
    #             fi; \
    #             done"'''

    #         result = subprocess.run(
    #             lammps_cmd,
    #             shell=True,
    #             capture_output=True,
    #             text=True,
    #             timeout=7200
    #         )
            
    #         return f"""LAMMPS Batch Run:
    # EXIT CODE: {result.returncode}
    # STDOUT:
    # {result.stdout[-1000:]}

    # STDERR:
    # {result.stderr[-1000:]}
    # """ if result.returncode == 0 else f"Error:\n{result.stderr}"
        
    #     except Exception as e:
    #         return f"Exception during remote LAMMPS batch run: {e}"
        
    
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

    
    def run_all_lammps_displacements_local(
        self,
        lammps_folder: str = None,
        *,
        # backward-compat with your earlier signature
        remote_dir: str = None,
        lammps_exe: str = "lmp",          # e.g. "lmp", "lmp.exe", "lmp_serial", "lmp_mpi"
        input_file: str = "in.lmp",
        timeout_s: int = 7200,
        mpi_cmd: list | None = None,      # e.g. ["mpiexec", "-n", "8"] to run with MPI
        tail_lines: int = 12
    ) -> str:
        """
        Run LAMMPS in all 'disp-*' subdirectories under the given root folder.
        - Cross-platform (no shell loops).
        - Writes combined stdout/stderr to disp-*/lammps.out.
        - Returns a summary with exit codes and the last lines of each log.

        Args:
            lammps_folder: Root directory containing disp-* subfolders.
            remote_dir: (deprecated) Alias of lammps_folder for backward compatibility.
            lammps_exe: LAMMPS executable name or full path.
            input_file: Input script name inside each disp-* folder.
            timeout_s: Per-job timeout in seconds.
            mpi_cmd: Optional launcher prefix, e.g. ["mpiexec", "-n", "8"].
            tail_lines: Number of lines to show from end of each lammps.out in the summary.
        """
        import os
        import glob
        import shutil
        import subprocess
        from collections import Counter

        # Resolve folder argument with backward compatibility
        root = lammps_folder or remote_dir
        if not root:
            return "Error: You must pass lammps_folder (or remote_dir for backward compatibility)."

        root = os.path.abspath(os.path.expanduser(root))
        if not os.path.isdir(root):
            return f"Error: '{root}' is not a valid directory."

        # Check LAMMPS executable
        if shutil.which(lammps_exe) is None and not os.path.isfile(lammps_exe):
            return (f"Error: LAMMPS executable '{lammps_exe}' not found on PATH or as a file. "
                    f"Provide the correct name or full path (e.g., 'lmp.exe').")

        disp_dirs = sorted([d for d in glob.glob(os.path.join(root, "disp-*")) if os.path.isdir(d)])
        if not disp_dirs:
            return f"No 'disp-*' subdirectories found inside '{root}'."

        def _tail(path: str, n: int) -> str:
            try:
                with open(path, "rb") as fh:
                    # Efficient tail for moderate files
                    fh.seek(0, os.SEEK_END)
                    size = fh.tell()
                    block = 4096
                    data = b""
                    while size > 0 and data.count(b"\n") <= n:
                        jump = min(block, size)
                        size -= jump
                        fh.seek(size)
                        data = fh.read(jump) + data
                    lines = data.splitlines()[-n:]
                return "\n".join(line.decode("utf-8", errors="ignore") for line in lines)
            except FileNotFoundError:
                return "(lammps.out not found)"
            except Exception as e:
                return f"(failed to read lammps.out: {e})"

        results = []
        counts = Counter()

        for d in disp_dirs:
            in_path = os.path.join(d, input_file)
            out_path = os.path.join(d, "lammps.out")

            if not os.path.isfile(in_path):
                results.append((d, "SKIPPED: missing in.lmp", None))
                counts["skipped"] += 1
                continue

            cmd = ([lammps_exe, "-in", input_file] if not mpi_cmd
                else [*mpi_cmd, lammps_exe, "-in", input_file])

            try:
                with open(out_path, "w", encoding="utf-8", errors="ignore") as fh:
                    proc = subprocess.run(
                        cmd,
                        cwd=d,
                        stdout=fh,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=timeout_s
                    )
                if proc.returncode == 0:
                    counts["ok"] += 1
                    status = f"OK (exit 0)"
                else:
                    counts["fail"] += 1
                    status = f"FAILED (exit {proc.returncode})"
                results.append((d, status, _tail(out_path, tail_lines)))
            except subprocess.TimeoutExpired:
                counts["timeout"] += 1
                results.append((d, f"TIMEOUT after {timeout_s}s", _tail(out_path, tail_lines)))
            except Exception as e:
                counts["exception"] += 1
                # Try to capture any partial output
                results.append((d, f"EXCEPTION: {e}", _tail(out_path, tail_lines)))

        # Build summary text
        header = [
            f"LAMMPS Batch Run in: {root}",
            f"Found {len(disp_dirs)} disp-* folders",
            f"Results: OK={counts['ok']}, FAIL={counts['fail']}, TIMEOUT={counts['timeout']}, "
            f"SKIPPED={counts['skipped']}, EXCEPTION={counts['exception']}",
            ""
        ]
        blocks = []
        for d, status, tail in results:
            name = os.path.basename(d)
            blocks.append(
                f"[{name}] {status}\n"
                f"--- tail of lammps.out ({tail_lines} lines) ---\n{tail}\n"
            )
        return "\n".join(header + blocks)
