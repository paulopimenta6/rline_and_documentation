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

      real(kind=8) function sigmaz(xd)
! -----------------------------------------------------------------------------------
!     Written by AV, MGS and DKH
!     RLINE v1.2, November 2013
!
!     Calculates the vertical plume spread including source configuration effects
!
! -----------------------------------------------------------------------------------

      use Line_Source_Data
      implicit None

! Local variables:
      real(kind=double)  :: xd,sigmaz_max,xbar,utemp,xdabs
      real(kind=double)  :: sigz
      real(kind=double)  :: sigmazD         ! depressed roadway
      real(kind=double)  :: sigmazB, HB, dw ! barrier

! Parameters
      real(kind=double)  :: sq2pi=0.797885
!--------------------------------------------------------------------------------

      xbar       = abs(xd/Lmon)
      xdabs      = abs(xd)
      sigmaz_max = sq2pi*zmixed
      sigmazD    = 0.0
      sigmazB    = 0.0
      utemp      = ueff ! use profiled wind speed, Ueff, for Udisp 
      HB         = Source(indq)%hwall
      dw         = (Source(indq)%dCL_wall - Source(indq)%dCL)

! ----vertical dispersion curve 
      if (Lmon>0.0) then     
        sigz = 0.57*(ustar*xdabs/utemp)/(1.0+3.0*(ustar/utemp)*(xbar)**(2.0/3.0))
      else      
        sigz = 0.57*(ustar*xdabs/utemp)*(1.0+1.5*(ustar/utemp*xbar))   
      end  if

      if (op_SC =='Y')then ! Adjustments for near source configurations (depression, barrier) 
! ------DEPRESSED ROADWAY ALGORITHM 
        if (Source(indq)%Depth < 0.0) then ! Add additional dispersion if source is in depression 
          sigmazD = sqrt((Source(indq)%Depth/2.15)**2) 
        end if
! ------END DEPRESSED ROADWAY ALGORITHM
        
! ------BARRIER ALGORITHM 
        if ((HB .GT. 0.0) .AND. (abs(dw) .LT. 11.0*HB)) then ! Add additional init. dispersion for barriers
          sigmazB =0.5*sq2pi*(HB - 0.125*(abs(dw)-3.0*HB))
        end if
! ------END BARRIER ALGORITHM
      end if

      sigz=sqrt(sigmazD*sigmazD+sigz*sigz+sigmaz0*sigmaz0)+sigmazB
      sigmaz=min(sigz,sigmaz_max)
  
      end function