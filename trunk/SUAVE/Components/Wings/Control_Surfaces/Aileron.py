## @ingroup Components-Wings-Control_Surfaces
# Aileron.py
#
# Created:  Jan 2020, M. Clarke

# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------

# SUAVE imports
from SUAVE.Components.Wings.Control_Surfaces.Control_Surface import Control_Surface 

# ----------------------------------------------------------------------
#  Attribute
# ----------------------------------------------------------------------
## @ingroup Components-Wings-Control_Surfaces
class Aileron(Control_Surface):
    """This class is used to define ailerons in SUAVE

    Assumptions:
    None

    Source:
    N/A

    Inputs:
    None

    Outputs:
    None

    Properties Used:
    N/A
    """ 
    def __defaults__(self):
        """This sets the default for ailerons in SUAVE.
        
        see Control_Surface().__defaults__ for an explanation of attributes
    
        Assumptions:
        None

        Source:
        N/A

        Inputs:
        None

        Outputs:
        None

        Properties Used:
        N/A
        """ 
        
        self.tag                   = 'aileron'  
        self.hinge_fraction        = 0.0
        self.sign_duplicate        = -1.0
        
        pass 