## @ingroup Methods-Propulsion-Rotor_Wake-Fidelity_One
# generate_fidelity_one_wake_shape.py
#
# Created:  Jan 2022, R. Erhard
# Modified: 

# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------
from SUAVE.Core import Data
from SUAVE.Methods.Geometry.Two_Dimensional.Cross_Section.Airfoil.import_airfoil_geometry import import_airfoil_geometry 
from SUAVE.Methods.Propulsion.Rotor_Wake.Fidelity_Zero.compute_wake_contraction_matrix import compute_wake_contraction_matrix


# package imports
from jax import numpy as jnp


## @ingroup Methods-Propulsion-Rotor_Wake-Fidelity_One
def generate_fidelity_one_wake_shape(wake,rotor):
    """
    This generates the propeller wake control points and vortex distribution that make up the prescribed vortex wake. 
    All (x,y,z) coordinates are in the vehicle frame of reference (X points nose to tail).
    
    Assumptions:
       None
    
    Source: 
       None
    
    Inputs:
       rotor  -  A SUAVE rotor component for which the wake is generated
    
    """
        
    # Unpack rotor
    R                = rotor.tip_radius
    r                = rotor.radius_distribution 
    c                = rotor.chord_distribution 
    beta             = rotor.twist_distribution
    B                = rotor.number_of_blades  
    
    rotor_outputs    = rotor.outputs
    Na               = int(rotor_outputs.number_azimuthal_stations)
    Nr               = int(rotor_outputs.number_radial_stations)
    omega            = rotor_outputs.omega                               
    va               = rotor_outputs.disc_axial_induced_velocity 
    V_inf            = rotor_outputs.velocity
    gamma            = rotor_outputs.disc_circulation   
    rot              = rotor.rotation
    
    # apply rotation direction to twist and chord distribution
    c    = -rot*c
    beta = -rot*beta
    
    # dimensions for analysis                      
    Nr   = len(r)                   # number of radial stations
    m    = len(omega)                # number of control points
    B    = int(B)

    # Compute blade angles starting from each of Na azimuthal stations, shape: (Na,B)
    azi          = jnp.linspace(0,2*jnp.pi,Na+1)[:-1]
    azi_initial  = jnp.atleast_2d(jnp.linspace(0,2*jnp.pi,B+1)[:-1])
    blade_angles = (azi_initial + jnp.atleast_2d(azi).T) 
    
    # Extract specified wake settings:
    init_timestep_offset = wake.wake_settings.initial_timestep_offset
    n_rotations          = wake.wake_settings.number_rotor_rotations
    tsteps_per_rot       = wake.wake_settings.number_steps_per_rotation
    
    # Calculate additional wake properties
    dt    = (azi[1]-azi[0])/omega[0][0]
    nts   = int(tsteps_per_rot*n_rotations)
    dt    = int(dt)
    
    # Compute properties for each wake timestep
    ts                = jnp.linspace(0,dt*(nts-1),nts) 
    omega_ts          = jnp.multiply(omega,jnp.atleast_2d(ts))  # Angle of each azimuthal station in nts
    
    # Update start angle of rotor
    t0                = dt*init_timestep_offset
    start_angle       = omega[0]*t0 
    rotor.start_angle = start_angle[0]
    
    # extract mean inflow velocities
    axial_induced_velocity = jnp.mean(va,axis = 2) # radial inflow, averaged around the azimuth
    mean_induced_velocity  = jnp.mean( axial_induced_velocity,axis = 1)   

    alpha = rotor.orientation_euler_angles[1]
    rots  = jnp.array([[jnp.cos(alpha), 0, jnp.sin(alpha)], [0,1,0], [-jnp.sin(alpha), 0, jnp.cos(alpha)]])
    
    lambda_tot   = jnp.atleast_2d((jnp.dot(V_inf,rots[0])  + mean_induced_velocity)).T /(omega*R)   # inflow advance ratio (page 99 Leishman)
    mu_prop      = jnp.atleast_2d(jnp.dot(V_inf,rots[2])).T /(omega*R)                              # rotor advance ratio  (page 99 Leishman) 
    Vx           = jnp.repeat(V_inf[:,0,None], Nr, axis=1) # shape: (m,Nr)
    Vz           = jnp.repeat(V_inf[:,2,None], Nr, axis=1) # shape: (m,Nr)
    V_prop       = jnp.sqrt((Vx  + axial_induced_velocity)**2 + Vz**2)

    # wake skew angle 
    wake_skew_angle = -(jnp.arctan(mu_prop/lambda_tot))
    wake_skew_angle = jnp.tile(wake_skew_angle[:,:,None],(1,Nr,nts))
    
    # reshape gamma to find the average between stations           
    gamma_new = (gamma[:,:-1,:] + gamma[:,1:,:])*0.5  # [control points, Nr-1, Na ] one less radial station because ring
    
    num       = Na//B
    time_idx  = jnp.arange(nts)
    Gamma     = jnp.zeros((Na,m,B,Nr-1,nts))
    
    # generate Gamma for each start angle
    for ito in range(Na):
        t_idx     = jnp.atleast_2d(time_idx).T 
        B_idx     = jnp.arange(B) 
        B_loc     = (ito + B_idx*num - t_idx )%Na 
        Gamma1    = gamma_new[:,:,B_loc]  
        Gamma1    = Gamma1.transpose(0,3,1,2) 
        Gamma     = Gamma.at[ito,:,:,:,:].set(Gamma1)
  
    # --------------------------------------------------------------------------------------------------------------
    #    ( control point , blade number , radial location on blade , time step )
    # --------------------------------------------------------------------------------------------------------------
    V_p = jnp.repeat(V_prop[:,:,None],len(ts),axis=2)
                    
    sx_inf0            = jnp.multiply(V_p*jnp.cos(wake_skew_angle), jnp.repeat(jnp.atleast_2d(ts)[:,None,:],Nr,axis=1))
    sx_inf             = jnp.tile(sx_inf0[None,:, None, :,:], (Na,1,B,1,1))
                      
    sy_inf0            = jnp.multiply(jnp.atleast_2d(V_inf[:,1]).T,jnp.atleast_2d(ts)) # = zero since no crosswind
    sy_inf             = -rot*jnp.tile(sy_inf0[None,:, None, None,:], (Na,1,B,Nr,1)) 
    
    sz_inf0            = jnp.multiply(V_p*jnp.sin(wake_skew_angle),jnp.repeat(jnp.atleast_2d(ts)[:,None,:],Nr,axis=1))
    sz_inf             = jnp.tile(sz_inf0[None,:, None, :,:], (Na,1,B,1,1))        
    
    # wake panel and blade angles
    start_angle_offset = jnp.tile(start_angle[None,:,None,None,None], (Na,1,B,Nr,nts))
    blade_angle_loc    = start_angle_offset + jnp.tile( blade_angles[:,None,:,None,None], (1,m,1,Nr,nts))  # negative rotation, positive blade angle location
    
    # offset angle of trailing wake panels relative to blade location
    total_angle_offset = jnp.tile(omega_ts[None,:,None,None,:], (Na,1,B,Nr,1))   
    
    # azimuthal position of each wake panel, (blade start index, ctrl_pts, B, Nr, nts)
    panel_azimuthal_positions = rot*(total_angle_offset - blade_angle_loc)      # axial view in rotor frame (angle 0 aligned with z-axis); 
    
    # put into velocity frame and find (y,z) components
    azi_y   = jnp.sin(panel_azimuthal_positions)
    azi_z   = jnp.cos(panel_azimuthal_positions)
    

    # extract airfoil trailing edge coordinates for initial location of vortex wake
    a_sec        = rotor.airfoil_geometry   
    a_secl       = jnp.array(rotor.airfoil_polar_stations)
    airfoil_data = import_airfoil_geometry(a_sec,npoints=100)  
   
    # trailing edge points in airfoil coordinates
    xupper         = jnp.take(jnp.array(airfoil_data.x_upper_surface),a_secl,axis=0)
    yupper         = jnp.take(jnp.array(airfoil_data.y_upper_surface),a_secl,axis=0)   
    
    # Align the quarter chords of the airfoils (zero sweep)
    airfoil_le_offset = -c/2
    xte_airfoils      = xupper[:,-1]*c + airfoil_le_offset
    yte_airfoils      = yupper[:,-1]*c 
    
    xle_airfoils = xupper[:,0]*c + airfoil_le_offset
    yle_airfoils = yupper[:,0]*c 
    
    
    x_c_4_airfoils = (xle_airfoils - xte_airfoils)/4 - airfoil_le_offset
    y_c_4_airfoils = (yle_airfoils - yte_airfoils)/4
    
    # apply blade twist rotation along rotor radius
    xte_twisted = jnp.cos(beta)*xte_airfoils - jnp.sin(beta)*yte_airfoils        
    yte_twisted = jnp.sin(beta)*xte_airfoils + jnp.cos(beta)*yte_airfoils    
    
    x_c_4_twisted = jnp.cos(beta)*x_c_4_airfoils - jnp.sin(beta)*y_c_4_airfoils 
    y_c_4_twisted = jnp.sin(beta)*x_c_4_airfoils + jnp.cos(beta)*y_c_4_airfoils  
    
    # transform coordinates from airfoil frame to rotor frame
    xte = jnp.tile(jnp.atleast_2d(yte_twisted), (B,1))
    xte_rotor = jnp.tile(xte[None,:,:,None], (m,1,1,nts))  
    yte_rotor = -jnp.tile(xte_twisted[None,None,:,None],(m,B,1,1))*jnp.cos(panel_azimuthal_positions)
    zte_rotor = jnp.tile(xte_twisted[None,None,:,None],(m,B,1,1))*jnp.sin(panel_azimuthal_positions)
    
    r_4d = jnp.tile(r[None,None,:,None], (m,B,1,nts))
    
    x0 = 0
    y0 = r_4d*azi_y
    z0 = r_4d*azi_z
    
    x_pts0 = x0 + xte_rotor
    y_pts0 = y0 + yte_rotor
    z_pts0 = z0 + zte_rotor
    
    x_c_4_rotor = x0 - jnp.tile(y_c_4_twisted[None,None,:,None], (m,B,1,nts))
    y_c_4_rotor = y0 + jnp.tile(x_c_4_twisted[None,None,:,None], (m,B,1,nts))*jnp.cos(panel_azimuthal_positions)
    z_c_4_rotor = z0 - jnp.tile(x_c_4_twisted[None,None,:,None], (m,B,1,nts))*jnp.sin(panel_azimuthal_positions)   
    
    # compute wake contraction, apply to y-z plane
    X_pts0           = x_pts0 + sx_inf
    wake_contraction = compute_wake_contraction_matrix(rotor,Nr,m,nts,X_pts0,rotor_outputs) 
    Y_pts0           = y_pts0*wake_contraction + sy_inf
    Z_pts0           = z_pts0*wake_contraction + sz_inf
    
    # append propeller wake to each of its repeated origins  
    X_pts   = rotor.origin[0][0] + X_pts0  
    Y_pts   = rotor.origin[0][1] + Y_pts0
    Z_pts   = rotor.origin[0][2] + Z_pts0

    #------------------------------------------------------     
    # Account for lifting line panels
    #------------------------------------------------------
    x_c_4 = jnp.repeat(x_c_4_rotor[None,:,:,:,:], Na, axis=0) + rotor.origin[0][0]
    y_c_4 = (y_c_4_rotor) + rotor.origin[0][1]
    z_c_4 = (z_c_4_rotor) + rotor.origin[0][2]
    
    # prepend points at quarter chord to account for rotor lifting line
    X_pts = jnp.append(x_c_4[:,:,:,:,0][:,:,:,:,None], X_pts, axis=4) 
    Y_pts = jnp.append(y_c_4[:,:,:,:,0][:,:,:,:,None], Y_pts, axis=4)
    Z_pts = jnp.append(z_c_4[:,:,:,:,0][:,:,:,:,None], Z_pts, axis=4)

    #------------------------------------------------------
    # Store points  
    #------------------------------------------------------
    # Initialize vortex distribution and arrays with required matrix sizes
    VD = Data()
    rotor.vortex_distribution = VD        
    VD, WD = initialize_distributions(Nr, Na, B, nts, m,VD)
    
    # ( azimuthal start index, control point  , blade number , location on blade, time step )
    if rot==-1:
        # panels ordered root to tip, A for inner-most panel edge
        VD.Wake.XA1 = VD.Wake.XA1.at[:,:,0:B,:,:].set(X_pts[:, : , :, :-1 , :-1 ])
        VD.Wake.YA1 = VD.Wake.YA1.at[:,:,0:B,:,:].set(Y_pts[:, : , :, :-1 , :-1 ])
        VD.Wake.ZA1 = VD.Wake.ZA1.at[:,:,0:B,:,:].set(Z_pts[:, : , :, :-1 , :-1 ])
        VD.Wake.XA2 = VD.Wake.XA2.at[:,:,0:B,:,:].set(X_pts[:, : , :, :-1 ,  1: ])
        VD.Wake.YA2 = VD.Wake.YA2.at[:,:,0:B,:,:].set(Y_pts[:, : , :, :-1 ,  1: ])
        VD.Wake.ZA2 = VD.Wake.ZA2.at[:,:,0:B,:,:].set(Z_pts[:, : , :, :-1 ,  1: ])
        VD.Wake.XB1 = VD.Wake.XB1.at[:,:,0:B,:,:].set(X_pts[:, : , :, 1:  , :-1 ])
        VD.Wake.YB1 = VD.Wake.YB1.at[:,:,0:B,:,:].set(Y_pts[:, : , :, 1:  , :-1 ])
        VD.Wake.ZB1 = VD.Wake.ZB1.at[:,:,0:B,:,:].set(Z_pts[:, : , :, 1:  , :-1 ])
        VD.Wake.XB2 = VD.Wake.XB2.at[:,:,0:B,:,:].set(X_pts[:, : , :, 1:  ,  1: ])
        VD.Wake.YB2 = VD.Wake.YB2.at[:,:,0:B,:,:].set(Y_pts[:, : , :, 1:  ,  1: ])
        VD.Wake.ZB2 = VD.Wake.ZB2.at[:,:,0:B,:,:].set(Z_pts[:, : , :, 1:  ,  1: ])
    else:            
        # positive rotation reverses the A,B nomenclature of the panel
        VD.Wake.XA1 = VD.Wake.XA1.at[:,:,0:B,:,:].set(X_pts[:, : , :, 1: , :-1 ])
        VD.Wake.YA1 = VD.Wake.YA1.at[:,:,0:B,:,:].set(Y_pts[:, : , :, 1: , :-1 ])
        VD.Wake.ZA1 = VD.Wake.ZA1.at[:,:,0:B,:,:].set(Z_pts[:, : , :, 1: , :-1 ])
        VD.Wake.XA2 = VD.Wake.XA2.at[:,:,0:B,:,:].set(X_pts[:, : , :, 1: ,  1: ])
        VD.Wake.YA2 = VD.Wake.YA2.at[:,:,0:B,:,:].set(Y_pts[:, : , :, 1: ,  1: ])
        VD.Wake.ZA2 = VD.Wake.ZA2.at[:,:,0:B,:,:].set(Z_pts[:, : , :, 1: ,  1: ])
        VD.Wake.XB1 = VD.Wake.XB1.at[:,:,0:B,:,:].set(X_pts[:, : , :, :-1  , :-1 ])
        VD.Wake.YB1 = VD.Wake.YB1.at[:,:,0:B,:,:].set(Y_pts[:, : , :, :-1  , :-1 ])
        VD.Wake.ZB1 = VD.Wake.ZB1.at[:,:,0:B,:,:].set(Z_pts[:, : , :, :-1  , :-1 ])
        VD.Wake.XB2 = VD.Wake.XB2.at[:,:,0:B,:,:].set(X_pts[:, : , :, :-1  ,  1: ])
        VD.Wake.YB2 = VD.Wake.YB2.at[:,:,0:B,:,:].set(Y_pts[:, : , :, :-1  ,  1: ])
        VD.Wake.ZB2 = VD.Wake.ZB2.at[:,:,0:B,:,:].set(Z_pts[:, : , :, :-1  ,  1: ])
        

    VD.Wake.GAMMA = VD.Wake.GAMMA.at[:,:,0:B,:,:].set(Gamma) 
    
    # Append wake geometry and vortex strengths to each individual propeller
    wake.wake_vortex_distribution   = VD.Wake
    
    # append trailing edge locations
    wake.wake_vortex_distribution.Xblades_te = X_pts[:,0,:,:,0]
    wake.wake_vortex_distribution.Yblades_te = Y_pts[:,0,:,:,0]
    wake.wake_vortex_distribution.Zblades_te = Z_pts[:,0,:,:,0]

    # append quarter chord lifting line point locations        
    wake.wake_vortex_distribution.Xblades_c_4 = x_c_4_rotor 
    wake.wake_vortex_distribution.Yblades_c_4 = y_c_4_rotor
    wake.wake_vortex_distribution.Zblades_c_4 = z_c_4_rotor
    
    # append three-quarter chord evaluation point locations        
    wake.wake_vortex_distribution.Xblades_cp = x_c_4 
    wake.wake_vortex_distribution.Yblades_cp = y_c_4 
    wake.wake_vortex_distribution.Zblades_cp = z_c_4 

    # Compress Data into 1D Arrays  
    mat6_size = (Na,m,nts*B*(Nr-1)) 

    WD.XA1    =  jnp.reshape(VD.Wake.XA1,mat6_size)
    WD.YA1    =  jnp.reshape(VD.Wake.YA1,mat6_size)
    WD.ZA1    =  jnp.reshape(VD.Wake.ZA1,mat6_size)
    WD.XA2    =  jnp.reshape(VD.Wake.XA2,mat6_size)
    WD.YA2    =  jnp.reshape(VD.Wake.YA2,mat6_size)
    WD.ZA2    =  jnp.reshape(VD.Wake.ZA2,mat6_size)
    WD.XB1    =  jnp.reshape(VD.Wake.XB1,mat6_size)
    WD.YB1    =  jnp.reshape(VD.Wake.YB1,mat6_size)
    WD.ZB1    =  jnp.reshape(VD.Wake.ZB1,mat6_size)
    WD.XB2    =  jnp.reshape(VD.Wake.XB2,mat6_size)
    WD.YB2    =  jnp.reshape(VD.Wake.YB2,mat6_size)
    WD.ZB2    =  jnp.reshape(VD.Wake.ZB2,mat6_size)
    WD.GAMMA  =  jnp.reshape(VD.Wake.GAMMA,mat6_size)
    
    rotor.wake_skew_angle = wake_skew_angle
    WD.reshaped_wake = wake.wake_vortex_distribution
            
       
    return WD

