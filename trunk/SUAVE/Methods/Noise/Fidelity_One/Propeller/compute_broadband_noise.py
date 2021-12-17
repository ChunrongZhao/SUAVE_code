## @ingroupMethods-Noise-Fidelity_One-Propeller
# compute_broadband_noise.py
#
# Created:  Mar 2021, M. Clarke

# ----------------------------------------------------------------------
#  Imports
# ---------------------------------------------------------------------- 
from SUAVE.Core import Units , Data  
#from memory_profiler import profile 
import numpy as np 
 
from SUAVE.Methods.Noise.Fidelity_One.Noise_Tools.dbA_noise                     import A_weighting  
from SUAVE.Methods.Noise.Fidelity_One.Noise_Tools.SPL_harmonic_to_third_octave  import SPL_harmonic_to_third_octave
from SUAVE.Methods.Noise.Fidelity_One.Noise_Tools.compute_source_coordinates    import vectorize
from SUAVE.Methods.Geometry.Two_Dimensional.Cross_Section.Airfoil.compute_naca_4series import compute_naca_4series  
from SUAVE.Methods.Geometry.Two_Dimensional.Cross_Section.Airfoil.import_airfoil_geometry \
     import import_airfoil_geometry
from SUAVE.Methods.Aerodynamics.Airfoil_Panel_Method.airfoil_analysis           import airfoil_analysis
from scipy.special import fresnel

