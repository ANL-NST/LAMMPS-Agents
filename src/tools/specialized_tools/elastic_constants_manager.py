import os
import shutil
import re
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging


class ElasticConstantsManager:
    """
    Manager for LAMMPS elastic constants calculations.
    Contains functions to enable the simulations correctly
    """
    
    def __init__(self, work_dir: str, template_dir: str = None):
        """
        Initialize the ElasticConstantsManager.
        
        Args:
            work_dir: Working directory for calculations
            template_dir: Directory containing template files provided 
            in the LAMMPS github page: https://github.com/lammps/lammps/tree/develop/examples/ELASTIC
        """
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(exist_ok=True)
        
        if template_dir is None:
            template_dir = "src/tools/default_files"
        
        self.template_dir = Path(template_dir)
        self.logger = self._setup_logging()
        
        # Default parameters
        self.default_strain_range = (0.0001, 0.001, 0.01)
        self.max_iterations = 3
        
        # Required template files
        self.required_files = ['in.elastic', 'potential.mod', 'displace.mod', 'init.mod']
    
    def _setup_logging(self):
        """Set up logging for the manager"""
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)


    def setup_elastic_files(self, template_dir: str = None) -> str:
        """
        Step 1: Add standardized files for elastic calculations to working directory.
        
        Args:
            template_dir: Directory containing template files (optional, uses default if None)
        
        Returns:
            str: Success/failure message
        """
        try:
            if template_dir is not None:
                template_path = Path(template_dir)
            else:
                template_path = self.template_dir
            
            results = "SETTING UP ELASTIC CALCULATION FILES:\n"
            results += "="*50 + "\n"
            results += f"Template directory: {template_path}\n"
            results += f"Working directory: {self.work_dir}\n\n"
            
            copied_count = 0
            for file_name in self.required_files:
                src_file = template_path / file_name
                dst_file = self.work_dir / file_name
                
                if src_file.exists():
                    shutil.copy2(src_file, dst_file)
                    results += f"Copied {file_name} to working directory\n"
                    copied_count += 1
                else:
                    results += f"Template file {file_name} not found in {template_path}\n"
            
            if copied_count == len(self.required_files):
                results += f"\nSuccessfully set up all {copied_count} elastic calculation files"
            else:
                results += f"\nSet up {copied_count}/{len(self.required_files)} files - some templates missing"
            
            return results
            
        except Exception as e:
            error_msg = f"Error setting up elastic files: {str(e)}"
            self.logger.error(error_msg)
            return error_msg

    # Reads the last lines of the output file of the LAMMPS simulation
    def read_file_content(self,filename: str) -> str:
        from collections import deque
        """Read any file content for LLM analysis. Returns only the last 200 lines where are the results in the log.lammps file"""
        filepath = self.work_dir / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                last_200_lines = deque(f, maxlen=200)
 
                for line in last_200_lines:
                    print(line, end='')
                return f"Content of {filename}:\n" + ''.join(last_200_lines)
    
        return f"File {filename} not found"

    def save_file_content(self,filename: str, content: str) -> str:
        """Save content to file."""
        filepath = self.work_dir / filename
        with open(filepath, 'w') as f:
            f.write(content)
        return f"Saved {filename}"

    # SET STRAIN PARAMETER
    def set_strain_parameter(self, up_value: float) -> str:
        """
        Step 3: Set the 'variable up equal' parameter for strain calculations.
        
        Args:
            up_value: Strain parameter value (typically 0.0001 to 0.01)
        
        Returns:
            str: Success/failure message
        """
        try:
            elastic_input_path = self.work_dir / 'in.elastic'
            
            if not elastic_input_path.exists():
                return f" in.elastic file not found in {self.work_dir}"
            
            # Validate strain parameter range
            if not (self.default_strain_range[0] <= up_value <= self.default_strain_range[1]):
                self.logger.warning(f"Strain parameter {up_value} outside recommended range {self.default_strain_range}")
            
            # Read the elastic input file
            with open(elastic_input_path, 'r') as f:
                content = f.read()
            
            # Replace the strain parameter
            patterns = [
                r'(variable\s+up\s+equal\s+)[\d.eE+-]+',
                r'(variable\s+up\s+equal\s+)\$\{UP\}',
                r'(variable\s+up\s+equal\s+)UP_VALUE'
            ]
            
            replacement = f'variable up equal {up_value}'
            modified = False
            
            for pattern in patterns:
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    modified = True
                    break
            
            if not modified:
                lines = content.split('\n')
                insert_pos = 0
                
                for i, line in enumerate(lines):
                    if line.strip().startswith('variable') or line.strip().startswith('#'):
                        insert_pos = i + 1
                    elif line.strip() and not line.strip().startswith('#'):
                        break
                
                lines.insert(insert_pos, f"\n{replacement}")
                content = '\n'.join(lines)
            
            with open(elastic_input_path, 'w') as f:
                f.write(content)
            
            result = f"Set strain parameter: variable up equal {up_value}"
            self.logger.info(result)
            return result
            
        except Exception as e:
            error_msg = f"Error setting strain parameter: {str(e)}"
            self.logger.error(error_msg)
            return error_msg

    # RUN SIMULATION
    def run_elastic_simulation(self, hpc_manager) -> str:
        """
        Step 4: Run the LAMMPS simulation with in.elastic file on HPC.
        
        Args:
            hpc_manager: HPC manager instance for running simulations
        
        Returns:
            str: Simulation result message
        """
        try:
            results = " ELASTIC SIMULATION EXECUTION:\n"
            results += "="*40 + "\n"
            
            self.logger.info("Uploading files to HPC...")
            upload_result = hpc_manager.upload_files("*", "lammps_run_test")
            results += f" Upload: {upload_result}\n"
            
            self.logger.info("Running LAMMPS elastic simulation...")
            run_result = hpc_manager.run_lammps("in.elastic", "lammps_run_test")
            results += f" Execution: {run_result}\n"
            
            # Download results
            self.logger.info("Downloading results...")
            download_result = hpc_manager.download_results("lammps_run_test", "*.log *.out *.dump")
            results += f"Download: {download_result}\n"
            
            results += "\n Elastic simulation workflow completed"
            return results
            
        except Exception as e:
            error_msg = f"Error running elastic simulation: {str(e)}"
            self.logger.error(error_msg)
            return error_msg


    def visualize_elastic_results(self) -> str:
        """
        Step 7: Create visualization of elastic constants results.
        
        Returns:
            str: Visualization creation result
        """
        try:
            matrix_file = self.work_dir / 'elastic_matrix.txt'
            
            if not matrix_file.exists():
                return "Elastic matrix file not found. Create the elastic_matrix.txt first."
            
            matrix = np.loadtxt(matrix_file)

            fig, ax = plt.subplots(figsize=(8, 8))
            
            # Main plot: Heatmap
            mask = matrix == 0  # Mask zero elements
            sns.heatmap(matrix, annot=True, fmt='.1f', cmap='viridis', 
                       xticklabels=[f'C{i+1}' for i in range(6)],
                       yticklabels=[f'C{i+1}' for i in range(6)],
                       mask=mask, ax=ax, cbar_kws={'label': 'GPa'})
            ax.set_title('Elastic Constants Matrix (GPa)')
   
            plt.tight_layout()
            
            # Save plot
            output_file = self.work_dir / 'elastic_constants_visualization.png'
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            results = "ELASTIC CONSTANTS MATRIX VISUALIZATION:\n"
            self.logger.info("Successfully created elastic constants matrix")
            return results
            
        except Exception as e:
            error_msg = f"Error creating visualization: {str(e)}"
            self.logger.error(error_msg)
            return error_msg

    # ==================== HELPER METHODS ====================
    def _get_current_strain_parameter(self) -> Optional[float]:
        """Get current strain parameter from in.elastic file."""
        try:
            elastic_input_path = self.work_dir / 'in.elastic'
            if not elastic_input_path.exists():
                return None
            
            with open(elastic_input_path, 'r') as f:
                content = f.read()
            
            pattern = r'variable\s+up\s+equal\s+([\d.eE+-]+)'
            match = re.search(pattern, content)
            
            if match:
                return float(match.group(1))
            
            return None
            
        except Exception:
            return None
    
    def list_elastic_files(self) -> str:
        """List all elastic-related files in working directory."""
        try:
            results = "ELASTIC CALCULATION FILES:\n"
            results += "="*35 + "\n"
            
            elastic_files = {
                'Template files': ['in.elastic', 'potential.mod', 'displace.mod', 'init.mod'],
                'Result files': ['elastic_matrix.txt', 'elastic_constants_visualization.png'],
                'Log files': ['log.lammps', 'log.elastic']
            }
            
            for category, filenames in elastic_files.items():
                results += f"\n{category}:\n"
                for filename in filenames:
                    filepath = self.work_dir / filename
                    if filepath.exists():
                        size = filepath.stat().st_size
                        results += f" {filename} ({size} bytes)\n"
                    else:
                        results += f"  {filename} (not found)\n"
            
            return results
            
        except Exception as e:
            return f"Error listing files: {str(e)}"