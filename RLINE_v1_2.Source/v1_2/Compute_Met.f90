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

      subroutine Compute_Met
! -----------------------------------------------------------------------------------
!     Written by AV and MGS
!     RLINE v1.2, November 2013
!
!     This subroutine calculates sigmav using ustar and wstar
! -----------------------------------------------------------------------------------

      Use Line_Source_Data
      Implicit None

! Local variables:
      Real(kind=double)  :: angle, sigmav_calc

! -----------------------------------------------------------------------------------

! ----Calculate sigmav

      sigmav_calc = sqrt((0.6*wstar)**2+(1.9*ustar)**2) ! sigmav calculated from wstar and ustar
      sigmav      = max(sigmav_calc,0.2)  

      angle       = 270.0 - Wdir
      if (angle>180.0) then            
        angle     = angle - 360.0
      end if
      thetaw      = angle*pi/180.0

      end subroutine
