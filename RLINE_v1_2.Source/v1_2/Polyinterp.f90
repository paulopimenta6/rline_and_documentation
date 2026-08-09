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

      subroutine polyinterp(y,err,xa,ya,x,n);
! -----------------------------------------------------------------------------------
!     Written by AV
!     RLINE v1.2, November 2013
!
!     Given vectors xa and ya, y is interpolated value for x,err is the error in interpolation. 
!     Uses polynomial interpolation from "Numerical Recipes in Fortran", Press et al., page 103-104
! -----------------------------------------------------------------------------------

      use Line_Source_Data
      implicit none
      
! Parameters
      real(kind=double)  :: eps=1.0e-10
      
! Local variables:
! ----inputs
      integer            :: n            ! Length of xa and ya arrays
      Real(kind=double)  :: x,y          ! y is the interpolated value at x
      Real(kind=double)  :: xa(n), ya(n) ! Table of xa and ya values used in interpolation
! ----output
      Real(kind=double)  :: err
! ----------
      Integer            :: ns           ! Position of x in array
      Integer            :: i, m         ! Counting index 
      Real(kind=double)  :: dif, dift    ! Differences used in calculations
      Real(kind=double)  :: ho, hp, w, den
      Real(kind=double)  :: c(n), d(n)
      Real(kind=double)  :: deltay


! -----------------------------------------------------------------------------------
      deltay = 0.0 ! initialize

      ns = 1   
      dif=abs(x-xa(1))
      do i=1,n
        dift = abs(x-xa(i))
        if (dift<dif) then
          ns  = i
          dif = dift
        end if
        c(i) = ya(i)
        d(i) = ya(i)
      end do
      y  = ya(ns)
      ns = ns-1    
      do m = 1, n-1
        do i = 1, n-m
          ho   = xa(i)-x
          hp   = xa(i+m)-x
          w    = c(i+1)-d(i)
          den  = ho-hp
          d(i) = w*hp/den
          c(i) = w*ho/den
        end do
        if(2*ns<(n-m)) then
          deltay = c(ns+1)
        else
          deltay = d(ns)
          ns = ns-1
        end if
        y=y+deltay
      end do

      err = abs(deltay/(y+eps))
    
      end