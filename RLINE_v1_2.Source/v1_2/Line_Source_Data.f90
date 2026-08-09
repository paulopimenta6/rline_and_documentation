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

      module Line_Source_Data
! ---------------------------------------------------------------------------------------------
!     Written by AV, MGS and DKH
!     RLINE v1.2, Nov 2013
!
!     This module contains the variables required by the line source algorithm
! -----------------------------------------------------------------------------------------
      use Data_Structures

      character(len=12)    :: RLINEver = "RLINEv1_2" ! RLINE version name, used in aALL "write files".

! Inputs:

! Meteorology
      character(len=50)    :: InputSurfaceFile    ! Name of text file that needs to be converted 
      real(kind=double)    :: Wspd,Wdir,ustar,udisp,Lmon,wstar,sigmav,zmixed                          
      real(kind=double)    :: refht,zrough,dispht,ueff
      integer              :: hr,dy,mo,yr
      real(kind=double)    :: thetaw              ! wind direction in geometrical notation
      type(AVSurfaceMet), allocatable :: SurfaceMet(:)  ! Array of surface records
      type(AVProfile),    allocatable :: Profile(:)     ! Array of profile records

! Main input file
      character(len=40)    :: SourceFileName
      character(len=40)    :: OutputReceptorFile
      real(kind=double)    :: Error_Limit
      real(kind=double)    :: fac_dispht ! dispht=fac_dispht*zrough
      character(len=2)     :: op_C
      character(len=2)     :: op_ave
      character(len=2)     :: op_monthly
      character(len=2)     :: op_Analytical
      character(len=2)     :: op_SC
      character(len=2)     :: op_width
      character(len=2)     :: op_warn

! Source file
      real(kind=double)    :: sigmay0,sigmaz0, hrelease ! initial sigmay,initial sigmaz and source height
      real(kind=double)    :: width;              ! standard roadwidth
      real(kind=double)    :: Xsbegin, Ysbegin, Zsbegin ! begining points of line source
      real(kind=double)    :: Xsend, Ysend, Zsend       ! end points of line source
      integer              :: Number_Sources, Number_Groups
      integer              :: indq                      ! index of source used
      type(AVSource),    allocatable  :: Source(:)      ! Array of sources
      character(len=40), allocatable  :: Group_Names(:) ! stores group names
      integer,           allocatable  :: Group_Array(:,:) ! stores original soucre numbers for each group
    
! Receptor file
      character(len=40)    :: ReceptorFileName
      integer              :: Number_Receptors
      type(AVReceptor),  allocatable  :: Receptor(:)    ! Array of receptors
    
! Parameters used in computation
      Real(kind=double), Parameter    :: pi=3.14159265358979  ! Value of pi
      Real(kind=double), parameter    :: sm_num=1.0e-8, xd_min=1.0    
    
! Variables used in computation
      Real(kind=double)    :: Xexp(1000), Aexp(1000), Bexp(1000),delexp  ! Exponential lookup table
      Real(kind=double)    :: Xrecep, Yrecep, Zrecep    ! Dummy receptor cordinates
      Real(kind=double), Allocatable  :: Xrcp_rot(:), Yrcp_rot(:)  ! Rotated receptor coordinates
      Real(kind=double)    :: X0, Y0                    ! Origin of system 
      Real(kind=double)    :: Xr_rot, Yr_rot            ! Roatated receptor cordinates
      Real(kind=double), Allocatable  :: Xsb_rot(:), Ysb_rot(:),Xse_rot(:), Yse_rot(:) ! Rotated source coordinates
      Real(kind=double), Allocatable  :: Concentration(:,:,:)   ! Concentration at receptors  

      End Module Line_Source_Data