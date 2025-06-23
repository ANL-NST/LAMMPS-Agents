# init.mod – initialization for elastic constants of FCC Au

# Define the finite deformation size. Try several values of this
# variable to verify that results do not depend on it.
variable up equal 1.0e-6

# Define the amount of random jiggle for atoms
# This prevents atoms from staying on saddle points
variable atomjiggle equal 1.0e-5

# Units: metal; output elastic constants in GPa
units           metal
variable cfac equal 1.0e-4
variable cunits string GPa

# Minimization parameters
variable etol equal 0.0 
variable ftol equal 1.0e-10
variable maxiter equal 100
variable maxeval equal 1000
variable dmax equal 1.0e-2

# Simulation box and structure
boundary        p p p
atom_style      atomic

# Load structure created by Atomsk
read_data       si_fcc.lmp