# ----------------------------------------------------------------------
# Frequency Domain Broadband Noise Computation
# ----------------------------------------------------------------------
## @ingroupMethods-Noise-Fidelity_One-Propeller
#@profile
def compute_broadband_noise(freestream,angle_of_attack,blade_section_position_vectors,
                            velocity_vector,network,auc_opts,settings,res,source):
    '''This computes the trailing edge noise compoment of broadband noise of a propeller or 
    rotor in the frequency domain
    
    Assumptions:
        UPDATE

    Source:
       UPDATE
    
    
    Inputs:  
        freestream                    - freestream data structure                                                   [m/s]
        angle_of_attack               - aircraft angle of attack                                                    [rad]
        position_vector               - position vector of aircraft                                                 [m]
        velocity_vector               - velocity vector of aircraft                                                 [m/s]
        network                       - energy network object                                                       [None] 
        auc_opts                      - data structure of acoustic data                                             [None] 
        settings                      - accoustic settings                                                          [None] 
    
    Outputs 
       res.                                       *acoustic data is stored and passed in data structures*                        
           SPL_prop_broadband_spectrum           - harmonic noise in blade passing frequency spectrum              [dB]
           SPL_prop_broadband_spectrum_dBA       - dBA-Weighted harmonic noise in blade passing frequency spectrum [dbA]     
           SPL_prop_broadband_1_3_spectrum       - harmonic noise in 1/3 octave spectrum                           [dB]
           SPL_prop_broadband_1_3_spectrum_dBA   - dBA-Weighted harmonic noise in 1/3 octave spectrum              [dBA] 
           p_pref_broadband                      - pressure ratio of harmonic noise                                [Unitless]
           p_pref_broadband_dBA                  - pressure ratio of dBA-weighted harmonic noise                   [Unitless]
       
       
       
            
    Properties Used:
        N/A   
    '''     

    num_cpt         = len(angle_of_attack) 
    num_prop        = len(blade_section_position_vectors.blade_section_coordinate_sys[0,0,:,0,0,0,0,0]) 
    num_mic         = len(blade_section_position_vectors.blade_section_coordinate_sys[0,:,0,0,0,0,0,0])
    precision       = settings.floating_point_precision
    
    if source == 'lift_rotors':  
        propellers      = network.lift_rotors 
    else:
        propellers      = network.propellers
        
    propeller = propellers[list(propellers.keys())[0]]   # CORRECT 
    BSR       = settings.broadband_spectrum_resolution # broadband spectrum resolution    
    POS       = blade_section_position_vectors.blade_section_coordinate_sys   
    POS_2     = blade_section_position_vectors.vehicle_coordinate_sys           
    r         = blade_section_position_vectors.r                               
    beta_p    = blade_section_position_vectors.beta_p                          
    phi       = blade_section_position_vectors.phi                             
    alpha_eff = blade_section_position_vectors.alpha_eff                              
    t_v       = blade_section_position_vectors.t_v                             
    t_r       = blade_section_position_vectors.t_r                               
    M_hub     = blade_section_position_vectors.M_hub   
    
    # ----------------------------------------------------------------------------------
    # Trailing Edge Noise
    # ---------------------------------------------------------------------------------- 
    p_ref              = 2E-5                               # referece atmospheric pressure
    c_0                = freestream.speed_of_sound          # speed of sound
    rho                = freestream.density                 # air density 
    dyna_visc          = freestream.dynamic_viscosity
    kine_visc          = dyna_visc/rho                      # kinematic viscousity    
    alpha_blade        = auc_opts.disc_effective_angle_of_attack 
    Vt_2d              = auc_opts.disc_tangential_velocity  
    Va_2d              = auc_opts.disc_axial_velocity                
    blade_chords       = propeller.chord_distribution        # blade chord    
    r                  = propeller.radius_distribution        # radial location   
    num_sec            = len(r) 
    num_azi            = len(auc_opts.disc_effective_angle_of_attack[0,0,:])   
    U_blade            = np.sqrt(Vt_2d**2 + Va_2d **2)
    Re_blade           = U_blade*np.repeat(np.repeat(blade_chords[np.newaxis,:],num_cpt,axis=0)[:,:,np.newaxis],num_azi,axis=2)*\
                          np.repeat(np.repeat((rho/dyna_visc),num_sec,axis=1)[:,:,np.newaxis],num_azi,axis=2)
    rho_blade          = np.repeat(np.repeat(rho,num_sec,axis=1)[:,:,np.newaxis],num_azi,axis=2)
    U_inf              = np.atleast_2d(np.linalg.norm(velocity_vector,axis=1)).T
    M                  = U_inf/c_0                                             
    B                  = propeller.number_of_blades          # number of propeller blades
    Omega              = auc_opts.omega                      # angular velocity   
    pi                 = np.pi 
    beta_sq            = 1 - M**2                                  
    delta_r            = np.zeros_like(r)
    del_r              = r[1:] - r[:-1]
    delta_r[0]         = 2*del_r[0]
    delta_r[-1]        = 2*del_r[-1]
    delta_r[1:-1]      =  (del_r[:-1]+ del_r[1:])/2 

    delta        = np.zeros((num_cpt,num_mic,num_prop,num_sec,num_azi,BSR,2), dtype=precision) #  control points ,  number rotors, number blades , number sections , sides of airfoil   
    delta_star   = np.zeros_like(delta, dtype=precision)
    dp_dx        = np.zeros_like(delta, dtype=precision)
    tau_w        = np.zeros_like(delta, dtype=precision)
    Ue           = np.zeros_like(delta, dtype=precision)
    Theta        = np.zeros_like(delta, dtype=precision)  

    lower_surface_theta      = np.zeros((num_sec,num_azi), dtype=precision)
    lower_surface_delta      = np.zeros_like(lower_surface_theta, dtype=precision)
    lower_surface_delta_star = np.zeros_like(lower_surface_theta, dtype=precision)
    lower_surface_cf         = np.zeros_like(lower_surface_theta, dtype=precision)
    lower_surface_Ue         = np.zeros_like(lower_surface_theta, dtype=precision)
    lower_surface_H          = np.zeros_like(lower_surface_theta, dtype=precision) 
    lower_surface_dcp_dx     = np.zeros_like(lower_surface_theta, dtype=precision)
    upper_surface_theta      = np.zeros_like(lower_surface_theta, dtype=precision)
    upper_surface_delta      = np.zeros_like(lower_surface_theta, dtype=precision)
    upper_surface_delta_star = np.zeros_like(lower_surface_theta, dtype=precision)
    upper_surface_cf         = np.zeros_like(lower_surface_theta, dtype=precision)
    upper_surface_Ue         = np.zeros_like(lower_surface_theta, dtype=precision)
    upper_surface_H          = np.zeros_like(lower_surface_theta, dtype=precision)
    upper_surface_dcp_dx     = np.zeros_like(lower_surface_theta, dtype=precision)
    
    # ------------------------------------------------------------
    # ****** TRAILING EDGE BOUNDARY LAYER PROPERTY CALCULATIONS  ****** 
    for i in range(num_cpt) : # lower surface is 0, upper surface is 1  
        TE_idx                  = 4 # assume trailing edge is the forth from last panel  
        
        if propeller.nonuniform_freestream: # CORRECT THIS HANDLES AZIMUTHALLY CHANGING IN FLOW
            for i_azi in range(num_azi):
                if propeller.airfoil_flag  == True:   
                    a_geo                   = propeller.airfoil_geometry
                    airfoil_data            = import_airfoil_geometry(a_geo, npoints = propeller.number_of_airfoil_section_points)
                    Re_batch                = np.atleast_2d(Re_blade[i,:,0]).T
                    AoA_batch               = np.atleast_2d(alpha_blade[i,:,0]).T
                    npanel                  = len(airfoil_data.x_coordinates[0]) - 2
                    AP                      = airfoil_analysis(airfoil_data,AoA_batch,Re_batch, npanel, batch_analysis = False, airfoil_stations = propeller.airfoil_polar_stations)    
                else:               
                    camber                          = 0.0
                    camber_loc                      = 0.0
                    thickness                       = 0.12  
                    default_airfoil_data            = compute_naca_4series(camber, camber_loc, thickness,(propeller.number_of_airfoil_section_points*2 - 2)) 
                    airfoil_polar_stations          = np.zeros(num_sec)
                    default_airfoil_polar_stations  = list(airfoil_polar_stations.astype(int) )   
                    Re_batch                        = np.atleast_2d(Re_blade[i,:,0]).T
                    AoA_batch                       = np.atleast_2d(alpha_blade[i,:,0]).T
                    npanel                          = len(default_airfoil_data.x_coordinates[0]) - 2
                    AP                              = airfoil_analysis(default_airfoil_data,AoA_batch,Re_batch, npanel, batch_analysis = False, airfoil_stations = default_airfoil_polar_stations)    
     
                # extract properties 
                lower_surface_theta[:,i_azi]      = AP.theta[:,TE_idx]  
                lower_surface_delta[:,i_azi]      = AP.delta[:,TE_idx]  
                lower_surface_delta_star[:,i_azi] = AP.delta_star[:,TE_idx]   
                lower_surface_cf[:,i_azi]         = AP.Cf[:,TE_idx]   
                lower_surface_Ue[:,i_azi]         = AP.Ue_Vinf[:,TE_idx]   
                lower_surface_H[:,i_azi]          = AP.H[:,TE_idx]   
                surface_dcp_dx                    = (np.diff(AP.Cp,axis = 1)/np.diff(AP.x,axis = 1))
                lower_surface_dcp_dx[:,i_azi]     = abs(surface_dcp_dx[:,TE_idx]/blade_chords)    
                upper_surface_theta[:,i_azi]      = AP.theta[:,-TE_idx]   
                upper_surface_delta[:,i_azi]      = AP.delta[:,-TE_idx]   
                upper_surface_delta_star[:,i_azi] = AP.delta_star[:,-TE_idx]   
                upper_surface_cf[:,i_azi]         = AP.Cf[:,-TE_idx]   
                upper_surface_Ue[:,i_azi]         = AP.Ue_Vinf[:,-TE_idx]   
                upper_surface_H[:,i_azi]          = AP.H[:,-TE_idx]     
                upper_surface_dcp_dx[:,i_azi]     = abs(surface_dcp_dx[:,-TE_idx]/blade_chords)
        else:
            if propeller.airfoil_flag  == True:   
                a_geo                   = propeller.airfoil_geometry
                airfoil_data            = import_airfoil_geometry(a_geo, npoints = propeller.number_of_airfoil_section_points)
                Re_batch                = np.atleast_2d(Re_blade[i,:,0]).T
                AoA_batch               = np.atleast_2d(alpha_blade[i,:,0]).T
                npanel                  = len(airfoil_data.x_coordinates[0]) - 2
                AP                      = airfoil_analysis(airfoil_data,AoA_batch,Re_batch, npanel, batch_analysis = False, airfoil_stations = propeller.airfoil_polar_stations)    
            else:               
                camber                          = 0.0
                camber_loc                      = 0.0
                thickness                       = 0.12  
                default_airfoil_data            = compute_naca_4series(camber, camber_loc, thickness,(propeller.number_of_airfoil_section_points*2 - 2)) 
                airfoil_polar_stations          = np.zeros(num_sec)
                default_airfoil_polar_stations  = list(airfoil_polar_stations.astype(int) )   
                Re_batch                        = np.atleast_2d(Re_blade[i,:,0]).T
                AoA_batch                       = np.atleast_2d(alpha_blade[i,:,0]).T
                npanel                          = len(default_airfoil_data.x_coordinates[0]) - 2
                AP                              = airfoil_analysis(default_airfoil_data,AoA_batch,Re_batch, npanel, batch_analysis = False, airfoil_stations = default_airfoil_polar_stations)    
 
            # extract properties 
            lower_surface_theta[:,:]      = np.repeat(np.atleast_2d(AP.theta[:,TE_idx]).T,num_azi,axis = 1)  
            lower_surface_delta[:,:]      = np.repeat(np.atleast_2d(AP.delta[:,TE_idx]).T,num_azi,axis = 1)  
            lower_surface_delta_star[:,:] = np.repeat(np.atleast_2d(AP.delta_star[:,TE_idx]).T,num_azi,axis = 1)   
            lower_surface_cf[:,:]         = np.repeat(np.atleast_2d(AP.Cf[:,TE_idx]).T,num_azi,axis = 1)   
            lower_surface_Ue[:,:]         = np.repeat(np.atleast_2d(AP.Ue_Vinf[:,TE_idx]).T,num_azi,axis = 1)   
            lower_surface_H[:,:]          = np.repeat(np.atleast_2d(AP.H[:,TE_idx]).T,num_azi,axis = 1)   
            surface_dcp_dx                = (np.diff(AP.Cp,axis = 1)/np.diff(AP.x,axis = 1))
            lower_surface_dcp_dx[:,:]     = np.repeat(np.atleast_2d(abs(surface_dcp_dx[:,TE_idx]/blade_chords)  ).T,num_azi,axis = 1)  
            upper_surface_theta[:,:]      = np.repeat(np.atleast_2d(AP.theta[:,-TE_idx]).T,num_azi,axis = 1)   
            upper_surface_delta[:,:]      = np.repeat(np.atleast_2d(AP.delta[:,-TE_idx]).T,num_azi,axis = 1)   
            upper_surface_delta_star[:,:] = np.repeat(np.atleast_2d(AP.delta_star[:,-TE_idx]).T,num_azi,axis = 1)   
            upper_surface_cf[:,:]         = np.repeat(np.atleast_2d(AP.Cf[:,-TE_idx]).T,num_azi,axis = 1)   
            upper_surface_Ue[:,:]         = np.repeat(np.atleast_2d(AP.Ue_Vinf[:,-TE_idx]).T,num_azi,axis = 1)   
            upper_surface_H[:,:]          = np.repeat(np.atleast_2d(AP.H[:,-TE_idx]).T,num_azi,axis = 1)     
            upper_surface_dcp_dx[:,:]     = np.repeat(np.atleast_2d(abs(surface_dcp_dx[:,-TE_idx]/blade_chords)).T,num_azi,axis = 1)       
    
        # replace nans 0 with mean as a post post-processor  
        lower_surface_theta       = np.nan_to_num(lower_surface_theta)
        lower_surface_delta       = np.nan_to_num(lower_surface_delta)
        lower_surface_delta_star  = np.nan_to_num(lower_surface_delta_star)
        lower_surface_cf          = np.nan_to_num(lower_surface_cf)
        lower_surface_dcp_dx      = np.nan_to_num(lower_surface_dcp_dx)
        lower_surface_Ue          = np.nan_to_num(lower_surface_Ue)
        lower_surface_H           = np.nan_to_num(lower_surface_H)
        upper_surface_theta       = np.nan_to_num(upper_surface_theta)
        upper_surface_delta       = np.nan_to_num(upper_surface_delta)
        upper_surface_delta_star  = np.nan_to_num(upper_surface_delta_star)
        upper_surface_cf          = np.nan_to_num(upper_surface_cf)
        upper_surface_dcp_dx      = np.nan_to_num(upper_surface_dcp_dx)
        upper_surface_Ue          = np.nan_to_num(upper_surface_Ue)
        upper_surface_H           = np.nan_to_num(upper_surface_H)    
    
        lower_surface_theta[lower_surface_theta == 0]           = np.mean(lower_surface_theta)
        lower_surface_delta[lower_surface_delta == 0]           = np.mean(lower_surface_delta)
        lower_surface_delta_star[lower_surface_delta_star == 0] = np.mean(lower_surface_delta_star)
        lower_surface_cf[lower_surface_cf == 0]                 = np.mean(lower_surface_cf)
        lower_surface_dcp_dx[lower_surface_dcp_dx == 0]         = np.mean(lower_surface_dcp_dx)
        lower_surface_Ue[lower_surface_Ue == 0]                 = np.mean(lower_surface_Ue)
        lower_surface_H[lower_surface_H == 0]                   = np.mean(lower_surface_H)
        upper_surface_theta[upper_surface_theta == 0]           = np.mean(upper_surface_theta)
        upper_surface_delta[upper_surface_delta == 0]           = np.mean(upper_surface_delta)
        upper_surface_delta_star[upper_surface_delta_star== 0]  = np.mean(upper_surface_delta_star)
        upper_surface_cf[upper_surface_cf == 0]                 = np.mean(upper_surface_cf)
        upper_surface_dcp_dx[upper_surface_dcp_dx == 0]         = np.mean(upper_surface_dcp_dx)
        upper_surface_Ue[upper_surface_Ue == 0]                 = np.mean(upper_surface_Ue)
        upper_surface_H[upper_surface_H == 0]                   = np.mean(upper_surface_H)     
   
        # ------------------------------------------------------------
        # ****** TRAILING EDGE BOUNDARY LAYER PROPERTY CALCULATIONS  ******  
 
        delta_star[i,:,:,:,:,:,0]   = vectorize(lower_surface_delta_star,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 7)                               # lower surfacedisplacement thickness 
        delta_star[i,:,:,:,:,:,1]   = vectorize(upper_surface_delta_star,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 7)                               # upper surface displacement thickness   
        dp_dx[i,:,:,:,:,:,0]        = vectorize(lower_surface_dcp_dx,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 7)                                   # lower surface pressure differential 
        dp_dx[i,:,:,:,:,:,1]        = vectorize(upper_surface_dcp_dx,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 7)                                   # upper surface pressure differential 
        U_e_lower_surf              = lower_surface_Ue*U_blade[i]
        U_e_upper_surf              = upper_surface_Ue*U_blade[i]
        Ue[i,:,:,:,:,:,0]           = vectorize(U_e_lower_surf,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 7)                                                    # lower surface boundary layer edge velocity 
        Ue[i,:,:,:,:,:,1]           = vectorize(U_e_upper_surf,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 7)                                                   # upper surface boundary layer edge velocity 
        tau_w[i,:,:,:,:,:,0]        = vectorize(lower_surface_cf*(0.5*rho_blade[i]*(U_e_lower_surf**2)),num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 7)    # lower surface wall shear stress
        tau_w[i:,:,:,:,:,:,1]       = vectorize(upper_surface_cf*(0.5*rho_blade[i]* (U_e_upper_surf**2)),num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 7)    # upper surface wall shear stress 
        Theta[i,:,:,:,:,:,0]        = vectorize(lower_surface_theta,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 7)                                    # lower surface momentum thickness     
        Theta[i,:,:,:,:,:,1]        = vectorize(upper_surface_theta,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 7)                                   # upper surface momentum thickness  
 
    delta         = Theta*(3.15 + (1.72/((delta_star/Theta)- 1))) + delta_star
    # Update dimensions for computation      
    r         = vectorize(r,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 1) 
    c         = vectorize(blade_chords,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 1)  
    delta_r   = vectorize(delta_r,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 1)   
    M         = vectorize(M,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 3)    
    c_0       = vectorize(c_0,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 4)  
    beta_sq   = vectorize(beta_sq,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 4)  
    Omega     = vectorize(Omega,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 4)  
    U_inf     = vectorize(U_inf,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 4)  
    rho       = vectorize(rho,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 4)  
    kine_visc = vectorize(kine_visc,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 4)   

    X   = np.repeat(POS[:,:,:,:,:,:,0,:],2,axis = 6)                                    
    Y   = np.repeat(POS[:,:,:,:,:,:,1,:],2,axis = 6)
    Z   = np.repeat(POS[:,:,:,:,:,:,2,:],2,axis = 6)    
    X_2 = np.repeat(POS_2[:,:,:,:,:,:,0,:],2,axis = 6)
    Y_2 = np.repeat(POS_2[:,:,:,:,:,:,1,:],2,axis = 6)
    Z_2 = np.repeat(POS_2[:,:,:,:,:,:,2,:],2,axis = 6)

    R_s = np.repeat(np.linalg.norm(POS,axis = 6),2,axis = 6)  
    
    # ------------------------------------------------------------
    # ****** BLADE MOTION CALCULATIONS ****** 
    # the rotational Mach number of the blade section 
    frequency = np.linspace(1E2,1E4, BSR)                              
    omega     = 2*pi*frequency                                           
    omega     = vectorize(omega,num_cpt,num_mic,num_sec,num_prop,num_azi,BSR,precision,vectorize_method = 8)     
    r         = np.repeat(r[:,:,:,:,:,:,np.newaxis],2,axis = 6) 
    r         = np.array(r, dtype=precision)         
    c         = np.repeat(c[:,:,:,:,:,:,np.newaxis],2,axis = 6)          
    c         = np.array(c, dtype=precision) 
    delta_r   = np.repeat(delta_r[:,:,:,:,:,:,np.newaxis],2,axis = 6) 
    M         = np.repeat(M,2,axis = 6)            
    M         = np.array(M, dtype=precision)                                
    epsilon   = X**2 + (beta_sq)*(Y**2 + Z**2)                            
    l_r       = 1.6*(0.8*U_inf)/omega  
    omega_d   = omega/(1 +  (Omega*r/c_0)*(X/R_s)) # dopler shifted frequency      
    mu        = omega_d*M/(U_inf*beta_sq)  # omega_d*M/U_inf*beta_p          

    # ------------------------------------------------------------
    # ****** LOADING TERM CALCULATIONS ******   
    # equation 7                          
    K             = omega_d/(0.8*U_inf)                                                  
    bar_K         = K /(c/2)   
    gamma         = np.sqrt(((mu/epsilon)**2)*(X**2 + beta_sq*(Z**2)))                                                         
    bar_gamma     = gamma/(c/2)                                                       
    ss_1, cc_1    = fresnel(2*(bar_K + (mu/(c/2))*M + bar_gamma)) 
    cc_1          = np.array(cc_1, dtype=precision) 
    ss_1          = np.array(ss_1, dtype=precision)                                       
    ss_2, cc_2    = fresnel(2*((mu/(c/2))*X/epsilon + bar_gamma) )   
    cc_2          = np.array(cc_2, dtype=precision) 
    ss_2          = np.array(ss_2, dtype=precision)  
    triangle      = (omega/U_inf)/(c/2) - (mu/(c/2))*X/epsilon + (mu/(c/2))*M                                              
    norm_L_sq     = (1/triangle)*abs(np.exp(1j*2*triangle)*((1 - (1 + 1j)*(cc_1 - 1j*ss_1 ) ) +\
                    ((np.exp(-1j*2*triangle))*(np.sqrt((K + mu*M + gamma)/(mu*X/epsilon +gamma)))*(1 + 1j)*( cc_2 - 1j*ss_2))))                             
    norm_L_sq     = np.array(norm_L_sq, dtype=precision) 
    # ------------------------------------------------------------
    # ****** EMPIRICAL WALL PRESSURE SPECTRUM ******  
    # equation 8                                                 
    beta_c              =  (Theta/tau_w)*dp_dx     
    Delta               = delta/delta_star                                                          
    e                   = 3.7 + 1.5*beta_c                                                          
    d                   = 4.76*((1.4/Delta)**0.75)*(0.375*e - 1)                                               
    a                   = (2.82*(Delta**2)*((6.13*(Delta**(-0.75)) + d)**e))*(4.2*((0.8*((beta_c + 0.5)**(3/4))) /Delta) + 1)  
    mu_tau              = (tau_w/rho)**0.5                                       
    d_star              = d                                                                         
    d_star[beta_c<0.5]  = np.maximum(np.ones_like(mu_tau, dtype=precision)   ,1.5*d)[beta_c<0.5]                                          
    Phi_pp_expression   =  (np.maximum(a, (0.25*beta_c - 0.52)*a)*((omega*delta_star/Ue)**2))/( (4.76*((omega*delta_star/Ue)**0.75) + d_star)**e  +\
                            (8.8*((delta/Ue)/(kine_visc/(mu_tau**2)) **(-0.57))*(omega*delta_star/Ue))** (np.minimum(3*np.ones_like(mu_tau, dtype=precision),(0.139 + 3.1043*beta_c)) + 7 ))                                                     
    Phi_pp              = ((tau_w**2)*delta_star*Phi_pp_expression)/Ue  

    # ------------------------------------------------------------
    # ****** DIRECTIVITY ******      
    #   equation A1 to A5 in Prediction of Urban Air Mobility Multirotor VTOL Broadband Noise Using UCD-QuietFly 

    l_x    = M_hub[:,:,:,:,:,:,0,:]
    l_y    = M_hub[:,:,:,:,:,:,1,:]
    l_z    = M_hub[:,:,:,:,:,:,2,:] 

    A4    = l_y + Y_2 - r*np.sin(beta_p)*np.sin(phi)
    A3    = (np.cos(t_r + t_v))*((np.cos(t_v))*(l_z + Z_2) - (np.sin(t_v))*(l_x + X_2))\
        - np.sin(t_r+ t_v)*((np.cos(t_v))*(l_x + X_2) + (np.sin(t_v))*l_z + Z_2) + r*np.cos(beta_p)
    A2    =  (np.cos(t_r + t_v))*((np.cos(t_v))*(l_x + X_2) + (np.sin(t_v))*(l_z + Z_2))\
        + np.sin(t_r+ t_v)*((np.cos(t_v))*(l_z + Z_2) - (np.sin(t_v))*l_x + X_2) - r*np.cos(phi)*np.cos(beta_p)
    A1    = (np.cos( alpha_eff)*A3 + np.sin( alpha_eff)*np.cos(beta_p)*A4 - np.sin( alpha_eff)*np.sin(beta_p)*A2)**2
    D_phi = A1/( (np.sin( alpha_eff)*A3 - np.cos( alpha_eff)*np.cos(beta_p)*A4 \
                  + np.cos( alpha_eff)*np.sin(beta_p)*A2**2)\
                 + (np.sin(beta_p)*A4 + np.cos(beta_p)*A2)**2)**2 

    # Acousic Power Spectrial Density from each blade - equation 6 
    mult     = ((omega/c_0 )**2)*c**2*delta_r*(1/(32*pi**2))*(B/(2*pi)) 
    mult     = np.array(mult, dtype=precision)     
    S_pp     = mult[:,:,:,:,0,:,:]*np.trapz(D_phi*norm_L_sq*l_r*Phi_pp,axis = 4)
    S_pp_azi = mult*D_phi*norm_L_sq*l_r*Phi_pp

    # equation 9 
    SPL     = 10*np.log10((2*pi*S_pp)/((p_ref)**2))
    SPL_azi = 10*np.log10((2*pi*S_pp_azi)/((p_ref)**2))

    SPL_surf                     = 10**(0.1*SPL[:,:,:,:,:,0]) + 10**(0.1*SPL[:,:,:,:,:,1]) # equation 10 inside brackets 
    SPL_surf_azi                 = 10**(0.1*SPL_azi[:,:,:,:,:,:,0]) + 10**(0.1*SPL_azi[:,:,:,:,:,:,1]) # equation 10 inside brackets
    SPL_rotor                    = 10*np.log10(np.sum(SPL_surf,axis=3))  # equation 10 inside brackets  
    SPL_rotor_azi                = 10*np.log10(np.sum(SPL_surf_azi,axis=3))  # equation 10 inside brackets  
    SPL_rotor_dBA                = A_weighting(SPL_rotor,frequency)  
    SPL_rotor_dBA_azi            = A_weighting(SPL_rotor_azi,frequency) 
     
    # convert to 1/3 octave spectrum   
    f = np.repeat(np.atleast_2d(frequency),num_cpt,axis = 0) 
    
    # azimuthal-averaged sound pressure levels 
    res.p_pref_broadband                              = 10**(SPL_rotor /10) 
    res.p_pref_broadband_dBA                          = 10**(SPL_rotor_dBA /10)  
    res.SPL_prop_broadband_spectrum                   = SPL_rotor   
    res.SPL_prop_broadband_spectrum_dBA               = SPL_rotor_dBA    
    res.SPL_prop_broadband_1_3_spectrum               = SPL_harmonic_to_third_octave(SPL_rotor,f,settings)  
    res.SPL_prop_broadband_1_3_spectrum_dBA           = SPL_harmonic_to_third_octave(SPL_rotor_dBA,f,settings)
    
    # sound pressure levels 
    res.p_pref_azimuthal_broadband                    = 10**(SPL_rotor_azi /10)   
    res.p_pref_azimuthal_broadband_dBA                = 10**(SPL_rotor_dBA_azi /10)  
    res.SPL_prop_azimuthal_broadband_spectrum         = SPL_rotor_azi  
    res.SPL_prop_azimuthal_broadband_spectrum_dBA     = SPL_rotor_dBA_azi
    res.SPL_prop_azimuthal_broadband_1_3_spectrum     = SPL_harmonic_to_third_octave(SPL_rotor_azi,f,settings)       
    res.SPL_prop_azimuthal_broadband_1_3_spectrum_dBA = SPL_harmonic_to_third_octave(SPL_rotor_dBA_azi,f,settings)  
    
    return 

 