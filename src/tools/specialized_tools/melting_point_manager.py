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
                fig = plt.figure(figsize=(12, 5))
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
                fig, analysis = self.create_simple_melting_plots(data, system_info) #create_melting_analysis_plots
                
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


    def create_simple_melting_plots(self, data, system_info=None):
        """Create simplified melting analysis with just two plots side by side"""
        
        # Create figure with white background and wide layout for two plots
        fig = plt.figure(figsize=(12, 5), facecolor='white')
        
        # Validate and convert data to numpy arrays safely
        required_keys = ['step', 'temperature', 'pair_energy', 'molecular_energy', 'total_energy', 'pressure', 'volume']
        for key in required_keys:
            if key not in data:
                data[key] = np.array([])  # Create empty array if key missing
            elif not isinstance(data[key], np.ndarray):
                data[key] = np.array(data[key])
        
        temp = data['temperature']
        volume = data['volume']
        potential_energy = data['pair_energy']  # Use potential energy
        pressure = data['pressure']

        if len(temp) > 0:
            min_temp = temp.min()
            temp_threshold = min_temp + 300
            mask = temp >= temp_threshold
            temp = temp[mask]
            volume = volume[mask]
            potential_energy = potential_energy[mask]
            pressure = pressure[mask]
        
        # Only perform analysis if we have sufficient data
        analysis = {}
        if len(temp) > 10 and len(potential_energy) > 10:
            analysis = self.analyze_melting_behavior(temp, volume, potential_energy, pressure)
        
        label_font_size = 14
        title_font_size = 16
        tick_font_size = 12
        title_pad = 20
        
        # Plot 1: Potential Energy vs Temperature (left side)
        ax1 = plt.subplot(1, 2, 1)
        
        if len(temp) > 0 and len(potential_energy) > 0 and np.any(potential_energy != 0):
            scatter = ax1.scatter(temp, potential_energy, 
                                c='#dc2626',
                                alpha=0.6, 
                                s=80,
                                edgecolors='#991b1b',
                                linewidth=0.6,
                                label='MD Trajectory')
            
            ax1.set_xlabel('Temperature (K)', fontsize=label_font_size)
            ax1.set_ylabel('Potential Energy (eV)', fontsize=label_font_size)
            ax1.set_title('Potential Energy vs Temperature', 
                        fontsize=title_font_size, pad=title_pad)
            ax1.legend(fontsize=tick_font_size)
            ax1.grid(True, alpha=0.3, linestyle='--')
            ax1.tick_params(axis='both', labelsize=tick_font_size)
            
            # ...existing margin code...
        
        else:
            ax1.text(0.5, 0.5, 'No potential energy data available', 
                    ha='center', va='center', transform=ax1.transAxes,
                    fontsize=label_font_size, bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
            ax1.set_title('Potential Energy vs Temperature', fontsize=title_font_size)
            ax1.set_xlabel('Temperature (K)', fontsize=label_font_size)
            ax1.set_ylabel('Potential Energy (eV)', fontsize=label_font_size)
        
        # Plot 2: Heat Capacity Analysis (right side)
        ax2 = plt.subplot(1, 2, 2)
        
        if 'binned_analysis' in analysis:
            binned = analysis['binned_analysis']
            ax2.plot(binned['temperature'], binned['heat_capacity'], 
                    color='#f97316', linewidth=3, label='Heat Capacity')
            
            if 'melting_temp_heat_capacity' in analysis:
                mt = analysis['melting_temp_heat_capacity']
                ax2.axvline(mt, color='#dc2626', linestyle='--', alpha=0.8, linewidth=2,
                        label=f'Peak: {mt:.0f} K')
                ax2.legend(fontsize=tick_font_size)
            
            ax2.set_xlabel('Temperature (K)', fontsize=label_font_size)
            ax2.set_ylabel('Heat Capacity (eV/K)', fontsize=label_font_size)
            ax2.set_title('Heat Capacity Analysis', fontsize=title_font_size, pad=title_pad)
            ax2.grid(True, alpha=0.3, linestyle='--')
            ax2.tick_params(axis='both', labelsize=tick_font_size)
        else:
            ax2.text(0.5, 0.5, 'Insufficient data for\nheat capacity analysis', 
                    ha='center', va='center', transform=ax2.transAxes,
                    fontsize=label_font_size, bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
            ax2.set_title('Heat Capacity Analysis', fontsize=title_font_size)
            ax2.set_xlabel('Temperature (K)', fontsize=label_font_size)
            ax2.set_ylabel('Heat Capacity (eV/K)', fontsize=label_font_size)
        
        plt.tight_layout()
        
        return fig, analysis


    def create_melting_analysis_plots(self, data, system_info=None):
        """Create melting analysis plots matching the interactive scatter plot style"""
        
        # Create figure with white background and larger size for better visibility
        fig = plt.figure(figsize=(16, 10), facecolor='white')
        
        # Validate and convert data to numpy arrays safely
        required_keys = ['step', 'temperature', 'pair_energy', 'molecular_energy', 'total_energy', 'pressure', 'volume']
        for key in required_keys:
            if key not in data:
                data[key] = np.array([])  # Create empty array if key missing
            elif not isinstance(data[key], np.ndarray):
                data[key] = np.array(data[key])
        
        temp = data['temperature']
        volume = data['volume']
        potential_energy = data['pair_energy']  # Use potential energy
        pressure = data['pressure']
        
        # Only perform analysis if we have sufficient data
        analysis = {}
        if len(temp) > 10 and len(potential_energy) > 10:
            analysis = self.analyze_melting_behavior(temp, volume, potential_energy, pressure)
        
        # Main scatter plot - Potential Energy vs Temperature
        ax1 = plt.subplot(2, 2, (1, 2))  # Top row spanning both columns
        
        if len(temp) > 0 and len(potential_energy) > 0 and np.any(potential_energy != 0):
            # Create scatter plot with red color scheme matching the React version
            scatter = ax1.scatter(temp, potential_energy, 
                                c='#dc2626',  # Red color
                                alpha=0.6, 
                                s=80,  # Point size
                                edgecolors='#991b1b',  # Darker red edge
                                linewidth=0.6,
                                label='MD Trajectory')
            
            # Add smoothed line if available
            # if 'smoothed_data' in analysis:
            #     smooth = analysis['smoothed_data']
            #     ax1.plot(smooth['temperature'], smooth['energy'], 
            #             color='#991b1b', linewidth=3, alpha=0.8, label='Smoothed')
            
            ax1.set_xlabel('Temperature (K)', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Potential Energy (eV)', fontsize=14, fontweight='bold')
            ax1.set_title('Molecular Dynamics: Potential Energy vs Temperature', 
                        fontsize=16, fontweight='bold', pad=20)
            ax1.legend(fontsize=12)
            ax1.grid(True, alpha=0.3, linestyle='--')
            ax1.tick_params(axis='both', labelsize=12)
            
            # Add some padding to the axes
            x_margin = (temp.max() - temp.min()) * 0.05
            y_margin = (potential_energy.max() - potential_energy.min()) * 0.05
            ax1.set_xlim(temp.min() - x_margin, temp.max() + x_margin)
            ax1.set_ylim(potential_energy.min() - y_margin, potential_energy.max() + y_margin)
            
        else:
            ax1.text(0.5, 0.5, 'No potential energy data available', 
                    ha='center', va='center', transform=ax1.transAxes,
                    fontsize=14, bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
            ax1.set_title('Potential Energy vs Temperature', fontsize=16, fontweight='bold')
            ax1.set_xlabel('Temperature (K)', fontsize=14)
            ax1.set_ylabel('Potential Energy (eV)', fontsize=14)
        
        # Plot 2: Heat Capacity Analysis (bottom left)
        ax2 = plt.subplot(2, 2, 3)
        if 'binned_analysis' in analysis:
            binned = analysis['binned_analysis']
            ax2.plot(binned['temperature'], binned['heat_capacity'], 
                    color='#f97316', linewidth=3, label='Heat Capacity')  # Orange color
            
            if 'melting_temp_heat_capacity' in analysis:
                mt = analysis['melting_temp_heat_capacity']
                ax2.axvline(mt, color='#dc2626', linestyle='--', alpha=0.8, linewidth=2,
                        label=f'Peak: {mt:.0f} K')
                ax2.legend(fontsize=10)
            
            ax2.set_xlabel('Temperature (K)', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Heat Capacity (eV/K)', fontsize=12, fontweight='bold')
            ax2.set_title('Heat Capacity Analysis', fontsize=14, fontweight='bold')
            ax2.grid(True, alpha=0.3, linestyle='--')
            ax2.tick_params(axis='both', labelsize=10)
        else:
            ax2.text(0.5, 0.5, 'Insufficient data for\nheat capacity analysis', 
                    ha='center', va='center', transform=ax2.transAxes,
                    fontsize=12, bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
            ax2.set_title('Heat Capacity Analysis', fontsize=14, fontweight='bold')
            ax2.set_xlabel('Temperature (K)', fontsize=12)
            ax2.set_ylabel('Heat Capacity (eV/K)', fontsize=12)
        
        # Plot 3: Statistics and Analysis Summary (bottom right)
        ax3 = plt.subplot(2, 2, 4)
        ax3.axis('off')
        
        # Create comprehensive summary matching the React version style
        summary_parts = []
        
        # Title
        summary_parts.append("MOLECULAR DYNAMICS ANALYSIS")
        summary_parts.append("=" * 35)
        summary_parts.append("")
        
        if len(temp) > 0:
            # System information
            if system_info is not None:
                if 'system_name' in system_info:
                    summary_parts.append(f"System: {system_info['system_name']}")
                if 'num_atoms' in system_info:
                    summary_parts.append(f"Atoms: {system_info['num_atoms']}")
                if 'material' in system_info:
                    summary_parts.append(f"Material: {system_info['material']}")
                summary_parts.append("")
            
            # Data summary
            summary_parts.append(f"DATA SUMMARY:")
            summary_parts.append(f"   • Data points: {len(temp)} timesteps")
            summary_parts.append(f"   • Temperature range: {temp.min():.0f} - {temp.max():.0f} K")
            summary_parts.append(f"   • Simulation: 200k steps, 216 atoms")
            summary_parts.append("")
            
            if len(potential_energy) > 0 and np.any(potential_energy != 0):
                summary_parts.append(f"⚡ ENERGY ANALYSIS:")
                summary_parts.append(f"   • PE range: {potential_energy.min():.1f} - {potential_energy.max():.1f} eV")
                pe_change = potential_energy.max() - potential_energy.min()
                summary_parts.append(f"   • PE change: {pe_change:.1f} eV")
                summary_parts.append("")
            
            # Melting point estimates
            summary_parts.append("🔥 MELTING ANALYSIS:")
            melting_found = False
            if analysis:
                if 'melting_temp_heat_capacity' in analysis:
                    mt = analysis['melting_temp_heat_capacity']
                    summary_parts.append(f"   • Heat capacity peak: {mt:.0f} K")
                    melting_found = True
                if 'melting_temp_deviation' in analysis:
                    mt = analysis['melting_temp_deviation']
                    summary_parts.append(f"   • Volume expansion: {mt:.0f} K")
                    melting_found = True
                if 'melting_temp_pressure_fluctuations' in analysis:
                    mt = analysis['melting_temp_pressure_fluctuations']
                    summary_parts.append(f"   • Pressure fluctuations: {mt:.0f} K")
                    melting_found = True
            
            if not melting_found:
                summary_parts.append("   • No clear melting point detected")
            
            summary_parts.append("")
            
            # Physical interpretation
            summary_parts.append("PHYSICAL INTERPRETATION:")
            summary_parts.append("   • Negative PE: Bound molecular system")
            summary_parts.append("   • Increasing trend: Thermal expansion")
            summary_parts.append("   • Scatter: Normal MD fluctuations")
            
            # Simulation type
            if 'volume_constant' in analysis:
                summary_parts.append("   • Simulation type: NVT (constant volume)")
            elif len(volume) > 0 and np.std(volume)/np.mean(volume) < 0.01:
                summary_parts.append("   • Simulation type: Minimal volume change")
            else:
                summary_parts.append("   • Simulation type: NPT (variable volume)")
            
        else:
            summary_parts.append("NO DATA AVAILABLE")
            summary_parts.append("Check input files and format.")
        
        # Display the summary text with nice formatting
        summary_text = "\n".join(summary_parts)
        ax3.text(0.05, 0.95, summary_text, transform=ax3.transAxes, fontsize=10,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round,pad=1', facecolor='#f8f9fa', 
                        edgecolor='#dee2e6', alpha=0.9))
        
        # Add statistics boxes at the bottom (matching React version style)
        if len(temp) > 0:
            fig.text(0.02, 0.02, f"Data Points\n{len(temp)} timesteps", 
                    bbox=dict(boxstyle='round', facecolor='#dbeafe', edgecolor='#3b82f6'),
                    fontsize=10, ha='left')
            
            fig.text(0.25, 0.02, f"Temperature Range\n{temp.min():.0f} - {temp.max():.0f} K", 
                    bbox=dict(boxstyle='round', facecolor='#fed7aa', edgecolor='#f97316'),
                    fontsize=10, ha='left')
            
            if len(potential_energy) > 0:
                fig.text(0.48, 0.02, f"PE Range\n{potential_energy.min():.1f} - {potential_energy.max():.1f} eV", 
                        bbox=dict(boxstyle='round', facecolor='#fee2e2', edgecolor='#dc2626'),
                        fontsize=10, ha='left')
            
            fig.text(0.71, 0.02, f"Simulation\n200k steps, 216 atoms", 
                    bbox=dict(boxstyle='round', facecolor='#dcfce7', edgecolor='#16a34a'),
                    fontsize=10, ha='left')
        
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.12)  # Make room for the statistics boxes
        
        return fig, analysis