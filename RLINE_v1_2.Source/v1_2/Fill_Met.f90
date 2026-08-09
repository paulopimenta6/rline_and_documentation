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

      subroutine Fill_Met(im)            
! -----------------------------------------------------------------------------------
!     Written by AV and MGS
!     RLINE v1.2, November 2013
!
!     Assigns meteorological values in the surface meteorology 
!     file to global variables
!
! -----------------------------------------------------------------------------------

      Use Line_Source_Data
      Implicit None

! Local variables:
      Integer       :: im

! -----------------------------------------------------------------------------------

! ----Assign Met Variables

      hr=  SurfaceMet(im)%Hour
      dy=SurfaceMet(im)%Day
      mo=SurfaceMet(im)%Month
      yr=SurfaceMet(im)%Year    
      Wspd=SurfaceMet(im)%Ws
      Wdir=SurfaceMet(im)%Wd    
      udisp=SurfaceMet(im)%Ws
      ustar=max(SurfaceMet(im)%Ustar,0.0)
      wstar=max(SurfaceMet(im)%Wstar,0.0)
      Lmon=SurfaceMet(im)%Lmon
      refht=SurfaceMet(im)%zref
      zrough=SurfaceMet(im)%z0
      dispht=fac_dispht*zrough
      zmixed=max(SurfaceMet(im)%SBL,SurfaceMet(im)%CBL)

      end subroutine
! -----------------------------------------------------------------------------------

