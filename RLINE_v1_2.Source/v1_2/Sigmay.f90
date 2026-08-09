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

      real(kind=8) function sigmay(xd);
! -----------------------------------------------------------------------------------
!     Written by AV, MGS and DKH
!     RLINE v1.2, November 2013
!
!     Calculates the horizontal plume spread
!
! -----------------------------------------------------------------------------------
      use Line_Source_Data
      implicit none

! External functions:
      real(kind=double)    :: sigmaz
! Local variables:
      real(kind=double)    :: xd, sz

! -----------------------------------------------------------------------------------

      sz=sigmaz(xd)
      sz = sqrt(sz**2-sigmaz0**2)
  
      if (Lmon > 0) then ! stable
        sigmay = 1.6*sigmav/ustar*sz*(1.0+2.5*sz/abs(Lmon)) 
      else ! convective
        sigmay = 1.6*sigmav/ustar*sz*(1.0+1.0*sz/abs(Lmon))**(-1.0/2.0) 
      end if

      sigmay = sqrt(sigmay**2+sigmay0**2)

      end function
