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

      real*8 function expx(xp);
! -----------------------------------------------------------------------------------
!     Written by AV
!     RLINE v1.2, November 2013
!
!     This function uses a table to compute the exponential function
! -----------------------------------------------------------------------------------

      Use Line_Source_Data
      Implicit None

! Local variables:
      Integer        :: p
      Real(kind=double) :: xp,xpd
! -----------------------------------------------------------------------------------

      xpd=xp
      xpd=max(Xexp(1),xpd)
      p=floor((xpd+20.0)/delexp)+1
      expx=Aexp(p)+Bexp(p)*xpd

    end function
