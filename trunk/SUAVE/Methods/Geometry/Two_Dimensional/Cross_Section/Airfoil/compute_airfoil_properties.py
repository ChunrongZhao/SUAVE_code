## @ingroup Methods-Geometry-Two_Dimensional-Cross_Section-Airfoil
# compute_airfoil_properties.py
# 
# Created:  Mar 2019, M. Clarke
# Modified: Mar 2020, M. Clarke
#           Jan 2021, E. Botero
#           Jan 2021, R. Erhard
#           Nov 2021, R. Erhard

# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------

import SUAVE
from SUAVE.Core                                                       import Data , Units
from SUAVE.Methods.Aerodynamics.AERODAS.pre_stall_coefficients        import pre_stall_coefficients
from SUAVE.Methods.Aerodynamics.AERODAS.post_stall_coefficients       import post_stall_coefficients 
from SUAVE.Methods.Aerodynamics.Airfoil_Panel_Method.airfoil_analysis import airfoil_analysis 
from .import_airfoil_polars                                           import import_airfoil_polars 
import numpy as np
import time 
from scipy.interpolate import RegularGridInterpolator


## @ingroup Methods-Geometry-Two_Dimensional-Cross_Section-Airfoil
def compute_airfoil_properties(airfoil_geometry, airfoil_polars = None, boundary_layer_files = None ,use_pre_stall_data=True):
    """This computes the lift and drag coefficients of an airfoil in stall regimes using pre-stall
    characterstics and AERODAS formation for post stall characteristics. This is useful for 
    obtaining a more accurate prediction of wing and blade loading. Pre stall characteristics 
    are obtained in the form of a text file of airfoil polar data obtained from airfoiltools.com
    
    Assumptions:
    Uses AERODAS formulation for post stall characteristics 

    Source:
    Models of Lift and Drag Coefficients of Stalled and Unstalled Airfoils in Wind Turbines and Wind Tunnels
    by D Spera, 2008

    Inputs:
    airfoil_geometry       <string>
    airfoil_polars
            <string>
    use_pre_stall_data     [Boolean]

    Outputs:
    airfoil_data.
        cl_polars          [unitless]
        cd_polars          [unitless]      
        aoa_sweep          [unitless]
    
    Properties Used:
    N/A
    """   
    AoA_sweep                 = np.array([-2,0,4])*Units.degrees  # np.array([-2,0,4,8])*Units.degrees 
    Re_sweep                  = np.array([1,25,75])*1E4 # np.array([1,25,75,100])*1E4
    Ma_sweep                  = np.array([0.2,0.4,0.7]) # np.array([0.0,0.2,0.4,0.7]) 
    
    num_airfoils              = len(airfoil_geometry.x_coordinates)  
    dim_aoa                   = len(AoA_sweep)
    dim_Re                    = len(Re_sweep)
    dim_Ma                    = len(Ma_sweep) 
    
    airfoil_data                  = Data() 
    theta_lower_surface_surs      = Data()
    delta_lower_surface_surs      = Data()
    delta_star_lower_surface_surs = Data()
    sa_lower_surface_surs         = Data()
    ue_lower_surface_surs         = Data()
    cf_lower_surface_surs         = Data()
    Ret_lower_surface_surs        = Data()
    H_lower_surface_surs          = Data()
    theta_upper_surface_surs      = Data()
    delta_upper_surface_surs      = Data()
    delta_star_upper_surface_surs = Data()
    sa_upper_surface_surs         = Data()
    ue_upper_surface_surs         = Data()
    cf_upper_surface_surs         = Data()
    Ret_upper_surface_surs        = Data()
    H_upper_surface_surs          = Data() 
    
    if boundary_layer_files == None:        
        for af in range(num_airfoils):  
            cl                        = np.zeros((dim_aoa,dim_Re,dim_Ma))
            cd                        = np.zeros((dim_aoa,dim_Re,dim_Ma))
            cm                        = np.zeros((dim_aoa,dim_Re,dim_Ma))
            theta_lower_surface       = np.zeros((dim_aoa,dim_Re,dim_Ma))
            delta_lower_surface       = np.zeros((dim_aoa,dim_Re,dim_Ma))
            delta_star_lower_surface  = np.zeros((dim_aoa,dim_Re,dim_Ma))
            sa_lower_surface          = np.zeros((dim_aoa,dim_Re,dim_Ma))       
            ue_lower_surface          = np.zeros((dim_aoa,dim_Re,dim_Ma))   
            cf_lower_surface          = np.zeros((dim_aoa,dim_Re,dim_Ma))      
            Ret_lower_surface         = np.zeros((dim_aoa,dim_Re,dim_Ma))    
            H_lower_surface           = np.zeros((dim_aoa,dim_Re,dim_Ma))  
            theta_upper_surface       = np.zeros((dim_aoa,dim_Re,dim_Ma))
            delta_upper_surface       = np.zeros((dim_aoa,dim_Re,dim_Ma))
            delta_star_upper_surface  = np.zeros((dim_aoa,dim_Re,dim_Ma))
            sa_upper_surface          = np.zeros((dim_aoa,dim_Re,dim_Ma))       
            ue_upper_surface          = np.zeros((dim_aoa,dim_Re,dim_Ma))   
            cf_upper_surface          = np.zeros((dim_aoa,dim_Re,dim_Ma))      
            Ret_upper_surface         = np.zeros((dim_aoa,dim_Re,dim_Ma))    
            H_upper_surface           = np.zeros((dim_aoa,dim_Re,dim_Ma)) 
            
            for aoa_i in range(dim_aoa):
                for re_i in range(dim_Re):
                    for ma_i in range(dim_Ma): 
                    
                        AoA     = np.atleast_2d(AoA_sweep[aoa_i])
                        Re      = np.atleast_2d(Re_sweep[re_i] )
                        Ma      = np.atleast_2d(Ma_sweep[ma_i] )    
                        
                        # run airfoil analysis  
                        af_res  = airfoil_analysis(airfoil_geometry,AoA,Re,Ma,airfoil_stations = [af],viscous_flag = True)              
                        
                        bstei = 4 # bottom surface trailing edge index
                        nw    = af_res.num_wake_pts
                        tstei = -(bstei + nw) # top surface trailing edge index 
                        
                        # store raw results 
                        cl[af,aoa_i,re_i,ma_i]                        = af_res.cl[0][0]
                        cd[af,aoa_i,re_i,ma_i]                        = af_res.cd[0][0]
                        cm[af,aoa_i,re_i,ma_i]                        = af_res.cm[0][0]
                        theta_lower_surface[af,aoa_i,re_i,ma_i]       = af_res.theta[0][bstei]
                        delta_lower_surface[af,aoa_i,re_i,ma_i]       = af_res.delta[0][bstei]
                        delta_star_lower_surface[af,aoa_i,re_i,ma_i]  = af_res.delta_star[0][bstei]
                        sa_lower_surface[af,aoa_i,re_i,ma_i]          = af_res.sa[0][bstei]      
                        ue_lower_surface[af,aoa_i,re_i,ma_i]          = af_res.ue[0][bstei]   
                        cf_lower_surface[af,aoa_i,re_i,ma_i]          = af_res.cf[0][bstei]      
                        Ret_lower_surface[af,aoa_i,re_i,ma_i]         = af_res.Re_theta[0][bstei]    
                        H_lower_surface[af,aoa_i,re_i,ma_i]           = af_res.H[0][bstei] 
                        theta_upper_surface[af,aoa_i,re_i,ma_i]       = af_res.theta[0][tstei]
                        delta_upper_surface[af,aoa_i,re_i,ma_i]       = af_res.delta[0][tstei]
                        delta_star_upper_surface[af,aoa_i,re_i,ma_i]  = af_res.delta_star[0][tstei]
                        sa_upper_surface[af,aoa_i,re_i,ma_i]          = af_res.sa[0][tstei]      
                        ue_upper_surface[af,aoa_i,re_i,ma_i]          = af_res.ue[0][tstei]   
                        cf_upper_surface[af,aoa_i,re_i,ma_i]          = af_res.cf[0][tstei]      
                        Ret_upper_surface[af,aoa_i,re_i,ma_i]         = af_res.Re_theta[0][tstei]    
                        H_upper_surface[af,aoa_i,re_i,ma_i]           = af_res.H[0][tstei]    
                        
            
            # create surrogates  
            theta_lower_surface_surs[airfoil_geometry.name[af] + '_ls']       = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),theta_lower_surface ,bounds_error=False,fill_value=None  ) 
            delta_lower_surface_surs[airfoil_geometry.name[af]+ '_ls']       = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),delta_lower_surface ,bounds_error=False,fill_value=None  ) 
            delta_star_lower_surface_surs[airfoil_geometry.name[af]+ '_ls']  = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),delta_star_lower_surface,bounds_error=False,fill_value=None  ) 
            sa_lower_surface_surs[airfoil_geometry.name[af]+ '_ls']          = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),sa_lower_surface ,bounds_error=False,fill_value=None)   
            ue_lower_surface_surs[airfoil_geometry.name[af]+ '_ls']          = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),ue_lower_surface ,bounds_error=False,fill_value=None) 
            cf_lower_surface_surs[airfoil_geometry.name[af]+ '_ls']          = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),cf_lower_surface ,bounds_error=False,fill_value=None) 
            Ret_lower_surface_surs[airfoil_geometry.name[af]+ 'ls']         = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),Ret_lower_surface,bounds_error=False,fill_value=None  ) 
            H_lower_surface_surs[airfoil_geometry.name[af]+ '_ls']           = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),H_lower_surface  ,bounds_error=False,fill_value=None)
            theta_upper_surface_surs[airfoil_geometry.name[af]+ '_us']        = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),theta_upper_surface ,bounds_error=False,fill_value=None ) 
            delta_upper_surface_surs[airfoil_geometry.name[af]+ '_us']       = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),delta_upper_surface  ,bounds_error=False,fill_value=None) 
            delta_star_upper_surface_surs[airfoil_geometry.name[af]+ '_us']  = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),delta_star_upper_surface ,bounds_error=False,fill_value=None ) 
            sa_upper_surface_surs[airfoil_geometry.name[af]+ '_us']          = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),sa_upper_surface ,bounds_error=False,fill_value=None )   
            ue_upper_surface_surs[airfoil_geometry.name[af]+ '_us']          = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),ue_upper_surface ,bounds_error=False,fill_value=None ) 
            cf_upper_surface_surs[airfoil_geometry.name[af]+ '_us']          = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),cf_upper_surface ,bounds_error=False,fill_value=None ) 
            Ret_upper_surface_surs[airfoil_geometry.name[af]+ '_us']         = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),Ret_upper_surface,bounds_error=False,fill_value=None  ) 
            H_upper_surface_surs[airfoil_geometry.name[af]+ '_us']           = RegularGridInterpolator((AoA_sweep, Re_sweep, Ma_sweep),H_upper_surface  ,bounds_error=False,fill_value=None)  
                        
                
        # store surrogates  
        
        airfoil_data.theta_lower_surface_surrogates      = theta_lower_surface_surs  
        airfoil_data.delta_lower_surface_surrogates      = delta_lower_surface_surs 
        airfoil_data.delta_star_lower_surface_surrogates = delta_star_lower_surface_surs    
        airfoil_data.sa_lower_surface_surrogates         = sa_lower_surface_surs       
        airfoil_data.ue_lower_surface_surrogates         = ue_lower_surface_surs   
        airfoil_data.cf_lower_surface_surrogates         = cf_lower_surface_surs      
        airfoil_data.Re_theta_lower_surface_surrogates   = Ret_lower_surface_surs    
        airfoil_data.H_lower_surface_surrogates          = H_lower_surface_surs 
        airfoil_data.theta_upper_surface_surrogates      = theta_upper_surface_surs  
        airfoil_data.delta_upper_surface_surrogates      = delta_upper_surface_surs 
        airfoil_data.delta_star_upper_surface_surrogates = delta_star_upper_surface_surs    
        airfoil_data.sa_upper_surface_surrogates         = sa_upper_surface_surs       
        airfoil_data.ue_upper_surface_surrogates         = ue_upper_surface_surs   
        airfoil_data.cf_upper_surface_surrogates         = cf_upper_surface_surs      
        airfoil_data.Re_theta_upper_surface_surrogates   = Ret_upper_surface_surs    
        airfoil_data.H_upper_surface_surrogates          = H_upper_surface_surs 
         
    
    if airfoil_polars == None :

       
        airfoil_data.cl_surrogates    = cl_surs      
        airfoil_data.cm_surrogates    = cm_surs       
        airfoil_data.cd_surrogates    = cd_surs 
          
         
        
    else: 
        # check number of polars per airfoil in batch
        num_polars   = 0
        for i in range(num_airfoils): 
            n_p = len(airfoil_polars[i])
            if n_p < 3:
                raise AttributeError('Provide three or more airfoil polars to compute surrogate')
            
            num_polars = max(num_polars, n_p)         
    
        # Get all of the coefficients for AERODAS wings
        AoA_sweep_deg     = np.linspace(-14,90,105)
        AoA_sweep_radians = AoA_sweep_deg*Units.degrees
        CL                = np.zeros((num_airfoils,num_polars,len(AoA_sweep_deg)))
        CD                = np.zeros((num_airfoils,num_polars,len(AoA_sweep_deg)))
        aoa0              = np.zeros((num_airfoils,num_polars))
        cl0               = np.zeros((num_airfoils,num_polars))
    
        CL_surs = Data()
        CD_surs = Data()    
        aoa_from_polars = []
        
        # Create an infinite aspect ratio wing
        geometry              = SUAVE.Components.Wings.Wing()
        geometry.aspect_ratio = np.inf
        geometry.section      = Data()
        
        # Create dummy settings and state
        settings = Data()
        state    = Data()
        state.conditions = Data()
        state.conditions.aerodynamics = Data()
        state.conditions.aerodynamics.pre_stall_coefficients = Data()
        state.conditions.aerodynamics.post_stall_coefficients = Data()
    
        # read airfoil polars 
        airfoil_polar_data = import_airfoil_polars(airfoil_polars)
        
        # AERODAS 
        for i in range(num_airfoils):
            
            # Modify the "wing" slightly:
            geometry.thickness_to_chord = airfoil_geometry.thickness_to_chord[i]
            
            for j in range(len(airfoil_polars[i])):
                # Extract from polars
                airfoil_cl         = airfoil_polar_data.lift_coefficients[i,j] 
                airfoil_cd         = airfoil_polar_data.drag_coefficients[i,j] 
                airfoil_aoa        = airfoil_polar_data.angle_of_attacks  
                
                # computing approximate zero lift aoa
                airfoil_cl_plus = airfoil_cl[airfoil_cl>0]
                idx_zero_lift = np.where(airfoil_cl == min(airfoil_cl_plus))[0][0]
                airfoil_cl_crossing = airfoil_cl[idx_zero_lift-1:idx_zero_lift+1]
                airfoil_aoa_crossing = airfoil_aoa[idx_zero_lift-1:idx_zero_lift+1]
                try:
                    A0  = np.interp(0,airfoil_cl_crossing, airfoil_aoa_crossing)* Units.deg 
                except:
                    A0 = airfoil_aoa[idx_zero_lift] * Units.deg
                
    
                # max lift coefficent and associated aoa
                CL1max = np.max(airfoil_cl)
                idx_aoa_max_prestall_cl = np.where(airfoil_cl == CL1max)[0][0]
                ACL1 = airfoil_aoa[idx_aoa_max_prestall_cl] * Units.degrees
    
                # computing approximate lift curve slope
                linear_idxs = [int(np.where(airfoil_aoa==0)[0]),int(np.where(airfoil_aoa==4)[0])]
                cl_range = airfoil_cl[linear_idxs]
                aoa_range = airfoil_aoa[linear_idxs] * Units.degrees
                S1 = (cl_range[1]-cl_range[0])/(aoa_range[1]-aoa_range[0])
    
                # max drag coefficent and associated aoa
                CD1max  = np.max(airfoil_cd) 
                idx_aoa_max_prestall_cd = np.where(airfoil_cd == CD1max)[0][0]
                ACD1   = airfoil_aoa[idx_aoa_max_prestall_cd] * Units.degrees     
                
                # Find the point of lowest drag and the CD
                idx_CD_min = np.where(airfoil_cd==min(airfoil_cd))[0][0]
                ACDmin     = airfoil_aoa[idx_CD_min] * Units.degrees
                CDmin      = airfoil_cd[idx_CD_min]    
                
                # Setup data structures for this run
                ones = np.ones_like(AoA_sweep_radians)
                settings.section_zero_lift_angle_of_attack                = A0
                state.conditions.aerodynamics.angle_of_attack             = AoA_sweep_radians * ones 
                geometry.section.angle_attack_max_prestall_lift           = ACL1 * ones 
                geometry.pre_stall_maximum_drag_coefficient_angle         = ACD1 * ones 
                geometry.pre_stall_maximum_lift_coefficient               = CL1max * ones 
                geometry.pre_stall_maximum_lift_drag_coefficient          = CD1max * ones 
                geometry.section.minimum_drag_coefficient                 = CDmin * ones 
                geometry.section.minimum_drag_coefficient_angle_of_attack = ACDmin
                geometry.pre_stall_lift_curve_slope                       = S1
                
                # Get prestall coefficients
                CL1, CD1 = pre_stall_coefficients(state,settings,geometry)
                
                # Get poststall coefficents
                CL2, CD2 = post_stall_coefficients(state,settings,geometry)
                
                # Take the maxes
                CL_ij = np.fmax(CL1,CL2)
                CL_ij[AoA_sweep_radians<=A0] = np.fmin(CL1[AoA_sweep_radians<=A0],CL2[AoA_sweep_radians<=A0])
                
                CD_ij = np.fmax(CD1,CD2)
                
                # Pack this loop
                CL[i,j,:] = CL_ij
                CD[i,j,:] = CD_ij
                aoa0[i,j] = A0
                cl0[i,j]  = np.interp(0,airfoil_aoa,airfoil_cl)
                
                if use_pre_stall_data == True:
                    CL[i,j,:], CD[i,j,:] = apply_pre_stall_data(AoA_sweep_deg, airfoil_aoa, airfoil_cl, airfoil_cd, CL[i,j,:], CD[i,j,:])
            
            # remove placeholder values (for airfoils that have different number of polars)
            n_p      = len(airfoil_polars[i])
            RE_data  = airfoil_polar_data.reynolds_number[i][0:n_p]
            aoa_data = AoA_sweep_radians
            
            CL_sur = RegularGridInterpolator((RE_data, aoa_data), CL[i,0:n_p,:],bounds_error=False,fill_value=None)  
            CD_sur = RegularGridInterpolator((RE_data, aoa_data), CD[i,0:n_p,:],bounds_error=False,fill_value=None)           
            
            CL_surs[airfoil_geometry.name[i]]  = CL_sur
            CD_surs[airfoil_geometry.name[i]]  = CD_sur   
            aoa_from_polars.append(airfoil_aoa)
            
        airfoil_data.angle_of_attacks              = AoA_sweep_radians
        airfoil_data.lift_coefficient_surrogates   = CL_surs
        airfoil_data.drag_coefficient_surrogates   = CD_surs  
        airfoil_data.lift_coefficients_from_polar  = airfoil_polar_data.lift_coefficients
        airfoil_data.drag_coefficients_from_polar  = airfoil_polar_data.drag_coefficients
        airfoil_data.re_from_polar                 = airfoil_polar_data.reynolds_number
        airfoil_data.aoa_from_polar                = aoa_from_polars #airfoil_polar_data.angle_of_attacks
        
    return airfoil_data

