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

      real*8 function Point_Conc(X,Y,Z)
! -----------------------------------------------------------------------------------
!     Written by AV, MGS and DKH
!     RLINE v1.2, November 2013
!
!     This function calculates the direct plume contribution 
!     of a point source using Gaussian dispersion. Then combines
!     the direct plume and meander contributions to determine
!     the total concentration from a point to the receptor.
!
! -----------------------------------------------------------------------------------
      use Line_Source_Data
      implicit none

! External functions:
      real(kind=double) :: Meander, expx
      real(kind=double) :: sigmay, sigmaz
      
! Local variables:
      real(kind=double) :: X,Y,Z ! inputs
      real(kind=double) :: Conc_m, Conc_p
      real(kind=double) :: sy, sz
      real(kind=double) :: fran
      real(kind=double) :: vert, horz,xd,yd 
      real(kind=double) :: heff

! -----------------------------------------------------------------------------------
! ----Initialize point and meander concentrations
      Conc_p = 0.0
      Conc_m = 0.0
      fran   = 0.0
      sy     = 0.0
      xd     = Xr_rot-X
      heff   = Z  
        
      call Effective_Wind(xd,heff)
    
! ----Calculate direct plume concentration
      if (xd<0.0001) then     
        Conc_p = 0.0   
      else
        xd     = max(xd,xd_min)
        yd     = Yr_rot-Y
        sz     = sigmaz(xd) 
        sy     = sigmay(xd)
        vert   = sqrt(2.0/pi)*(expx(-0.5*((heff-Zrecep)/sz)**2)&
                 +expx(-0.5*((heff+Zrecep)/sz)**2))/(2.0*sz*ueff)
        horz   = 1/(sqrt(2.0*pi)*sy)*expx(-0.5*(yd/sy)**2)
        Conc_p = vert*horz 
      end if

! ----Calculate meander concentration
      fran   = 2.0*sigmav*sigmav/(ueff*ueff)    
      Conc_m = Meander(X,Y,Z)

! ----Combine direct plume and meander contributions
      if (op_C =='M') then
        Point_Conc = Conc_m*fran
      elseif(op_C =='P') then
        Point_Conc = Conc_p*(1-fran)
      else
        Point_Conc = Conc_p*(1-fran)+Conc_m*fran
      end if

      end function
      
