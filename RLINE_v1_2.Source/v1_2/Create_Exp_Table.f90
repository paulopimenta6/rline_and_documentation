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

      subroutine Create_Exp_Table
! -----------------------------------------------------------------------------------
!     Written by AV
!     RLINE v1.2, November 2013
!
!     Creates a look-up table based on arguments of the built-in 
!     exponential function to improve computation time.
!
! -----------------------------------------------------------------------------------

      Use Line_Source_Data        ! Include Data
      Implicit None

! Local variables:
      Integer          :: ind
      Real(kind=double)    :: ext(1000) 
  
! -----------------------------------------------------------------------------------
    
      delexp=20.0/999.0;
      Xexp(1)=-20.0
      ext(1)=exp(Xexp(1))

      do ind=2,1000
        Xexp(ind)=Xexp(ind-1)+delexp
        ext(ind)=exp(Xexp(ind))
      end do

      do ind=1,999
        Bexp(ind)=(ext(ind+1)-ext(ind))/(Xexp(ind+1)-Xexp(ind))
        Aexp(ind)=ext(ind)-Bexp(ind)*Xexp(ind)
      end Do

      Bexp(1000)=Bexp(999); Aexp(1000)=Aexp(999)

      end subroutine



