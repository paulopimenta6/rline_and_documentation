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

      subroutine Effective_Wind(xd,heff)
! -----------------------------------------------------------------------------------
!     Written by AV, MGS and DKH
!     RLINE v1.2, November 2013
!
!     This function calculates the effective wind speed at mean plume height
!
! -----------------------------------------------------------------------------------

      use Line_Source_Data
      implicit none

! declare erf
      Real(kind=double)             :: erf

! External functions:
      Real(kind=double), external   :: sigmaz, MOST_Wind

! Local variables:
      Real(kind=double),intent(in)  :: xd, heff  ! inputs
      Real(kind=double)             :: sz, sz_new, err, uref, zbar
      Integer                       :: iter

! Parameters
      Real(kind=double), parameter  :: sq2pi = 0.797885
! -----------------------------------------------------------------------------------

      sz=sigmaz(xd)
      err=10
      iter=1
      uref = MOST_Wind(refht,zrough,dispht,ustar,Lmon)
      ueff=MOST_Wind(heff,zrough,dispht,ustar,Lmon)*Wspd/uref
      
      do while ((err>1.0e-02).AND.(iter<20)) 
        zbar = sq2pi*sz*exp(-0.5*(heff/sz)**2)+heff*erf(heff/(sqrt(2.0)*sz))
        ueff=MOST_Wind(max(zbar,heff),zrough,dispht,ustar,Lmon)*Wspd/uref
        ueff=sqrt(2*sigmav**2+ueff**2)
        sz_new=sigmaz(xd)
        err=abs((sz_new-sz)/sz)
        sz=sz_new; iter=iter+1
      end do
  
      end subroutine
