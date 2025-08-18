from autogen import register_function
import os

class FunctionRegistry:
    """Class to register and manage functions for LAMMPS workflow agents."""
    
    def __init__(self, agents_dict, managers_dict, workdir):
        """
        Initialize the function registry.
        
        Args:
            agents_dict: Dictionary of agents from AgentFactory
            managers_dict: Dictionary of manager instances
            workdir: Working directory path
        """
        print("Initializing FunctionRegistry...")
        
        self.agents = agents_dict
        self.managers = managers_dict
        self.workdir = workdir
        
        self.lammps_admin = agents_dict['admin']
        self.structure_agent = agents_dict['structure']
        self.potential_agent = agents_dict['potential']
        self.lammps_agent = agents_dict['lammps']
        self.lammps_elastic_agent = agents_dict['lammps_elastic']
        self.hpc_agent = agents_dict['hpc']
        self.analysis_agent = agents_dict['analysis']
        self.websurfer = agents_dict['websurfer']
        self.phonopy_agent = agents_dict['phonopy']
        
        self.file_manager = managers_dict['file_manager']
        self.structure_creator = managers_dict['structure_creator']
        self.potential_manager = managers_dict['potential_manager']
        self.hpc_manager = managers_dict['hpc_manager']
        self.local_run_manager = managers_dict['local_run_manager']
        self.phonopy_manager = managers_dict['phonopy_manager']
        self.validation_manager = managers_dict.get('validation_manager')
        
        print(f"✅ Agents loaded: {list(agents_dict.keys())}")
        print(f"✅ Managers loaded: {list(managers_dict.keys())}")
        print(f"✅ ValidationManager: {self.validation_manager}")
    
    def register_all_functions(self):
        """Register all functions for all agents."""
        print("Registering functions for all agents...")
        
        self.register_structure_functions()
        self.register_potential_functions()
        self.register_lammps_functions()
        self.register_elastic_functions()
        self.register_hpc_functions()
        self.register_analysis_functions()
        self.register_phonopy_functions()
        self.register_validation_functions()
        self.register_melting_point_visualization_functions()
        print("✅ All functions registered successfully!")

    # ==================== STRUCTURE CONSTRUCTION FUNCTIONS ====================
    def register_structure_functions(self):
        """Register functions for StructureCreator agent."""
        print("Registering structure functions...")
        
        def create_crystal_structure(crystal_type: str, lattice_param: float, element: str, 
                           size: str, output_format: str = "lammps") -> str:
            return self.structure_creator.create_crystal_structure(
                crystal_type, lattice_param, element, size, output_format
            )
        
        def create_random_alloy_structure(crystal_type: str, lattice_param: float,
                                  base_element: str, alloy_element: str,
                                  size: str, alloy_fraction: float,
                                  output_filename: str = None,
                                  shape_filter: bool = False,
                                  cylinder_axis: str = "Z", cylinder_radius: float = 40.0) -> str:
            
            return self.structure_creator.create_random_alloy_structure(
                crystal_type, lattice_param,
                                  base_element, alloy_element,
                                  size, alloy_fraction,
                                  output_filename,
                                  shape_filter,
                                  cylinder_axis, cylinder_radius)      

        register_function(
            create_crystal_structure,
            caller=self.structure_agent,
            executor=self.lammps_admin,
            name="create_structure",
            description="Create crystal structure of a single element. Parameters: crystal_type (str), lattice_param (float), element (str), size (str like '10 10 10'), output_format (str, default 'lammps')",
        )

        register_function(
            create_random_alloy_structure,
            caller=self.structure_agent,
            executor=self.lammps_admin,
            name="create_alloy_structure",
                description="Create an alloy structure using Atomsk. Always use this function when tasked to calculate properties of an alloy structure. "
                "Parameters: crystal_type (str), lattice_param (float), base_element (str), alloy_element (str), "
                "size (str like '10 10 10'), alloy_fraction (float), "
                "output_filename (str, optional), shape_filter (bool, default False), cylinder_axis (str, default 'Z'), cylinder_radius (float, optional)"
            )   

    # ==================== POTENTIAL FUNCTIONS ====================
    
    def register_potential_functions(self):
        """Register functions for PotentialManager agent with enhanced ZIP/OpenKIM support."""
        print("  ⚛️  Registering potential functions...")
        
        # Basic potential functions
        def create_sw_potential(element: str = "Si") -> str:
            return self.potential_manager.create_sw_potential(element)
        
        def download_potential(potential_name: str, custom_url: str = None) -> str:
            return self.potential_manager.download_potential(potential_name, custom_url)
        
        def save_potential(content: str, potential_type: str, filename: str = None) -> str:
            return self.file_manager.save_potential_file(content, potential_type, filename)
        
        def search_github_potentials(element: str) -> str:
            return self.potential_manager.search_github_potentials(element)
        
        def auto_find_potential(element: str, crystal_structure: str = "diamond") -> str:
            return self.potential_manager.auto_find_potential(element, crystal_structure)
        
        def list_available_potentials() -> str:
            return self.potential_manager.list_available_potentials()
        
        def list_available_sources(element: str = None) -> str:
            return self.potential_manager.list_available_known_sources(element)
        
        # 🆕 NEW: OpenKIM and ZIP support functions
        def download_from_openkim(kim_model_id: str, element: str = None) -> str:
            """Download potential from OpenKIM using model ID. Supports TXZ archives."""
            return self.potential_manager.download_from_openkim(kim_model_id, element)
        
        def search_openkim(element: str, potential_type: str = "EAM") -> str:
            """Search OpenKIM database for potentials of specified element and type."""
            return self.potential_manager.search_openkim(element, potential_type)
        
        # 🆕 NEW: Advanced potential discovery functions
        def validate_potential_file(filepath: str, element: str) -> str:
            """Validate if a potential file is correct for the given element."""
            is_valid, message = self.potential_manager.validate_potential_file(filepath, element)
            return f"{'✅ VALID' if is_valid else '❌ INVALID'}: {message}"
        
        def try_known_sources(element: str, potential_type: str = "EAM") -> str:
            """Try downloading from comprehensive known sources (including ZIP archives)."""
            success, filepath, message = self.potential_manager.try_known_sources(element, potential_type)
            if success:
                return f"✅ SUCCESS: {message}\n📁 File: {filepath}"
            else:
                return f"❌ FAILED: {message}"
        
        # Register all potential functions
        functions_to_register = [
            # Core functions
            (create_sw_potential, "create_sw_potential", 
            "Create SW potential with correct parameters. Parameter: element (str, default 'Si')"),
            
            (download_potential, "download_potential", 
            "Download potential file (supports direct URLs and ZIP/TXZ archives). Parameters: potential_name (str), custom_url (str, optional)"),
            
            (save_potential, "save_potential", 
            "Save potential file content to workdir. Parameters: content (str), potential_type (str), filename (str, optional)"),
            
            (search_github_potentials, "search_github_potentials", 
            "Search GitHub LAMMPS repository for potentials. Parameter: element (str)"),
            
            (auto_find_potential, "auto_find_potential", 
            "Automatically find best potential with fallbacks. Parameters: element (str), crystal_structure (str, default 'diamond')"),
            
            (list_available_potentials, "list_available_potentials", 
            "List all potential options including ZIP sources and test results"),
            
            (list_available_sources, "list_available_sources", 
            "List available known sources for elements. Parameter: element (str, optional)"),
            
            # 🆕 NEW: OpenKIM functions
            (download_from_openkim, "download_from_openkim", 
            "Download potential from OpenKIM using model ID (handles TXZ archives). Parameters: kim_model_id (str), element (str, optional)"),
            
            (search_openkim, "search_openkim", 
            "Search OpenKIM database for potentials. Parameters: element (str), potential_type (str, default 'EAM')"),
            
            # 🆕 NEW: Advanced validation functions
            (validate_potential_file, "validate_potential_file", 
            "Validate potential file format and content. Parameters: filepath (str), element (str)"),
            
            (try_known_sources, "try_known_sources", 
            "Try downloading from known sources including archives. Parameters: element (str), potential_type (str, default 'EAM')"),
        ]
        
        # Register functions for the main potential agent
        for func, name, description in functions_to_register:
            register_function(
                func,
                caller=self.potential_agent,
                executor=self.lammps_admin,
                name=name,
                description=description,
            )
        
        # Register subset for websurfer (functions it can use to save findings)
        websurfer_functions = [
            (save_potential, "save_potential", 
            "Save potential file content found during web search. Parameters: content (str), potential_type (str), filename (str, optional)"),
            
            (download_potential, "download_potential", 
            "Download potential from URL found during search (supports ZIP/TXZ). Parameters: potential_name (str), custom_url (str, optional)"),
            
            (download_from_openkim, "download_from_openkim", 
            "Download from OpenKIM model ID found during search. Parameters: kim_model_id (str), element (str, optional)"),
            
            (validate_potential_file, "validate_potential_file", 
            "Validate potential file after download. Parameters: filepath (str), element (str)"),
        ]
        
        # Register functions for websurfer agent
        for func, name, description in websurfer_functions:
            register_function(
                func,
                caller=self.websurfer,
                executor=self.lammps_admin,
                name=name,
                description=description,
            )
        
        print(f"    ✅ Registered {len(functions_to_register)} functions for potential_agent")
        print(f"    ✅ Registered {len(websurfer_functions)} functions for websurfer")
        print("    🔬 OpenKIM ZIP/TXZ support enabled")
        print("    📦 Multi-archive format support active")
        print("    🤖 Intelligent potential file selection ready")
  

    # ==================== LAMMPS FUNCTIONS ====================
    def register_lammps_functions(self):
        """Register functions for LAMMPSInputCreator agent."""
        print("  🔧 Registering LAMMPS functions...")
        
        def save_lammps_input(content: str, filename: str = "input.lammps") -> str:
            return self.file_manager.save_lammps_input(content, filename)
        
        def check_workflow_status_wrapper() -> str:
            """Check workflow status using ValidationManager."""
            print(f"🔍 Checking workflow status. ValidationManager: {self.validation_manager}")
            
            if self.validation_manager:
                try:
                    can_continue, message = self.validation_manager.check_workflow_status()
                    print(f"🔍 Workflow status result: {can_continue}, {message}")
                    return message
                except Exception as e:
                    error_msg = f"Workflow status check error: {str(e)}"
                    print(f"🔍 {error_msg}")
                    return error_msg
            else:
                error_msg = "ValidationManager not available"
                print(f"🔍 {error_msg}")
                return error_msg
        
        # Register LAMMPS functions
        register_function(
            save_lammps_input,
            caller=self.lammps_agent,
            executor=self.lammps_admin,
            name="save_lammps_input",
            description="Save LAMMPS input file. Parameters: content (str), filename (str, default 'input.lammps')",
        )
        
        register_function(
            check_workflow_status_wrapper,
            caller=self.lammps_agent,
            executor=self.lammps_admin,
            name="check_workflow_status",
            description="Check if workflow can continue - MUST call before creating LAMMPS input",
        )
    
    # ==================== HPC FUNCTIONS ====================
    def register_hpc_functions(self):
        """Register functions for HPCExecutor agent."""
        print("Registering HPC functions...")
        
        # def upload_files(files: str = "*", remote_dir: str = "lammps_run_test") -> str:
        #     return self.hpc_manager.upload_files(files, remote_dir)
        
        # def run_lammps(input_file: str = "input.lammps", remote_dir: str = "lammps_run_test") -> str:
        #     return self.hpc_manager.run_lammps(input_file, remote_dir)
        
        # def download_results(remote_dir: str = "lammps_run_test", file_pattern: str = "*.dump *.log *.data") -> str:
        #     return self.hpc_manager.download_results(remote_dir, file_pattern)
        
        # def run_command(command: str) -> str:
        #     """Execute shell command in working directory."""
        #     import subprocess
        #     try:
        #         result = subprocess.run(
        #             command, shell=True, cwd=self.workdir,
        #             capture_output=True, text=True, timeout=120
        #         )
        #         output = f"Command: {command}\nExit code: {result.returncode}\n"
        #         if result.stdout:
        #             output += f"STDOUT:\n{result.stdout}\n"
        #         if result.stderr:
        #             output += f"STDERR:\n{result.stderr}\n"
        #         return output
        #     except Exception as e:
        #         return f"Command failed: {str(e)}"
        
        # def run_all_lammps_displacements(remote_dir: str = "lammps_run_test") -> str:
        #     return self.hpc_manager.run_all_lammps_displacements(remote_dir)
        
        # def run_lammps_local(input_file: str = "input.lammps", remote_dir: str = "lammps_run_test") -> str:
        #     return self.hpc_manager.run_lammps(input_file, remote_dir)
        
        def run_lammps_local(input_file: str = "input.lammps", remote_dir: str = "lammps_run_test") -> str:
            return self.local_run_manager.run_lammps_local(input_file, remote_dir)
       
        # def run_all_lammps_displacements_local(remote_dir: str = "lammps_run_test") -> str:
        #     return self.hpc_manager.run_all_lammps_displacements(remote_dir)
        def run_all_lammps_displacements_local(remote_dir: str = "lammps_run_test") -> str:
            return self.local_run_manager.run_all_lammps_displacements_local(remote_dir)

        # def download_force_dumps(remote_dir: str = "lammps_run_test") -> str:
        #     return self.hpc_manager.download_force_dumps(remote_dir)

        hpc_functions = [
            # (upload_files, "upload_files", "Upload files to Carbon HPC. Parameters: files (str, default '*'), remote_dir (str, default 'lammps_run_test')"),
            # (run_lammps, "run_lammps", "Run LAMMPS on Carbon. Parameters: input_file (str, default 'input.lammps'), remote_dir (str, default 'lammps_run_test')"),
            # (download_results, "download_results", "Download results from Carbon. Parameters: remote_dir (str, default 'lammps_run_test'), file_pattern (str, default '*.dump *.log *.data')"),
            # (run_command, "run_command", "Execute shell command. Parameter: command (str)"),
            # (run_all_lammps_displacements, "run_all_lammps_displacements", "Use it for phonon dispersion calculations. Runs all the LAMMPS calculations inside the displacements directory. Parameters: remote_dir (str, default 'lammps_run_test')"),
            (run_lammps_local, "run_lammps_local", "Run LAMMPS on local PC. Parameters: input_file (str, default 'input.lammps'), remote_dir (str, default 'lammps_run_test')"),
            (run_all_lammps_displacements_local, "run_all_lammps_displacements_local", "Runs on local PC. Use it for phonon dispersion calculations. Runs all the LAMMPS calculations inside the displacements directory. Parameters: remote_dir (str, default 'lammps_run_test')"),
            # (download_force_dumps, "download_force_dumps", "Use it for phonon dispersion calculations. Download force dumps from Carbon HPC. Parameters: remote_dir (str, default 'lammps_run_test')"),
        ]
        
        for func, name, description in hpc_functions:
            register_function(
                func,
                caller=self.hpc_agent,
                executor=self.lammps_admin,
                name=name,
                description=description,
            )

    # ==================== LOCAL RUN FUNCTIONS ====================
    # def register_local_lammps_run_functions(self):
    #     """Register functions for HPCExecutor agent."""
    #     print("Registering local LAMMPS functions...")
        
    #     def run_lammps_local(input_file: str = "input.lammps", remote_dir: str = "lammps_run_test") -> str:
    #         return self.local_run_manager.run_lammps(input_file, remote_dir)
        
       
    #     def run_all_lammps_displacements_local(remote_dir: str = "lammps_run_test") -> str:
    #         return self.local_run_manager.run_all_lammps_displacements(remote_dir)


    #     local_run_functions = [
    #         (run_lammps_local, "run_lammps_local", "Run LAMMPS on local PC. Parameters: input_file (str, default 'input.lammps'), remote_dir (str, default 'lammps_run_test')"),
    #         (run_all_lammps_displacements_local, "run_all_lammps_displacements_local", "Runs on local PC. Use it for phonon dispersion calculations. Runs all the LAMMPS calculations inside the displacements directory. Parameters: remote_dir (str, default 'lammps_run_test')"),
    #     ]
        
    #     for func, name, description in local_run_functions:
    #         register_function(
    #             func,
    #             caller=self.hpc_agent,
    #             executor=self.lammps_admin,
    #             name=name,
    #             description=description,
    #         )

    # ==================== ANALYSIS FUNCTIONS ====================

    def register_analysis_functions(self):
        """Register functions for ResultsAnalyzer agent with enhanced visualization and log analysis."""
        print("Registering analysis functions...")
        
        # Initialize VisualizationManager
        from src.tools.specialized_tools.visualization_manager import VisualizationManager  
        visualization_manager = VisualizationManager(self.workdir)
        
        def list_files() -> str:
            return self.file_manager.list_files()
        
        def run_command(command: str) -> str:
            """Execute shell command in working directory."""
            import subprocess
            try:
                result = subprocess.run(
                    command, shell=True, cwd=self.workdir,
                    capture_output=True, text=True, timeout=120
                )
                output = f"Command: {command}\nExit code: {result.returncode}\n"
                if result.stdout:
                    output += f"STDOUT:\n{result.stdout}\n"
                if result.stderr:
                    output += f"STDERR:\n{result.stderr}\n"
                return output
            except Exception as e:
                return f"Command failed: {str(e)}"
        
        def analyze_results() -> str:
            """Analyze LAMMPS output files with enhanced detection."""
            files_found = []
            analysis = "📊 COMPREHENSIVE RESULTS ANALYSIS:\n"
            
            # Check for different output files
            if os.path.exists(self.workdir):
                for file in os.listdir(self.workdir):
                    filepath = os.path.join(self.workdir, file)
                    if os.path.isfile(filepath):
                        size = os.path.getsize(filepath)
                        
                        if file.startswith('dump') or '.dump' in file:
                            files_found.append(f"  📄 {file} ({size} bytes) - Trajectory data")
                        elif file.startswith('log') or '.log' in file:
                            files_found.append(f"  📄 {file} ({size} bytes) - LAMMPS log")
                        elif file.endswith('.data'):
                            files_found.append(f"  📄 {file} ({size} bytes) - Structure data")
                        elif file.endswith(('.png', '.jpg', '.gif')):
                            files_found.append(f"  🖼️  {file} ({size} bytes) - Visualization")
                        elif file.endswith(('.lmp', '.lammps')):
                            files_found.append(f"  📄 {file} ({size} bytes) - LAMMPS input")
                        elif file.endswith(('.eam', '.sw', '.meam')):
                            files_found.append(f"  ⚛️  {file} ({size} bytes) - Potential file")
                        elif file.endswith('.out'):
                            files_found.append(f"  📄 {file} ({size} bytes) - Output file")
            
            if files_found:
                analysis += "\n".join(files_found)
            else:
                analysis += "  ⚠️  No output files found"
            
            return analysis
        
        def analyze_lammps_log(log_file: str = "log.lammps") -> str:
            """Analyze LAMMPS log file and extract key information."""
            import os
            import re
            
            log_path = os.path.join(self.workdir, log_file)
            
            if not os.path.exists(log_path):
                # Try to find any log file
                possible_logs = [f for f in os.listdir(self.workdir) if f.startswith('log') or '.log' in f]
                if possible_logs:
                    log_path = os.path.join(self.workdir, possible_logs[0])
                    log_file = possible_logs[0]
                else:
                    return f"❌ No log file found. Searched for: {log_file}"
            
            try:
                with open(log_path, 'r') as f:
                    content = f.read()
                
                analysis = f"📊 LAMMPS LOG ANALYSIS ({log_file}):\n"
                analysis += "="*50 + "\n"
                
                # Extract simulation info
                lines = content.split('\n')
                
                # Find simulation box info
                box_info = []
                for line in lines:
                    if 'orthogonal box' in line.lower():
                        box_info.append(line.strip())
                    elif 'lattice parameter' in line.lower():
                        box_info.append(line.strip())
                
                if box_info:
                    analysis += "📦 SIMULATION BOX:\n"
                    for info in box_info:
                        analysis += f"  {info}\n"
                    analysis += "\n"
                
                # Extract timestep information
                timestep_pattern = r'Step\s+(\d+)'
                timesteps = re.findall(timestep_pattern, content)
                if timesteps:
                    analysis += f"⏱️  TIMESTEPS: {timesteps[0]} → {timesteps[-1]} (Total: {len(timesteps)} steps)\n\n"
                
                # Extract energy information
                energy_lines = []
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['energy', 'potential', 'kinetic', 'total']):
                        if any(char.isdigit() for char in line):
                            energy_lines.append(line.strip())
                
                if energy_lines:
                    analysis += "⚡ ENERGY DATA:\n"
                    for energy_line in energy_lines[-5:]:  # Last 5 energy lines
                        analysis += f"  {energy_line}\n"
                    analysis += "\n"
                
                # Extract warnings and errors
                warnings = []
                errors = []
                for line in lines:
                    line_lower = line.lower()
                    if 'warning' in line_lower:
                        warnings.append(line.strip())
                    elif 'error' in line_lower or 'failed' in line_lower:
                        errors.append(line.strip())
                
                if warnings:
                    analysis += "⚠️  WARNINGS:\n"
                    for warning in warnings[-3:]:  # Last 3 warnings
                        analysis += f"  {warning}\n"
                    analysis += "\n"
                
                if errors:
                    analysis += "❌ ERRORS:\n"
                    for error in errors:
                        analysis += f"  {error}\n"
                    analysis += "\n"
                
                # Extract final status
                if 'Total wall time' in content:
                    wall_time_match = re.search(r'Total wall time:\s*([\d:]+)', content)
                    if wall_time_match:
                        analysis += f"✅ SIMULATION COMPLETED\n"
                        analysis += f"  Wall time: {wall_time_match.group(1)}\n"
                
                # File size
                file_size = os.path.getsize(log_path)
                analysis += f"\n📁 File size: {file_size} bytes ({file_size/1024:.1f} KB)"
                
                return analysis
                
            except Exception as e:
                return f"❌ Error analyzing log file: {str(e)}"


        def extract_lattice_constants(log_file: str = "log.lammps") -> str:
            """Extract lattice constants from a LAMMPS log file.

            1) Attempts to locate the very last “Step  Temp  PotEng  Lx  Ly  Lz  Cella  Cellb  Cellc  CellAlpha  CellBeta  CellGamma” table,
            and pulls out the last row after that header.
            2) If that fails, falls back to regex‐based searches (“lattice parameter”, “a = …”, etc.).
            """
            import os
            import re

            # 1) Locate the log file
            log_path = os.path.join(self.workdir, log_file)
            if not os.path.exists(log_path):
                possible_logs = [
                    f for f in os.listdir(self.workdir)
                    if f.startswith("log") or f.lower().endswith(".log")
                ]
                if possible_logs:
                    log_path = os.path.join(self.workdir, possible_logs[0])
                else:
                    return "❌ No log file found for lattice constant extraction"

            try:
                # 2) Read the file content (try multiple encodings)
                content = None
                for enc in ["utf-8", "latin-1", "cp1252", "ascii"]:
                    try:
                        with open(log_path, "r", encoding=enc) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue

                if content is None:
                    with open(log_path, "rb") as f:
                        raw = f.read()
                    content = raw.decode("utf-8", errors="ignore")

                # Prepare the results header
                results = "🔍 LATTICE CONSTANT EXTRACTION:\n" + ("=" * 40) + "\n"

                # 3) Split into lines and find ALL header occurrences
                lines = content.splitlines()
                header_pattern = re.compile(
                    r"\s*Step\s+Temp\s+PotEng\s+Lx\s+Ly\s+Lz\s+Cella\s+Cellb\s+Cellc", re.IGNORECASE
                )
                header_indices = [i for i, line in enumerate(lines) if header_pattern.match(line)]

                if header_indices:
                    # Choose the index of the LAST header
                    header_idx = header_indices[-1]

                    # Collect all non‐blank lines after that header
                    data_lines = []
                    for row in lines[header_idx + 1 :]:
                        if row.strip() == "":
                            break
                        data_lines.append(row)

                    if data_lines:
                        last_row_tokens = data_lines[-1].split()
                        # Expect at least 12 tokens:
                        # [0]=Step, [1]=Temp, [2]=PotEng, [3]=Lx, [4]=Ly, [5]=Lz,
                        # [6]=Cella, [7]=Cellb, [8]=Cellc, [9]=CellAlpha, [10]=CellBeta, [11]=CellGamma
                        if len(last_row_tokens) >= 12:
                            step, temp, poteng = last_row_tokens[0], last_row_tokens[1], last_row_tokens[2]
                            lx, ly, lz = last_row_tokens[3], last_row_tokens[4], last_row_tokens[5]
                            cella, cellb, cellc = last_row_tokens[6], last_row_tokens[7], last_row_tokens[8]
                            alpha, beta, gamma = last_row_tokens[9], last_row_tokens[10], last_row_tokens[11]

                            results += (
                                f"📋 Found final cell table at lines {header_idx+1}–{header_idx+1+len(data_lines)}:\n"
                                f"  Step={step}  Temp={temp}  PotEng={poteng}\n"
                                f"  Lx={lx}  Ly={ly}  Lz={lz}\n"
                                f"  Cella={cella} Å  Cellb={cellb} Å  Cellc={cellc} Å\n"
                                f"  CellAlpha={alpha}°  CellBeta={beta}°  CellGamma={gamma}°\n"
                            )
                            return results
                        else:
                            # Malformed row (too few columns)
                            results += (
                                "❗ The last table was found, but its final row has fewer than 12 columns. "
                                "Falling back to regex search.\n"
                            )
                    else:
                        # Header exists but no data lines after it
                        results += (
                            "❗ Header for the last cell table was found, but no rows followed. "
                            "Falling back to regex search.\n"
                        )
                else:
                    # No header found at all
                    results += "ℹ️ No final “Step … Cella … CellGamma” table detected. Falling back to regex.\n"

                # 4) REGEX‐BASED FALLBACK
                lattice_patterns = [
                    r"lattice\s+parameter[:\s]+([\d\.]+)",
                    r"a\s*=\s*([\d\.]+)",
                    r"lattice\s+constant[:\s]+([\d\.]+)",
                    r"cell\s+parameter[:\s]+([\d\.]+)",
                ]
                found_values = []
                for patt in lattice_patterns:
                    matches = re.findall(patt, content, re.IGNORECASE)
                    found_values.extend(matches)

                if found_values:
                    results += "\n📏 FOUND LATTICE PARAMETERS (regex‐based):\n"
                    for idx, val in enumerate(found_values, 1):
                        results += f"  Value {idx}: {val} Å\n"
                    if len(found_values) > 1:
                        avg = sum(float(v) for v in found_values) / len(found_values)
                        results += f"\n📊 Average: {avg:.4f} Å\n"
                else:
                    results += "\n❌ No explicit lattice constants found via regex.\n"
                    results += "💡 Suggest checking box dimensions or final coordinates manually.\n"

                return results

            except Exception as e:
                return f"❌ Error extracting lattice constants: {str(e)}"                   
        
        # OVITO Visualization Functions
        def visualize_dump_file(dump_file: str = "dump.output", output_image: str = "visualization.png", 
                            frame_number: str = "last") -> str:
            """Visualize LAMMPS dump file using OVITO."""
            return visualization_manager.render_lammps_dump(dump_file, output_image, frame_number)
        
        def create_animation(dump_file: str = "dump.output", output_gif: str = "animation.gif") -> str:
            """Create animation from LAMMPS dump file."""
            return visualization_manager.create_animation(dump_file, output_gif)
        
        def analyze_dump_structure(dump_file: str = "dump.output") -> str:
            """Analyze dump file structure and properties."""
            return visualization_manager.analyze_dump_file(dump_file)
        
        def render_multiple_frames(dump_file: str = "dump.output", frame_count: int = 5) -> str:
            """Render multiple frames from dump file."""
            return visualization_manager.render_multiple_frames(dump_file, frame_count)
        
        def find_and_analyze_all_outputs() -> str:
            """Find and analyze all LAMMPS output files in the working directory."""
            import os
            
            results = "🔍 COMPREHENSIVE OUTPUT ANALYSIS:\n"
            results += "="*50 + "\n"
            
            # Find all relevant files
            dump_files = [f for f in os.listdir(self.workdir) if f.startswith('dump') or '.dump' in f]
            log_files = [f for f in os.listdir(self.workdir) if f.startswith('log') or '.log' in f]
            data_files = [f for f in os.listdir(self.workdir) if f.endswith('.data')]
            
            # Analyze log files
            if log_files:
                results += f"\n📊 ANALYZING {len(log_files)} LOG FILE(S):\n"
                for log_file in log_files:
                    log_analysis = analyze_lammps_log(log_file)
                    results += f"\n{log_analysis}\n"
            
            # Analyze dump files
            if dump_files:
                results += f"\n📄 ANALYZING {len(dump_files)} DUMP FILE(S):\n"
                for dump_file in dump_files:
                    dump_analysis = analyze_dump_structure(dump_file)
                    results += f"\n{dump_analysis}\n"
            
            # Basic file summary
            results += f"\n📁 FILE SUMMARY:\n"
            results += f"  Log files: {len(log_files)}\n"
            results += f"  Dump files: {len(dump_files)}\n"
            results += f"  Data files: {len(data_files)}\n"
            
            return results
        
        def read_log_file(log_file: str = "log.lammps", max_lines: int = 500) -> str:
            """Read raw LAMMPS log file content for agent analysis."""
            import os
            
            log_path = os.path.join(self.workdir, log_file)
            
            if not os.path.exists(log_path):
                possible_logs = [f for f in os.listdir(self.workdir) if f.startswith('log') or '.log' in f]
                if possible_logs:
                    log_path = os.path.join(self.workdir, possible_logs[0])
                    log_file = possible_logs[0]
                else:
                    return f"❌ No log file found"
            
            try:
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                
                # Limit content to avoid overwhelming the LLM
                if len(lines) > max_lines:
                    content = ''.join(lines[-max_lines:])  # Last N lines
                    result = f"📄 LOG FILE CONTENT ({log_file}) - Last {max_lines} lines:\n"
                    result += "="*60 + "\n"
                    result += content
                    result += f"\n[File has {len(lines)} total lines, showing last {max_lines}]"
                else:
                    content = ''.join(lines)
                    result = f"📄 LOG FILE CONTENT ({log_file}) - Complete file:\n"
                    result += "="*60 + "\n"
                    result += content
                
                return result
                
            except Exception as e:
                return f"❌ Error reading log file: {str(e)}"

        def read_file_section(filename: str, start_line: int = 1, end_line: int = 100) -> str:
            """Read specific section of any file for detailed analysis."""
            import os
            
            filepath = os.path.join(self.workdir, filename)
            
            if not os.path.exists(filepath):
                return f"❌ File not found: {filename}"
            
            try:
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                
                # Convert to 0-based indexing
                start_idx = max(0, start_line - 1)
                end_idx = min(len(lines), end_line)
                
                content = ''.join(lines[start_idx:end_idx])
                
                result = f"📄 FILE SECTION ({filename}) - Lines {start_line} to {end_line}:\n"
                result += "="*50 + "\n"
                result += content
                result += f"\n[Total file lines: {len(lines)}]"
                
                return result
                
            except Exception as e:
                return f"❌ Error reading file section: {str(e)}"            
       
        # Register all analysis functions
        analysis_functions = [
            (list_files, "list_files", "List files in working directory with details"),
            (run_command, "run_command", "Execute shell command. Parameter: command (str)"),
            (analyze_results, "analyze_results", "Analyze LAMMPS output files in working directory"),
            (analyze_lammps_log, "analyze_lammps_log", "Analyze LAMMPS log file and extract key information. Parameters: log_file (str, default 'log.lammps')"),
            (extract_lattice_constants, "extract_lattice_constants", "Extract lattice constants from LAMMPS log file. Parameters: log_file (str, default 'log.lammps')"),
            (visualize_dump_file, "visualize_dump_file", "Visualize LAMMPS dump file using OVITO. Parameters: dump_file (str), output_image (str), frame_number (int, default 0)"),
            (create_animation, "create_animation", "Create animation from LAMMPS dump file. Parameters: dump_file (str), output_gif (str)"),
            (analyze_dump_structure, "analyze_dump_structure", "Analyze dump file structure and properties. Parameters: dump_file (str)"),
            (render_multiple_frames, "render_multiple_frames", "Render multiple frames from dump file. Parameters: dump_file (str), frame_count (int, default 5)"),
            (find_and_analyze_all_outputs, "find_and_analyze_all_outputs", "Find and analyze all LAMMPS output files in working directory"),
            (read_log_file, "read_log_file", "Read raw LAMMPS log file content. Parameters: log_file (str), max_lines (int, default 500)"),
            (read_file_section, "read_file_section", "Read specific section of any file. Parameters: filename (str), start_line (int, default 1), end_line (int, default 100)"),
        ]
        
        for func, name, description in analysis_functions:
            register_function(
                func,
                caller=self.analysis_agent,
                executor=self.lammps_admin,
                name=name,
                description=description,
            )


    # ==================== PHONOPY FUNCTIONS ====================
    def register_phonopy_functions(self):
        """Register functions for PhonopyCalculator agent."""
        print("  🌊 Registering phonopy functions...")
        
        def create_poscar_from_lmp(lmp_filename: str) -> str:
            return self.phonopy_manager.create_poscar_from_lmp(lmp_filename)
        
        def create_displacement_yaml(dim: str) -> str:
            return self.phonopy_manager.create_displacement_yaml(dim)
        
        def create_displacement_files() -> str:
            return self.phonopy_manager.create_displacement_files()
        

        def create_lammps_input_for_displacements(potential_file: str) -> str:
            return self.phonopy_manager.create_lammps_input_for_displacements(potential_file)

        def collect_forces_from_displacements() -> str:
            return self.phonopy_manager.collect_forces_from_displacements()
        

        def generate_band_conf_and_plot() -> str:
            return self.phonopy_manager.generate_band_conf_and_plot()
        
        phonopy_functions = [
            (create_poscar_from_lmp, "create_poscar_from_lmp", "Convert the structure file from atomsk to POSCAR format, lmp_filename (str, optional). Auto-detects file if not provided."),
            (create_displacement_yaml, "create_displacement_yaml", "Create displacement YAML file using phonopy and the existing POSCAR. Parameters: dim (str, optional)."),
            (create_displacement_files, "create_displacement_files", "Create displaced structures using phonopy and saves as POSCARs. Parameters: None - uses existing displacement YAML."),
            (create_lammps_input_for_displacements, "create_lammps_input_for_displacements", "Create LAMMPS input files for phonon displacements. Parameters: potential_file (str)."),
            (collect_forces_from_displacements, "collect_forces_from_displacements", "Collect forces from LAMMPS displacements and generates the FORCE_SETS file."),
            (generate_band_conf_and_plot, "generate_band_conf_and_plot", "Generate band structure configuration and plot. Parameterer: npoints(int, optional) ."),
        ]
        
        for func, name, description in phonopy_functions:
            register_function(
                func,
                caller=self.phonopy_agent,
                executor=self.lammps_admin,
                name=name,
                description=description,
            )
    
    # ==================== VALIDATION FUNCTIONS ====================
    def register_validation_functions(self):
        """Register validation and workflow control functions."""
        print("  ✅ Registering validation functions...")
        print(f"  🔍 ValidationManager available: {self.validation_manager is not None}")
        
        def validate_potential_file_wrapper(filepath: str, element: str) -> str:
            """Validate potential file using ValidationManager."""
            if self.validation_manager:
                try:
                    is_valid, message = self.validation_manager.validate_potential_file(filepath, element)
                    
                    # Update potential manager status
                    if hasattr(self.potential_manager, 'potential_validated'):
                        self.potential_manager.potential_validated = is_valid
                        if is_valid:
                            # Ensure we have the full path
                            if not os.path.isabs(filepath):
                                full_filepath = os.path.join(self.workdir, filepath)
                            else:
                                full_filepath = filepath
                            self.potential_manager.last_potential_file = full_filepath
                        else:
                            self.potential_manager.last_potential_file = None
                    
                    return f"Validation result: {message}"
                except Exception as e:
                    return f" Validation error: {str(e)}"
            return " ValidationManager not available"
        
        def download_from_url(url: str, filename: str) -> str:
            """Download potential file directly from URL provided by WebSurfer."""
            import urllib.request
            
            try:
                filepath = os.path.join(self.workdir, filename)
                urllib.request.urlretrieve(url, filepath)
                
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    return f" Downloaded {filename} from URL ({file_size} bytes)"
                else:
                    return f" Download failed - file not created"
                    
            except Exception as e:
                return f" Download error: {str(e)}"
        
        def verify_download_success(filepath: str, expected_element: str) -> str:
            """Verify that a file was actually downloaded and contains real data."""
            if self.validation_manager:
                try:
                    return self.validation_manager.verify_download_success(filepath, expected_element)
                except Exception as e:
                    return f" Verification error: {str(e)}"
            
            # Fallback verification
            return self._simple_file_verification(filepath)
        
        # Validation functions for the potential agent
        validation_functions = [
            (validate_potential_file_wrapper, "validate_potential_file", 
             "Validate potential file format and parameters. Parameters: filepath (str), element (str)"),
            (download_from_url, "download_from_url", "Download file from URL. "
            "Parameters: url (str), filename (str)"),
            (verify_download_success, "verify_download_success", 
             "Verify downloaded file is real (not dummy). Parameters: filepath (str), expected_element (str)"),
        ]
        
        for func, name, description in validation_functions:
            register_function(
                func,
                caller=self.potential_agent,
                executor=self.lammps_admin,
                name=name,
                description=description,
            )
    
    # ==================== HELPER METHODS ====================
    def _simple_file_verification(self, filepath: str) -> str:
        """Simple file verification when ValidationManager not available."""
        if not os.path.exists(filepath):
            return f" File does not exist: {filepath}"
        
        file_size = os.path.getsize(filepath)
        if file_size < 1000:
            return f" File too small ({file_size} bytes) - likely empty"
        
        return f" Basic verification passed ({file_size} bytes)"
    

    # ==================== ELASTIC CONSTANTS FUNCTIONS ====================
    def register_elastic_functions(self):
        """Register functions for LAMMPSElasticConstants agent."""
        print("  🔬 Registering elastic constants functions...")
        
        # Initialize the ElasticConstantsManager
        from src.tools.specialized_tools.elastic_constants_manager import ElasticConstantsManager
        elastic_manager = ElasticConstantsManager(self.workdir)
        
        # Wrapper functions that call the manager methods
        def setup_elastic_files(template_dir: str = None) -> str:
            return elastic_manager.setup_elastic_files(template_dir)
        
        def read_file_content(default_file: str) -> str:
            return elastic_manager.read_file_content(default_file)
        
        def save_file_content(default_file: str, content: str) -> str:
            return elastic_manager.save_file_content(default_file, content)
        
        # def set_strain_parameter(up_value: float) -> str:
        #     return elastic_manager.set_strain_parameter(up_value)
        
        def run_elastic_simulation() -> str:
            return elastic_manager.run_elastic_simulation(self.hpc_manager)
        
        # def extract_elastic_matrix(log_file: str = "log.lammps") -> str:
        #     return elastic_manager.extract_elastic_matrix(log_file)
        
        # def validate_elastic_matrix(tolerance: float = 0.05) -> str:
        #     return elastic_manager.validate_elastic_matrix(tolerance)
        
        # def visualize_elastic_results() -> str:
        #     return elastic_manager.visualize_elastic_results()
        
        # def complete_elastic_workflow(strain_param: float = 0.001, tolerance: float = 0.05, 
        #                             max_iterations: int = 3) -> str:
        #     return elastic_manager.complete_elastic_workflow(strain_param, tolerance, max_iterations, self.hpc_manager)
        
        def list_elastic_files() -> str:
            return elastic_manager.list_elastic_files()
        
        # Register all elastic functions
        elastic_functions = [
            (setup_elastic_files, "setup_elastic_files", "Setup standardized files for elastic calculations. Parameters: template_dir (str, optional)"),
            (read_file_content, "read_file_content", "Reads potential.mod and updates with correct potential. Parameters: potential_file (str)"),
            (save_file_content, "save_file_content", "Saves the updated potential.mod. Parameters: potential_file (str)"),
            # (set_strain_parameter, "set_strain_parameter", "Set strain parameter for elastic calculations. Parameters: up_value (float)"),
            (run_elastic_simulation, "run_elastic_simulation", "Run LAMMPS elastic simulation on HPC. No parameters required."),
            # (extract_elastic_matrix, "extract_elastic_matrix", "Extract 6x6 elastic constants matrix from log file. Parameters: log_file (str, default 'log.lammps')"),
            # (validate_elastic_matrix, "validate_elastic_matrix", "Validate elastic matrix for consistency. Parameters: tolerance (float, default 0.05)"),
            # (visualize_elastic_results, "visualize_elastic_results", "Create visualization of elastic constants. No parameters required."),
            # (complete_elastic_workflow, "complete_elastic_workflow", "Complete elastic workflow with automatic parameter adjustment. Parameters: strain_param (float, default 0.001), tolerance (float, default 0.05), max_iterations (int, default 3)"),
            (list_elastic_files, "list_elastic_files", "List all elastic calculation files in working directory. No parameters required."),
        ]
        
        for func, name, description in elastic_functions:
            register_function(
                func,
                caller=self.lammps_elastic_agent,
                executor=self.lammps_admin,
                name=name,
                description=description,
            )

    # ==================== MELTING POINT FUNCTIONS ====================
    def register_melting_point_visualization_functions(self):
        """Register functions for ResultsAnalyzer agent."""
        print("Registering melting point visualization functions...")

        # Initialize managers
        from src.tools.specialized_tools.vision_manager import VisionManager
        from src.tools.specialized_tools.melting_point_manager import MeltingPointsManager
        
        vision_manager = VisionManager(self.workdir)
        melting_point_manager = MeltingPointsManager(self.workdir)

        # Create wrapper functions that use the manager
        def analyze_melting_point_simulation(image_path: str) -> str:
            """Simple image analysis for simulation termination decision."""
            return vision_manager.analyze_melting_point_simulation(image_path)

        def analyze_solid_liquid_interface(image_path: str) -> str:
            """Simple image analysis for deciding if an interface is 50:50 solid liquid."""
            return vision_manager.analyze_solid_liquid_interface(image_path)
        
        def analyze_melting_point_plots(image_path: str) -> str:
            """Plot analysis for deciding in the melting point simulation was successful."""
            return vision_manager.analyze_melting_point_plots(image_path)

        def list_images(image_path: str) -> str:
            """List all images in working directory."""
            return vision_manager.list_images_in_workdir()

        def visualize_melting_point_results(system_info: str) -> str:
            return melting_point_manager.visualize_melting_point_results(system_info)        
    
        melting_analysis_functions = [
            (list_images, "list_images_in_workdir", "List all image files in working directory. No parameters required."),
            (analyze_solid_liquid_interface, "analyze_solid_liquid_interface", "Analyzes the ovito frame image to understand if a 50:50 solid liquid interface exists. Parameters: image_path (str)"),
            (analyze_melting_point_simulation, "analyze_melting_point_simulation", "Analyzes the final ovito frame image to understand if the structure is fully melted. Parameters: image_path (str)"),
            (visualize_melting_point_results, "visualize_melting_point_results", "Creates the analysis plots for the melting point calculation. Parameters: output_file (str)"),
            (analyze_melting_point_plots, "analyze_melting_point_plots", "Analyzes the plots of the melting point calculation and decides whether the calculation is complete. Parameters: image_path (str)"),
        ]
        for func, name, description in melting_analysis_functions:
            register_function(
                func,
                caller=self.analysis_agent,
                executor=self.lammps_admin,
                name=name,
                description=description,
            )


    # def register_melting_point_visualization_functions(self):
    #     """Register functions for ResultsAnalyzer agent."""
    #     print("Registering melting point visualization functions...")

    #     import asyncio, os, time, pathlib, uuid
    #     from typing import Optional, Callable
    #     import concurrent.futures

    #     from src.tools.specialized_tools.vision_manager import VisionManager
    #     from src.tools.specialized_tools.melting_point_manager import MeltingPointsManager

    #     # --- instance state
    #     self._mp_tasks = getattr(self, "_mp_tasks", {})
    #     self._mp_stop_events = getattr(self, "_mp_stop_events", {})
    #     self._mp_last_result = getattr(self, "_mp_last_result", None)
    #     # Add thread pool for async operations
    #     self._mp_executor = getattr(self, "_mp_executor", concurrent.futures.ThreadPoolExecutor(max_workers=2))

    #     vision_manager = VisionManager(self.workdir)
    #     melting_point_manager = MeltingPointsManager(self.workdir)

    #     # ----------------- helpers -----------------
    #     from datetime import datetime

    #     def _now_iso():
    #         return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

    #     def _ensure_dir(p: str) -> str:
    #         pathlib.Path(p).mkdir(parents=True, exist_ok=True)
    #         return p

    #     # REMOVED: _schedule_coro function - it was overly complex and unused

    #     async def _render_frame_from_dump(dump_path: str, frames_dir: str) -> Optional[str]:
    #         """
    #         Create/overwrite a frame image from the current state of dump.output.
    #         Returns the path to the image or None if nothing could be rendered.
    #         """
    #         os.makedirs(frames_dir, exist_ok=True)

    #         out_png = os.path.join(frames_dir, f"frame_{_now_iso()}.png")
    #         try:
    #             result_path = await asyncio.to_thread(
    #                 melting_point_manager.render_frame_from_dump, dump_path, out_png
    #             )
    #             return result_path if os.path.exists(result_path) else (out_png if os.path.exists(out_png) else None)
    #         except Exception as e:
    #             print(f"Error rendering frame: {e}")
    #             return None

    #     def _is_fully_melted(analysis_text: str) -> bool:
    #         """
    #         Heuristic stop signal from your analyzer.
    #         Adjust to your analyzer's wording/return format.
    #         """
    #         text = (analysis_text or "").lower()
    #         keywords = [
    #             "fully melted", "complete melt", "structure is fully melted",
    #             "no crystalline peaks", "terminated: full melt"
    #         ]
    #         return any(k in text for k in keywords)

    #     async def _stop_simulation(job_id: Optional[str]) -> str:
    #         """
    #         Implement actual stop logic. Three common options:
    #         1) Call your LAMMPS admin agent/tool to cancel the job by id.
    #         2) Touch a sentinel file your simulation loop watches to exit cleanly.
    #         3) Run a queue command (scancel, qdel) via your job controller.
    #         """
    #         try:
    #             if hasattr(self, "lammps_admin") and hasattr(self.lammps_admin, "cancel_job"):
    #                 # If you have a direct method:
    #                 return await asyncio.to_thread(self.lammps_admin.cancel_job, job_id)
    #             # Fallback: call a manager hook if you have one:
    #             if hasattr(melting_point_manager, "stop_active_simulation"):
    #                 return await asyncio.to_thread(melting_point_manager.stop_active_simulation, job_id)
    #             return f"No stop method wired; please implement _stop_simulation for job_id={job_id!r}"
    #         except Exception as e:
    #             return f"Error while stopping simulation: {e}"

    #     # ----------------- the monitor (runs in parallel) -----------------
    #     async def start_dump_monitor(
    #         dump_path: str,
    #         frames_dir: str,
    #         interval_sec: float = 60.0,   # one frame per minute
    #         job_id: Optional[str] = None, # pass your scheduler/job id if you have one
    #         task_id: str = "mp_dump_monitor",
    #         stop_on_full_melt: bool = True,
    #     ) -> str:
    #         """
    #         Continuously: (1) read dump.output, (2) render a frame, (3) analyze the image,
    #         (4) if 'full melt' detected, stop the simulation and halt the monitor.
    #         """

    #         if task_id in self._mp_tasks and not self._mp_tasks[task_id].done():
    #             return f"Monitor '{task_id}' already running."

    #         dump_path = os.path.abspath(dump_path)
    #         frames_dir = _ensure_dir(os.path.abspath(frames_dir))
    #         stop_event = asyncio.Event()
    #         self._mp_stop_events[task_id] = stop_event

    #         async def _runner():
    #             # debounce: only stop once
    #             stopped = False
    #             while not stop_event.is_set():
    #                 try:
    #                     if not os.path.exists(dump_path):
    #                         # dump doesn't exist yet; wait and retry
    #                         await asyncio.sleep(interval_sec)
    #                         continue

    #                     # 1) Render frame from current dump
    #                     frame_path = await _render_frame_from_dump(dump_path, frames_dir)
    #                     if frame_path and os.path.exists(frame_path):
    #                         # 2) Analyze frame
    #                         analysis = await asyncio.to_thread(
    #                             vision_manager.analyze_melting_point_simulation, frame_path
    #                         )
    #                         # record the last result
    #                         self._mp_last_result = {
    #                             "timestamp": time.time(),
    #                             "frame": frame_path,
    #                             "result": analysis,
    #                         }

    #                         # 3) Decide stop
    #                         if stop_on_full_melt and _is_fully_melted(analysis) and not stopped:
    #                             stopped = True
    #                             stop_msg = await _stop_simulation(job_id)
    #                             self._mp_last_result["stop_action"] = stop_msg
    #                             # after stopping sim, we can end monitor loop
    #                             stop_event.set()
    #                             break

    #                     # 4) sleep until next interval
    #                     await asyncio.sleep(interval_sec)

    #                 except Exception as e:
    #                     # keep monitor alive but record error
    #                     self._mp_last_result = {
    #                         "timestamp": time.time(),
    #                         "frame": None,
    #                         "result": f"Monitor error: {e}",
    #                     }
    #                     await asyncio.sleep(max(5.0, interval_sec))

    #         task = asyncio.create_task(_runner(), name=f"mp:{task_id}")
    #         self._mp_tasks[task_id] = task
    #         return (
    #             f"Started dump monitor '{task_id}' watching '{dump_path}', "
    #             f"writing frames to '{frames_dir}', every {interval_sec:.0f}s."
    #         )

    #     # FIXED: Make this a sync function that properly handles the async task
    #     def stop_dump_monitor_sync(task_id: str = "mp_dump_monitor") -> str:
    #         """Sync wrapper for stopping the dump monitor."""
    #         stop_event = self._mp_stop_events.get(task_id)
    #         task = self._mp_tasks.get(task_id)
    #         if not stop_event or not task:
    #             return f"No running monitor found for '{task_id}'."
            
    #         # Set the stop event - the task will clean itself up
    #         stop_event.set()
    #         return f"Stop signal sent to monitor '{task_id}'."

    #     # FIXED: Proper async task scheduling
    #     def start_dump_monitor_tool(
    #         dump_path: str,
    #         frames_dir: str,
    #         interval_sec: float = 60.0,
    #         job_id: str | None = None,
    #         task_id: str = "mp_dump_monitor",
    #         stop_on_full_melt: bool = True,
    #     ) -> str:
    #         """Sync shim that actually starts the async monitor in the background."""
    #         try:
    #             # Try to get the current running loop
    #             loop = asyncio.get_running_loop()
    #             # Schedule the coroutine in the current loop
    #             loop.create_task(
    #                 start_dump_monitor(
    #                     dump_path=dump_path,
    #                     frames_dir=frames_dir,
    #                     interval_sec=interval_sec,
    #                     job_id=job_id,
    #                     task_id=task_id,
    #                     stop_on_full_melt=stop_on_full_melt,
    #                 )
    #             )
    #         except RuntimeError:
    #             # No running loop - create a new one
    #             # This is less ideal but handles edge cases
    #             try:
    #                 loop = asyncio.new_event_loop()
    #                 asyncio.set_event_loop(loop)
    #                 loop.create_task(
    #                     start_dump_monitor(
    #                         dump_path=dump_path,
    #                         frames_dir=frames_dir,
    #                         interval_sec=interval_sec,
    #                         job_id=job_id,
    #                         task_id=task_id,
    #                         stop_on_full_melt=stop_on_full_melt,
    #                     )
    #                 )
    #                 # Start the loop in a separate thread to avoid blocking
    #                 import threading
    #                 def run_loop():
    #                     loop.run_forever()
    #                 thread = threading.Thread(target=run_loop, daemon=True)
    #                 thread.start()
    #             except Exception as e:
    #                 return f"Failed to start monitor: {e}"
            
    #         return (f"Starting dump monitor '{task_id}' on '{os.path.abspath(dump_path)}' "
    #                 f"-> frames '{os.path.abspath(frames_dir)}' every {int(interval_sec)}s.")

    #     def dump_monitor_status(task_id: str = "mp_dump_monitor") -> str:
    #         task = self._mp_tasks.get(task_id)
    #         running = task is not None and not task.done()
            
    #         # Clean up completed tasks
    #         if task and task.done():
    #             self._mp_tasks.pop(task_id, None)
    #             self._mp_stop_events.pop(task_id, None)
                
    #         return {
    #             "running": running,
    #             "task_exists": task is not None,
    #             "last_result": self._mp_last_result,
    #         }.__repr__()

    #     # ----------------- your existing tools (unchanged) -----------------
    #     def analyze_solid_liquid_interface(image_path: str) -> str:
    #         return vision_manager.analyze_solid_liquid_interface(image_path)

    #     def analyze_melting_point_plots(image_path: str) -> str:
    #         return vision_manager.analyze_melting_point_plots(image_path)

    #     def list_images(_: str = "") -> str:
    #         return vision_manager.list_images_in_workdir()

    #     def visualize_melting_point_results(system_info: str) -> str:
    #         return melting_point_manager.visualize_melting_point_results(system_info)

    #     # ADDED: Cleanup function for when the class is destroyed
    #     def cleanup_monitors() -> str:
    #         """Clean up all running monitors and thread pools."""
    #         count = 0
    #         for task_id, stop_event in list(self._mp_stop_events.items()):
    #             stop_event.set()
    #             count += 1
            
    #         if hasattr(self, '_mp_executor'):
    #             self._mp_executor.shutdown(wait=False)
                
    #         return f"Cleaned up {count} monitors and thread pool."

    #     # ----------------- Register all tools -----------------
    #     melting_analysis_functions = [
    #         # Monitor controls
    #         (start_dump_monitor_tool, "start_dump_monitor",
    #         "Start continuous monitoring of dump.output, render a frame every interval, analyze, and auto-stop on full melt. "
    #         "Parameters: dump_path (str), frames_dir (str), interval_sec (float=60), job_id (str|None), task_id (str='mp_dump_monitor'), stop_on_full_melt (bool=True)"),
    #         (stop_dump_monitor_sync, "stop_dump_monitor",  # FIXED: Use sync version
    #         "Stop the dump monitor. Parameters: task_id (str='mp_dump_monitor')"),
    #         (dump_monitor_status, "dump_monitor_status",
    #         "Get monitor running state and last analysis. Parameters: task_id (str='mp_dump_monitor')"),
    #         (cleanup_monitors, "cleanup_monitors",
    #         "Clean up all running monitors. No parameters."),

    #         # Existing utilities
    #         (analyze_solid_liquid_interface, "analyze_solid_liquid_interface",
    #         "Analyzes if a 50:50 solid-liquid interface exists. Parameters: image_path (str)"),
    #         (analyze_melting_point_plots, "analyze_melting_point_plots",
    #         "Analyzes melting point plots for completion. Parameters: image_path (str)"),
    #         (list_images, "list_images_in_workdir",
    #         "List all image files in working directory. No parameters."),
    #         (visualize_melting_point_results, "visualize_melting_point_results",
    #         "Creates analysis plots for the melting point calculation. Parameters: system_info (str)"),
    #     ]

    #     for func, name, description in melting_analysis_functions:
    #         register_function(
    #             func,
    #             caller=self.analysis_agent,
    #             executor=self.lammps_admin,
    #             name=name,
    #             description=description,
    #         )
