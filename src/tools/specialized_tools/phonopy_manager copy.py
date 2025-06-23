import os
import subprocess
import numpy as np
from pathlib import Path
from typing import Optional
from ase.io import read, write
from phonopy import Phonopy
# from phonopy.structure.atoms import PhonopyAtoms
from phonopy.interface.vasp import read_vasp, write_vasp

# from phonopy.structure.symmetry import symmetrize_force_constants


import numpy as np
import os


class PhonopyManager:
    def __init__(self, workdir: str):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        os.chdir(self.workdir)
    

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
        #phonopy --dim="3 3 3" -d  ---> this creates the phonopy_disp.yaml
        #phonopy -d --nosym --cell=phonopy_disp.yaml ---> this creates the displacement supercells
         

    # def generate_displacements(self, poscar_path="POSCAR", supercell_matrix=[2,2,2], disable_symmetry=False):
    #     poscar_path = self.workdir / poscar_path
    #     unitcell = read_vasp(poscar_path)
    #     phonon = Phonopy(unitcell, supercell_matrix)
        
    #     phonon.generate_displacements(distance=0.01, symmetry=False)

    #     supercells = phonon.get_supercells_with_displacements()

    #     for i, sc in enumerate(supercells):
    #         disp_dir = os.path.join(self.workdir, f"disp-{i+1:03d}")
    #         os.makedirs(disp_dir, exist_ok=True)
    #         write_vasp(os.path.join(disp_dir, "POSCAR"), sc, direct=True)

    #     return f"✅ Generated {len(supercells)} displacement supercells."


    def create_displacement_yaml(self, dim: str = "3 3 3") -> str:
        """Create displaced structures using phonopy."""
        try:
            result = subprocess.run(
                f"phonopy --dim=\"{dim}\" -d",
                shell=True, cwd=self.workdir, capture_output=True, text=True
            )
            if result.returncode != 0:
                return f"Phonopy error:\n{result.stderr}"
            return f"Displacement structures generated in {self.workdir}"
        except Exception as e:
            return f"Exception during displacement generation: {str(e)}"
        

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
        

    def create_lammps_input_for_displacements(self, potential_file: str) -> str:
        """Convert each displaced POSCAR to LAMMPS format and prepare input files."""
        from ase.io import read, write
        import glob
        # could also just save the input file of the displacements
        poscars = sorted(glob.glob("POSCAR-*"))
        for i, poscar in enumerate(poscars):
            atoms = read(poscar, format='vasp')
            dname = f"disp-{i:03d}"
            os.makedirs(dname, exist_ok=True)
            write(f"{dname}/structure.lmp", atoms, format='lammps-data')
            with open(f"{dname}/in.lmp", "w") as f:
                f.write(f"""units metal
atom_style atomic
boundary p p p
read_data structure.lmp
pair_style eam/fs
pair_coeff * * {potential_file} Au
compute 1 all property/atom fx fy fz
dump 1 all custom 1 dump.atom id type x y z fx fy fz
run 0
""")
        return f"LAMMPS input scripts created for {len(poscars)} displacements"


    def run_phonopy_analysis(self, element: str) -> str:
        """Parse LAMMPS forces and run phonopy analysis with plotting."""
        import matplotlib.pyplot as plt
        plt.switch_backend("Agg")

        # Collect forces
        subprocess.run("phonopy -f disp-*/dump.atom", shell=True, check=True)

        # Band structure path for FCC
        band_conf = f"""
ATOM_NAME = {element}
DIM = 3 3 3
BAND = 0 0 0 0.5 0 0 0.5 0.5 0 0 0.5 0 0 0 0
BAND_POINTS = 51
BAND_LABELS = Γ X K Γ L
"""
        with open("band.conf", "w") as f:
            f.write(band_conf.strip())

        # Run phonopy and generate plots
        subprocess.run("phonopy -p band.conf", shell=True, check=True)
        return "Phonopy analysis completed and dispersion plot saved"
