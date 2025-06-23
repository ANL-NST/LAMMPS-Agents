import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, Optional
import logging
from scipy.signal import savgol_filter
from scipy.stats import linregress


class MeltingPointsManager:
    """
    Manager for LAMMPS melting points calculations.
    Contains functions to visualize the results
    """
    
    def __init__(self, work_dir: str):
        """
        Initialize the MeltingPointsManager.
        
        Args:
            work_dir: Working directory for calculations
        """
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(exist_ok=True)
        
        self.logger = self._setup_logging()
        
        # Required template files
        self.required_files = ['lammps.out', 'log.lammps']
    
    def _setup_logging(self):
        """Set up logging for the manager"""
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def parse_lammps_output(self, filename: str) -> Optional[Dict]:
        """Parse LAMMPS output and adapt to variable column lengths."""
        
        if not os.path.exists(filename):
            self.logger.error(f"File '{filename}' not found!")
            return None

        with open(filename, 'r') as f:
            lines = f.readlines()

        data_lines = []
        in_data_section = False
        header_found = False

        for line in lines:
            line = line.strip()
            if ('Step' in line and 'Temp' in line):
                in_data_section = True
                header_found = True
                continue
            if any(k in line for k in ['Loop time', 'Performance:', 'MPI task timing']):
                in_data_section = False
                continue
            if not in_data_section or not line:
                continue

            values = line.split()
            try:
                step = float(values[0])
                temp = float(values[1])
                pot_eng = float(values[2]) if len(values) > 2 else 0.0
                tot_eng = float(values[3]) if len(values) > 3 else pot_eng
                volume = float(values[4]) if len(values) > 4 else 0.0

                data_lines.append([step, temp, pot_eng, 0.0, tot_eng, 0.0, volume])
            except (ValueError, IndexError):
                continue

        if not header_found or len(data_lines) == 0:
            self.logger.error("No valid data found in the file.")
            return None

        data = np.array(data_lines)

        return {
            'step': data[:, 0],
            'temperature': data[:, 1],
            'pair_energy': data[:, 2],
            'molecular_energy': data[:, 3],
            'total_energy': data[:, 4],
            'pressure': data[:, 5],
            'volume': data[:, 6],
        }


    def analyze_melting_behavior(self, temperature, volume, energy, pressure):
        """
        General melting analysis for any system (bulk, nanoparticle, etc.)
        """
        results = {}
        
        # Sort data by temperature
        sort_idx = np.argsort(temperature)
        temp_sorted = temperature[sort_idx]
        vol_sorted = volume[sort_idx]
        eng_sorted = energy[sort_idx]
        press_sorted = pressure[sort_idx]
        
        # 1. Running average analysis (reduces NPT fluctuations)
        window_size = max(10, len(temp_sorted) // 20)
        
        def running_average(x, window):
            return np.convolve(x, np.ones(window)/window, mode='valid')
        
        if len(temp_sorted) > window_size:
            temp_avg = running_average(temp_sorted, window_size)
            vol_avg = running_average(vol_sorted, window_size)
            eng_avg = running_average(eng_sorted, window_size)
            press_avg = running_average(press_sorted, window_size)
            
            # Adjust temperature array to match averaged data
            temp_avg = temp_avg[:(len(vol_avg))]
            
            results['smoothed_data'] = {
                'temperature': temp_avg,
                'volume': vol_avg,
                'energy': eng_avg,
                'pressure': press_avg
            }
        
        # 2. Linear thermal expansion analysis (only meaningful if volume changes)
        # Fit linear expansion in low temperature region (before melting)
        volume_variation = (vol_sorted.max() - vol_sorted.min()) / vol_sorted.mean()
        
        if volume_variation > 0.001:  
            low_temp_mask = temp_sorted < np.percentile(temp_sorted, 60) 
            if np.sum(low_temp_mask) > 10:
                slope, intercept, r_value, _, _ = linregress(temp_sorted[low_temp_mask], 
                                                           vol_sorted[low_temp_mask])
                results['linear_expansion'] = {
                    'slope': slope,
                    'intercept': intercept,
                    'r_squared': r_value**2
                }
                
                # Calculate expected volume from linear expansion
                vol_expected = slope * temp_sorted + intercept
                vol_deviation = vol_sorted - vol_expected
                
                # Find where volume significantly deviates from linear expansion
                deviation_threshold = 2 * np.std(vol_deviation[:np.sum(low_temp_mask)])
                significant_deviation = np.where(vol_deviation > deviation_threshold)[0]
                
                if len(significant_deviation) > 0:
                    melting_idx = significant_deviation[0]
                    results['melting_temp_deviation'] = temp_sorted[melting_idx]
        else:
            # Volume is essentially constant (NVT simulation)
            results['volume_constant'] = True
        
        # 3. Energy-based analysis (more reliable for nanoparticles)
        # Look for heat capacity peak using binned analysis
        n_bins = min(50, len(temp_sorted) // 10)
        temp_bins = np.linspace(temp_sorted.min(), temp_sorted.max(), n_bins)
        energy_binned = []
        temp_binned = []
        
        for i in range(len(temp_bins)-1):
            mask = (temp_sorted >= temp_bins[i]) & (temp_sorted < temp_bins[i+1])
            if np.sum(mask) > 0:
                energy_binned.append(np.mean(eng_sorted[mask]))
                temp_binned.append(np.mean(temp_sorted[mask]))
        
        if len(energy_binned) > 5:
            energy_binned = np.array(energy_binned)
            temp_binned = np.array(temp_binned)
            
            # Calculate heat capacity from binned data
            dE = np.gradient(energy_binned)
            dT = np.gradient(temp_binned)
            heat_cap_binned = dE / dT
            
            # Find peak in heat capacity
            if len(heat_cap_binned) > 3:
                # Smooth heat capacity
                if len(heat_cap_binned) > 7:
                    heat_cap_smooth = savgol_filter(heat_cap_binned, 7, 3)
                else:
                    heat_cap_smooth = heat_cap_binned
                    
                peak_idx = np.argmax(heat_cap_smooth)
                results['melting_temp_heat_capacity'] = temp_binned[peak_idx]
                
                results['binned_analysis'] = {
                    'temperature': temp_binned,
                    'energy': energy_binned,
                    'heat_capacity': heat_cap_smooth
                }
        
        # 4. Pressure fluctuation analysis (only if pressure data available)
        # Melting often corresponds to increased pressure fluctuations
        if np.any(press_sorted != 0) and np.std(press_sorted) > 1e-6:
            temp_windows = np.linspace(temp_sorted.min(), temp_sorted.max(), 20)
            pressure_std = []
            temp_window_centers = []
            
            for i in range(len(temp_windows)-1):
                mask = (temp_sorted >= temp_windows[i]) & (temp_sorted < temp_windows[i+1])
                if np.sum(mask) > 5:
                    pressure_std.append(np.std(press_sorted[mask]))
                    temp_window_centers.append((temp_windows[i] + temp_windows[i+1]) / 2)
            
            if len(pressure_std) > 3:
                pressure_std = np.array(pressure_std)
                temp_window_centers = np.array(temp_window_centers)
                
                # Find temperature where pressure fluctuations increase significantly
                if len(pressure_std) > 5:
                    pressure_smooth = savgol_filter(pressure_std, 5, 2)
                else:
                    pressure_smooth = pressure_std
                    
                # Look for significant increase in pressure fluctuations
                baseline_std = np.mean(pressure_smooth[:len(pressure_smooth)//3])
                significant_increase = pressure_smooth > 2 * baseline_std
                
                if np.any(significant_increase):
                    first_increase_idx = np.where(significant_increase)[0][0]
                    results['melting_temp_pressure_fluctuations'] = temp_window_centers[first_increase_idx]
                
                results['pressure_analysis'] = {
                    'temperature': temp_window_centers,
                    'pressure_std': pressure_smooth
                }
        
        return results

    def create_melting_analysis_plots(self, data, system_info=None):
        """Create melting analysis plots with graceful handling of missing data"""
        
        fig = plt.figure(figsize=(15, 6))
        for key in ['step', 'temperature', 'pair_energy', 'molecular_energy', 'total_energy', 'pressure', 'volume']:
            if not isinstance(data[key], np.ndarray):
                data[key] = np.array(data[key])
        
        temp = data['temperature']
        volume = data['volume']
        total_energy = data['total_energy']
        pressure = data['pressure']
        
        # Perform melting analysis
        analysis = self.analyze_melting_behavior(temp, volume, total_energy, pressure)
        
        # Helper function to create empty plot with message
        def create_empty_plot(subplot_num, title, xlabel, ylabel, message="Data not available"):
            plt.subplot(1, 3, subplot_num)
            plt.text(0.5, 0.5, message, ha='center', va='center', 
                    transform=plt.gca().transAxes, fontsize=12,
                    bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
            plt.title(title)
            plt.xlabel(xlabel)
            plt.ylabel(ylabel)
            plt.grid(True, alpha=0.3)
        
        # Plot 1: Energy Analysis
        plt.subplot(1, 3, 1)
        if len(temp) > 0 and len(total_energy) > 0:
            plt.plot(temp, total_energy, 'lightcoral', alpha=0.5, linewidth=1, label='Raw energy')
            
            if 'smoothed_data' in analysis:
                smooth = analysis['smoothed_data']
                plt.plot(smooth['temperature'], smooth['energy'], 'red', linewidth=3, label='Smoothed')
            
            plt.xlabel('Temperature (K)')
            plt.ylabel('Total Energy (eV)')
            plt.title('Energy vs Temperature')
            plt.legend()
            plt.grid(True, alpha=0.3)
        else:
            create_empty_plot(3, 'Energy vs Temperature', 'Temperature (K)', 'Total Energy (eV)',
                            "No energy data available")
        
        # Plot 2: Heat Capacity (Binned Analysis)
        plt.subplot(1, 3, 2)
        if 'binned_analysis' in analysis:
            binned = analysis['binned_analysis']
            plt.plot(binned['temperature'], binned['heat_capacity'], 'orange', linewidth=2)
            
            if 'melting_temp_heat_capacity' in analysis:
                mt = analysis['melting_temp_heat_capacity']
                plt.axvline(mt, color='red', linestyle='--', alpha=0.7,
                           label=f'Peak: {mt:.0f} K')
                plt.legend()
            
            plt.xlabel('Temperature (K)')
            plt.ylabel('Heat Capacity (eV/K)')
            plt.title('Heat Capacity (Binned Data)')
            plt.grid(True, alpha=0.3)
        else:
            create_empty_plot(4, 'Heat Capacity (Binned Data)', 'Temperature (K)', 'Heat Capacity (eV/K)',
                            "Insufficient data for\nheat capacity analysis")
            
        # Plot 3: Summary Statistics
        plt.subplot(1, 3, 3)
        plt.axis('off')
        
        # Create summary text
        summary_text = "MELTING POINT ANALYSIS\n"
        summary_text += "=" * 30 + "\n\n"
        
        if len(temp) > 0:
            # Add system information if provided
            if system_info is not None:
                if 'system_name' in system_info:
                    summary_text += f"System: {system_info['system_name']}\n"
                if 'num_atoms' in system_info:
                    summary_text += f"Atoms: {system_info['num_atoms']}\n"
                if 'material' in system_info:
                    summary_text += f"Material: {system_info['material']}\n"
                summary_text += "\n"
            
            summary_text += f"Data points: {len(temp)}\n"
            summary_text += f"Temp range: {temp.min():.0f} - {temp.max():.0f} K\n"
            
            if len(volume) > 0 and np.any(volume > 0):
                summary_text += f"Volume range: {volume.min():.1f} - {volume.max():.1f} Ų\n"
                vol_change = ((volume.max()-volume.min())/volume.min()*100) if volume.min() > 0 else 0
                summary_text += f"Volume change: {vol_change:.1f}%\n\n"
            else:
                summary_text += "Volume data: Not available\n\n"
            
            summary_text += "Estimated Melting Points:\n"
            melting_found = False
            if 'melting_temp_deviation' in analysis:
                summary_text += f"• Volume method: {analysis['melting_temp_deviation']:.0f} K\n"
                melting_found = True
            if 'melting_temp_heat_capacity' in analysis:
                summary_text += f"• Heat capacity: {analysis['melting_temp_heat_capacity']:.0f} K\n"
                melting_found = True
            if 'melting_temp_pressure_fluctuations' in analysis:
                summary_text += f"• Pressure fluct: {analysis['melting_temp_pressure_fluctuations']:.0f} K\n"
                melting_found = True
            
            if not melting_found:
                summary_text += "• No clear melting point detected\n"
            
            # Add simulation type note
            if 'volume_constant' in analysis:
                summary_text += "\nNote: Volume constant (NVT)\n"
            elif len(volume) > 0 and np.std(volume)/np.mean(volume) < 0.01:
                summary_text += "\nNote: Minimal volume change\n"
            else:
                summary_text += "\nNote: Variable volume (NPT)\n"
                
        else:
            summary_text += "No data available for analysis\n"
            summary_text += "Check input files and format."
        
        plt.text(0.05, 0.95, summary_text, transform=plt.gca().transAxes, fontsize=10,
                 verticalalignment='top', fontfamily='monospace',
                 bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        plt.tight_layout()
        return fig, analysis

    def visualize_melting_point_results(self, system_info=None) -> str:
        """
        Create visualization of the results of a melting point simulation.
        
        Args:
            system_info (dict, optional): Dictionary containing system information:
                - system_name: Name/description of the system
                - num_atoms: Number of atoms in the system
                - atomic_mass_u: Atomic mass in atomic mass units
                - material: Material type (e.g., 'Au', 'Cu', etc.)
                - total_mass_kg: Total mass in kg (alternative to num_atoms * atomic_mass_u)
        
        Returns:
            str: Path to the generated PNG file
        """
        # Try multiple possible filenames
        possible_files = [
            'log.lammps',             
            'lammps.out', 
            'output.log',
            'run.log',
            'thermo.out'
        ]
        
        self.logger.info("Analyzing melting simulation...")
        
        data = None
        filename = None
        
        # Change to work directory to look for files
        original_dir = os.getcwd()
        os.chdir(self.work_dir)
        
        try:
            for fname in possible_files:
                if os.path.exists(fname):
                    self.logger.info(f"Trying file: {fname}")
                    try:
                        data = self.parse_lammps_output(fname)
                        if data is not None:
                            filename = fname
                            break
                    except Exception as e:
                        self.logger.error(f"Failed to parse {fname}: {e}")
                        continue
            
            if data is None:
                self.logger.warning("No suitable LAMMPS output file found!")
                self.logger.warning("Creating empty visualization with available files...")
                
                # Create a minimal empty plot
                fig = plt.figure(figsize=(15, 6))
                for i in range(1, 13):
                    plt.subplot(1, 3, i)
                    plt.text(0.5, 0.5, 'No data available\nCheck input files', 
                            ha='center', va='center', transform=plt.gca().transAxes,
                            fontsize=12, bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
                    plt.title(f'Plot {i}')
                    plt.grid(True, alpha=0.3)
                
                plt.tight_layout()
                output_path = 'melting_analysis.png'
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                plt.close()
                
                return str(self.work_dir / output_path)
            
            self.logger.info(f"Successfully parsed {len(data['step'])} data points")
            
            try:
                fig, analysis = self.create_melting_analysis_plots(data, system_info)
                
                output_path = 'melting_analysis.png'
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                self.logger.info(f"Analysis saved as '{output_path}'")
                
                plt.close()
                
                return str(self.work_dir / output_path)
                
            except Exception as e:
                self.logger.error(f"Error creating plots: {e}")
                self.logger.info("But data was parsed successfully. Here's a summary:")
                for key, values in data.items():
                    if hasattr(values, 'min') and hasattr(values, 'max'):
                        self.logger.info(f"  {key}: {len(values)} values, range {values.min():.2f} to {values.max():.2f}")
                raise
        
        finally:
            os.chdir(original_dir)