## @ingroup Methods-Propulsion-Rotor_Wake-Fidelity_One
def initialize_distributions(Nr, Na, B, n_wts, m, VD):
    """
    Initializes the matrices for the wake vortex distributions.
    
    Assumptions:
        None

    Source:
        N/A
        
    Inputs:
       Nr    - number of radial blade elemnts
       Na    - number of azimuthal start positions
       B     - number of rotor blades
       n_wts - total number of wake time steps in wake simulation
       m     - number of control points to evaluate
       VD    - vehicle vortex distribution
       
    Outputs:
       VD  - Vortex distribution
       WD  - Wake vortex distribution
    
    Properties:
       N/A
       
    """
    nmax = Nr - 1 # one less vortex ring than blade elements
    
    VD.Wake       = Data()
    mat1_size     = (Na,m,B,nmax,n_wts)
    VD.Wake.XA1   = jnp.zeros(mat1_size) 
    VD.Wake.YA1   = jnp.zeros(mat1_size) 
    VD.Wake.ZA1   = jnp.zeros(mat1_size) 
    VD.Wake.XA2   = jnp.zeros(mat1_size) 
    VD.Wake.YA2   = jnp.zeros(mat1_size) 
    VD.Wake.ZA2   = jnp.zeros(mat1_size)    
    VD.Wake.XB1   = jnp.zeros(mat1_size) 
    VD.Wake.YB1   = jnp.zeros(mat1_size) 
    VD.Wake.ZB1   = jnp.zeros(mat1_size) 
    VD.Wake.XB2   = jnp.zeros(mat1_size) 
    VD.Wake.YB2   = jnp.zeros(mat1_size) 
    VD.Wake.ZB2   = jnp.zeros(mat1_size) 
    VD.Wake.GAMMA = jnp.zeros(mat1_size)  
      
    WD        = Data()
    mat2_size = (Na,m*n_wts*B*nmax)
    WD.XA1    = jnp.zeros(mat2_size)
    WD.YA1    = jnp.zeros(mat2_size)
    WD.ZA1    = jnp.zeros(mat2_size)
    WD.XA2    = jnp.zeros(mat2_size)
    WD.YA2    = jnp.zeros(mat2_size)
    WD.ZA2    = jnp.zeros(mat2_size)   
    WD.XB1    = jnp.zeros(mat2_size)
    WD.YB1    = jnp.zeros(mat2_size)
    WD.ZB1    = jnp.zeros(mat2_size)
    WD.XB2    = jnp.zeros(mat2_size)
    WD.YB2    = jnp.zeros(mat2_size)
    WD.ZB2    = jnp.zeros(mat2_size) 

 
    return VD, WD