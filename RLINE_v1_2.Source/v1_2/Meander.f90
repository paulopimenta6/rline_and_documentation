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

      real(kind=8) function Meander(X,Y,Z)
! -----------------------------------------------------------------------------------
!     Written by AV, MGS and DKH
!     RLINE v1.2, November 2013
!
!     This function calculates the contribution of a point source at (X,Y,Z)
!     to a receptor at (Xr_rot,Yr_rot,Zrcp) assuming that the material
!     spreads out radially in all directions
! -----------------------------------------------------------------------------------

      use Line_Source_Data
      implicit none

! External functions:
      Real(kind=double)  :: sigmaz, expx
! Local variables:
      Real(kind=double)  :: X, Y,Z   ! inputs
      Real(kind=double)  :: R, Vert, Horz, sz, heff

! -----------------------------------------------------------------------------------
 
      R       = sqrt((Xr_rot-X)**2+(Yr_rot-Y)**2) ! This is the radial distance to the receptor   
      R       = max(R,xd_min)
      heff    = Z 
      call Effective_Wind(R,heff)
      sz      = sigmaz(R) ! Effective sigmaz
      Vert    = sqrt(2.0/pi)*(expx(-0.5*((heff-Zrecep)/sz)**2)&
                +expx(-0.5*((heff+Zrecep)/sz)**2))/(2.0*sz*ueff)  ! Accounts for source height
      Horz    = 1.0/(2.0*pi*R);
      Meander = Vert*Horz;
     
      end function
