## @defgroup Plots-Performance Performance
# Plots contains functions for generating common figures
# @ingroup Plots

from .Mission_Plots       import plot_flight_conditions 
from .Mission_Plots       import plot_aerodynamic_coefficients
from .Mission_Plots       import plot_stability_coefficients
from .Mission_Plots       import plot_aerodynamic_forces
from .Mission_Plots       import plot_drag_components
from .Mission_Plots       import plot_altitude_sfc_weight
from .Mission_Plots       import plot_aircraft_velocities
from .Mission_Plots       import plot_battery_cell_conditions  
from .Mission_Plots       import plot_battery_pack_conditions
from .Mission_Plots       import plot_eMotor_Prop_efficiencies
from .Mission_Plots       import plot_disc_power_loading
from .Mission_Plots       import plot_solar_flux
from .Mission_Plots       import plot_lift_cruise_network  
from .Mission_Plots       import plot_propeller_conditions 
from .Mission_Plots       import plot_tiltrotor_conditions
from .Mission_Plots       import plot_surface_pressure_contours
from .Mission_Plots       import create_video_frames
from .Mission_Plots       import plot_lift_distribution 
from .Mission_Plots       import create_video_frames 
from .Mission_Plots       import plot_ground_noise_levels  
from .Mission_Plots       import plot_flight_profile_noise_contours 
from .Mission_Plots       import plot_fuel_use

from .Airfoil_Plots       import plot_airfoil_panels
from .Airfoil_Plots       import plot_airfoil_cp
from .Airfoil_Plots       import plot_airfoil
from .Airfoil_Plots       import plot_airfoil_boundary_layers
from .Airfoil_Plots       import plot_airfoil_distributions
from .Airfoil_Plots       import plot_airfoil_polar_files
from .Airfoil_Plots       import plot_airfoil_aerodynamic_coefficients

from .Propeller_Plots     import plot_propeller_disc_performance
from .Propeller_Plots     import plot_propeller_disc_inflow