def apply_pre_stall_data(AoA_sweep_deg, airfoil_aoa, airfoil_cl, airfoil_cd, CL, CD):
    # Coefficients in pre-stall regime taken from experimental data:
    aoa_locs = (AoA_sweep_deg>=airfoil_aoa[0]) * (AoA_sweep_deg<=airfoil_aoa[-1])
    aoa_in_data = AoA_sweep_deg[aoa_locs]
    
    # if the data is within experimental use it, if not keep the surrogate values
    CL[aoa_locs] = airfoil_cl[abs(aoa_in_data[:,None] - airfoil_aoa[None,:]).argmin(axis=-1)]
    CD[aoa_locs] = airfoil_cd[abs(aoa_in_data[:,None] - airfoil_aoa[None,:]).argmin(axis=-1)]
    
    # remove kinks/overlap between pre- and post-stall                
    data_lb = np.where(CD == airfoil_cd[0])[0][0]
    data_ub = np.where(CD == airfoil_cd[-1])[0][-1]
    CD[0:data_lb] = np.maximum(CD[0:data_lb], CD[data_lb]*np.ones_like(CD[0:data_lb]))
    CD[data_ub:]  = np.maximum(CD[data_ub:],  CD[data_ub]*np.ones_like(CD[data_ub:])) 
    
    return CL, CD