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

      subroutine  Translate_Rotate
! -----------------------------------------------------------------------------------
!     Written by AV, MGS and DKH
!     RLINE v1.2, November 2013
!
!     This program traslates and rotates the cordinates so that x-axis lies along the wind
!     X0=Xsource(1), Y0=Ysource(1) are the origins of the coordinate system
!     Xs_tran, Ys_tran are the translated coordinates of the source
!     Xs_rot, Ys_rot are the translated coordinates of the source
!     Xr_tran, Yr_tran are the translated coordinates of the receptor
!     Xr_rot, Yr_rot are the translated coordinates of the receptor
!
!     In addition, this subroutine allows the user to specify sources based on a 
!     centerline and the distance from the centerline (dCL).. ie an offset
!
!------------------------------------------------------------------------------------

      Use Line_Source_Data
      Implicit None

! External functions:
      Real(kind=double)  :: Depressed_Displacement

! Local variables:
      Integer            :: index                         ! Counting index
      Real(kind=double)  :: Xr_tran, Yr_tran,theta_line   ! Translated receptor cordinates
      Real(kind=double)  :: Xsb_tran, Ysb_tran, Xse_tran, Yse_tran
      Real(kind=double)  :: dCL                  

! -----------------------------------------------------------------------------------

! ----Translate line source origin

      X0=Source(1)%Xsb    
      Y0=Source(1)%Ysb

! ----Translate source and receptor coordinates and then rotate them along wind direction
  
      do index=1,Number_Sources  
 
! ------Intialize variables used
        dCL=Source(index)%dCL
  
! ------Move initial user coordinate system so the origin is at the begining of first source             
        Xsb_tran   = Source(index)%Xsb-X0
        Ysb_tran   = Source(index)%Ysb-Y0
        Xse_tran   = Source(index)%Xse-X0
        Yse_tran   = Source(index)%Yse-Y0
        theta_line = atan2(Yse_tran-Ysb_tran,Xse_tran-Xsb_tran)

        if (sin(theta_line) .eq. 0) then
          dCL = -dCL ! this is needed for due east lines; it defines + as 
                     ! north for dCL in following equations
        end if

! ------Needed to find the location of the line that is not within a depression,
! ------but is specified in source file with the centerline and distance from the centerline
        if (dCL .ne. 0.0 .and. Source(index)%Depth .eq. 0.0) then 
          Xse_tran = Xse_tran+dCL*sin(theta_line)*sign(DBLE(1.0),sin(theta_line))
          Yse_tran = Yse_tran-dCL*cos(theta_line)*sign(DBLE(1.0),sin(theta_line))
          Xsb_tran = Xsb_tran+dCL*sin(theta_line)*sign(DBLE(1.0),sin(theta_line))
          Ysb_tran = Ysb_tran-dCL*cos(theta_line)*sign(DBLE(1.0),sin(theta_line))
        end if
    
        if (op_SC =='Y')then ! Adjustments for near source configurations (depression)       
! --------DEPRESSED ROADWAY ALGORITHM
          if (Source(index)%Depth < 0.0) then 
            Xse_tran = Xse_tran-Depressed_Displacement(theta_line, index)*sin(theta_line)
            Yse_tran = Yse_tran+Depressed_Displacement(theta_line, index)*cos(theta_line)
            Xsb_tran = Xsb_tran-Depressed_Displacement(theta_line, index)*sin(theta_line)
            Ysb_tran = Ysb_tran+Depressed_Displacement(theta_line, index)*cos(theta_line)
          end if
! --------END DEPRESSED ROADWAY ALGORITHM
        end if

        Xsb_rot(index) =  Xsb_tran*cos(thetaw)+Ysb_tran*sin(thetaw)    
        Ysb_rot(index) = -Xsb_tran*sin(thetaw)+Ysb_tran*cos(thetaw)
        Xse_rot(index) =  Xse_tran*cos(thetaw)+Yse_tran*sin(thetaw)
        Yse_rot(index) = -Xse_tran*sin(thetaw)+Yse_tran*cos(thetaw)  
      end do

      do index=1,Number_Receptors
        Xr_tran         =  Receptor(index)%Xr-X0
        Yr_tran         =  Receptor(index)%Yr-Y0
        Xrcp_rot(index) =  Xr_tran*cos(thetaw)+Yr_tran*sin(thetaw)
        Yrcp_rot(index) = -Xr_tran*sin(thetaw)+Yr_tran*cos(thetaw)
      end do 

      end subroutine
