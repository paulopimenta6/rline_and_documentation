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

      subroutine Barrier_Displacement(heff)
! -----------------------------------------------------------------------------------
!     Written by MGS and DKH
!     RLINE v1.2, November 2013
!
!     Calculates a vertical displacement of the source to account for the 
!     effect of a roadside barrier.
!     In addition to this subroutine, code for the barrier algorithm resides 
!     in Sigmaz and RLINE_Main.
! -----------------------------------------------------------------------------------

      use Line_Source_Data
      implicit None

! Local variables:
      real(kind=double)  :: heff ! output
      real(kind=double)  :: xd, theta_line, SBDist
      real(kind=double)  :: htwall, fup, dw, m, b, Zave

! -----------------------------------------------------------------------------------

      fup        = 1.5
      htwall     = Source(indq)%hwall
      dw         = (Source(indq)%dCL_wall - Source(indq)%dCL);
      Zave       = (Source(indq)%Zsb+Source(indq)%Zse)/2.0;
      theta_line = atan2(Ysend-Ysbegin,Xsend-Xsbegin)
      SBDist     = dw*sin(theta_line) 

      if(SBDist .GT. 0.0) then ! barrier is downwind of  line
        if((Xsend-Xsbegin) .EQ. 0.0) then ! vertical line 
          xd = abs(Xr_rot-Xsbegin)
        else
          m  = (Ysend-Ysbegin)/(Xsend-Xsbegin)
          b  = (Ysbegin*Xsend-Ysend*Xsbegin)/(Xsend-Xsbegin)
          xd = abs(Yr_rot-m*Xr_rot-b)/sqrt(m*m+1.0) ! perp dist btw source and recep
        end if
        heff = max(Zave,fup*htwall-abs(fup*htwall-dispht)/(2*dw)*xd)
      else
        heff = Zave
      end if
 
      end subroutine