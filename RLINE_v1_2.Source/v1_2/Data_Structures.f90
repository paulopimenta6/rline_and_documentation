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

      module Data_Structures
! -----------------------------------------------------------------------------------
!     Written by AV and MGS
!     RLINE v1.2, November 2013
!
!     Module defining variable types for meteorological, receptor and source variables
!
! -----------------------------------------------------------------------------------

      IMPLICIT NONE

      Integer, Parameter  :: Single=4       ! Compiler dependent value
      Integer, Parameter  :: Double=8       ! Compiler dependent value

      Type AVSurfaceMet  
        Integer(2)         ::  Year
        Integer(2)         ::  Month
        Integer(2)         ::  Day
        Integer(2)         ::  J_Day
        Integer(2)         ::  Hour

        Real(Kind=Double)  ::  Hs           ! Sensible heat flux (W/m2)
        Real(Kind=Double)  ::  Ustar        ! Surface friction velocity (m/s)
        Real(Kind=Double)  ::  Wstar        ! Convective velocity (m/s)

        Real(Kind=Double)  ::  VPTG         ! Vertical potential temperature gradient above CBL
        Real(Kind=Double)  ::  CBL          ! Height of convective PBL (m)
        Real(Kind=Double)  ::  SBL          ! Height of stable PBL (m)

        Real(Kind=Double)  ::  Lmon         ! Monin-Obukhov length (m)
        Real(Kind=Double)  ::  z0           ! Roughness height (m)
        Real(Kind=Double)  ::  Bo           ! Bowen ratio=Sensible_heat_flux/Latent_heat_flux
        Real(Kind=Double)  ::  Alb          ! Albedo

        Real(Kind=Double)  ::  Ws           ! Wind speed (m/s)
        Real(Kind=Double)  ::  Wd           ! Wind direction (degrees)
        Real(Kind=Double)  ::  zref         ! Reference height of wind speed and direction

        Real(Kind=Double)  ::  Temp         ! Temperature(K)
        Real(Kind=Double)  ::  ztemp        ! Reference height for temp (m)
      End Type

      Type AVProfile  
        Integer(2)         ::  Year
        Integer(2)         ::  Month
        Integer(2)         ::  Day
        Integer(2)         ::  Hour

        Real(Kind=Double)  ::  Height       ! Height of measurement (m)  
        Integer(2)         ::  Top          ! =1 if this is highest level, =0 

        Real(Kind=Double)  ::  Wd           ! Wind direction in degrees
        Real(Kind=Double)  ::  Ws           ! Wind speed (m/s)
        Real(Kind=Double)  ::  Temp         ! Temperature (C)  
        Real(Kind=Double)  ::  Stheta       ! Sigma_theta (degrees)
        Real(Kind=Double)  ::  Sigmaw       ! Sigma_w   (m/s)  
      End Type

      Type AVReceptor
        Real(Kind=Double)  ::  Xr           ! X-cordinate
        Real(Kind=Double)  ::  Yr           ! Y-coordinate
        Real(Kind=Double)  ::  Zr           ! Z-cordinate
      End Type

      Type AVSource
        Character(len=40)  :: group         ! stores the group name used for computation and output

        Real(Kind=Double)  ::  Xsb          ! X-cordinate of beginning point (center line for depressed roadway)
        Real(Kind=Double)  ::  Ysb          ! Y-coordinate
        Real(Kind=Double)  ::  Zsb          ! Z-cordinate
                                    
        Real(Kind=Double)  ::  Xse          ! X-cordinate of end point (center line for depressed roadway)
        Real(Kind=Double)  ::  Yse          ! Y-coordinate
        Real(Kind=Double)  ::  Zse          ! Z-cordinate

        Real(Kind=Double)  ::  dCL          ! Distance from center line(offset) 
        Real(Kind=Double)  ::  init_sigmaz  ! intiial vertical spread
        Real(Kind=Double)  ::  Nlanes       ! number of lanes
        Real(Kind=Double)  ::  Qemis        ! Emission rate per unit length of road
  
        Real(Kind=Double)  ::  hwall        ! Barrier height
        Real(Kind=Double)  ::  dCL_wall     ! Barrier Distance from center line  

        Real(Kind=Double)  ::  hwall2       ! Barrier 2 height
        Real(Kind=Double)  ::  dCL_wall2    ! Barrier 2 Distance from center line  

         Real(Kind=Double) ::  Depth        ! Depth of Depression
        Real(Kind=Double)  ::  wTop         ! width of top of depression
        Real(Kind=Double)  ::  wBottom      ! width of bottom of depression
      End Type

      END Module Data_Structures