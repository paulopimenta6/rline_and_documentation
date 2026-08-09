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

      real*8 function MOST_Wind(z,z0,dh,ust,L)
! -----------------------------------------------------------------------------------
!     Written by AV
!     RLINE v1.2, November 2013
!
!     This function calculates the wind speed from similarity theory
! -----------------------------------------------------------------------------------
      use Line_Source_Data
      implicit none

! Local variables:
      real(kind=double) :: z,z0,dh,ust,L  ! height, roughness length, ustar, MO Length
      real(kind=double) :: x1,x2,psi1,psi2

! Parameters
      real(kind=double) :: kappa=0.4
! -----------------------------------------------------------------------------------

      if (dh .ge. z) then
        MOST_Wind = sqrt(2.0)*sigmav
      else
        if (L>0.0) then
          psi1=-17.0*(1-exp(-0.29*(z-dh)/L))  
          psi2=-17.0*(1-exp(-0.29*z0/L))    
        else     
          x1=(1.0-16.0*(z-dh)/L)**0.25; x2=(1.0-16.0*z0/L)**0.25     
          psi1=2.0*log((1.0+x1)/2.0)+log((1.0+x1*x1)/2.0)-2.0*atan(x1)+pi/2.0     
          psi2=2.0*log((1.0+x2)/2.0)+log((1.0+x2*x2)/2.0)-2.0*atan(x2)+pi/2.0     
        end  if
        MOST_Wind=ust*(log((z-dh)/z0)-psi1+psi2)/kappa
      end if

      end function