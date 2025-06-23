
# ========================================================================
# init.mod (generalizable version)
# Define units, deformation parameters, and read a prepared structure file
# ========================================================================

# --- Deformation parameters ---
variable up equal 1.0e-6             # Finite deformation size
variable atomjiggle equal 1.0e-5     # Small random jiggle to break symmetry

# --- Units & elastic constants scaling ---
units           metal
dimension       3
boundary        p p p
atom_style      atomic

variable cfac equal 1.0e-4           # Conversion factor to GPa for metal units
variable cunits string GPa

# --- Minimization settings ---
variable etol equal 0.0
variable ftol equal 1.0e-10
variable maxiter equal 100
variable maxeval equal 1000
variable dmax equal 1.0e-2

# --- Load structure ---
# NOTE: Replace the filename below with your structure file.
# Structure must define a *triclinic* box to support tilt deformations (xy, xz, yz).
# You can create the structure externally using Atomsk, ASE, or packmol.

read_data structure_triclinic.lmp

