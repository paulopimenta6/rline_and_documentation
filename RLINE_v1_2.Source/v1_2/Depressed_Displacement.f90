! ----------------------------------------------------------------------------------- !
! The Research LINE source (R-LINE) model is in continuous development by various     !
! groups and is based on information from these groups: Federal Government employees, !
! contractors working within a United States Government contract, and non-Federal     !
! sources including research institutions.  These groups give the Government          !
! permission to use, prepare derivative works of, and distribute copies of their work !
! in the R-LINE model to the public and to permit others to do so.  The United States !
! Environmental Protection Agency therefore grants similar permission to use the      !
! R-LINE model, but users are requested to provide copies of derivative works or      !
! products designed to operate in the R-LINE model to the United States Government    !
! without restrictions as to use by others.  Software that is used with the R-LINE    !
! model but distributed under the GNU General Public License or the GNU Lesser        !
! General Public License is subject to their copyright restrictions.                  !
! ----------------------------------------------------------------------------------- !

      real(kind=8) Function Depressed_Displacement(theta_line)
! -----------------------------------------------------------------------------------
!     Written by MGS and DKH
!     RLINE v1.2, November 2013
!
!     Computes transformation for a depressed roadway shifting the roadway upwind, 
!     also compresses or expands the roadways based on the new fractional width and 
!     the distance from the centerline. Other aspects of the depressed roadway 
!     algorithm reside in Sigmaz and Translate_Rotate.
!
! -----------------------------------------------------------------------------------

      use Line_Source_Data
      implicit none

! Local variables:
      real(kind=double)  :: theta_line    ! input
      real(kind=double)  :: Depth, wTop, wBottom, dCL 
      real(kind=double)  :: effD, relD, fracW, effW, theta_rel, Dcrit, F 

! -----------------------------------------------------------------------------------
      Depth     = Source(indq)%Depth
      wBottom   = Source(indq)%wBottom
      wTop      = Source(indq)%wTop     
      dCL       = Source(indq)%dCL

      theta_rel = theta_line-thetaw ! relative angle between roadway and wind direction

      effD      = (wBottom*abs(Depth)+((wTop-wBottom)/2*abs(Depth)))/wTop ! effective Depth
      relD      = effD/wBottom ! relative roadway depth
 
      if (relD .ge. 0.0483) then ! the fractional width is undefined if relD is >= 0.2 
        fracW = 1.0
      else
        fracW =  -0.0776 + sqrt(1.506-7.143*relD)! fractional width
      end if
 
      effW    = fracW**(1.0-(cos(abs(theta_rel))*cos(abs(theta_rel))))*wBottom ! effective width
      Dcrit   = 0.2064*wTop*wBottom/(0.5*(wTop+wBottom))
      F       = min(1.0,wBottom/wTop*(1.0+abs(Depth)/Dcrit))
      
      Depressed_Displacement = ((wTop*F-effW)/2)*((sin(theta_rel))**2)*sign(DBLE(1.0),sin(theta_rel))   &
        -(effW/wBottom*dCL)*sign(DBLE(1.0),sin(theta_line)) ! displacement from starting point

      end function