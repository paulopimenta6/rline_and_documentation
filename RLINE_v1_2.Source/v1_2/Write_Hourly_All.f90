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

      subroutine Write_Hourly_All(Surf)
! -----------------------------------------------------------------------------------
!     Written by AV, MGS and DKH
!     RLINE v1.2, November 2013
!
!     Writes the calculated hourly concentrations for each receptor location 
!     and each hour of meteorology (all in one file).
!
! -----------------------------------------------------------------------------------

      use Line_Source_Data
      implicit None

! Local variables:
      integer         :: Surf  ! input
      integer         :: Index, Imet, j
      integer         :: WriteStatus
      character(500)  :: colhead, rowfmt
! -----------------------------------------------------------------------------------
      open(Unit=25, File=OutputReceptorFile, Status="Replace", Action="Write", Iostat=WriteStatus)   ! Open file for wriring output
      write(25,'(A)')RLINEver
      write(25,'(A,A,A,I0,A)')"SOURCE FILE: ",trim(SourceFileName), " (",Number_Sources, " Sources)"
      write(25,'(A,A,A,I0,A)')"RECEPTOR FILE: ",trim(ReceptorFileName), " (",Number_Receptors, " Receptors)"
      write(25,'(A,A)')"SURFACE FILE: ",trim(InputSurfaceFile)
      write(25,'(A,ES10.3)')"Error Limit: ",Error_Limit
      write(25,'(A,F10.3,A)')"Displacement Height: ",fac_dispht,"*z0"
      if (op_C =='P') then
        write(25,'(A)') "Concentrations from: Plume"
      elseif (op_C =='M') then
        write(25,'(A)')  "Concentrations from: Meander"
      else
        write(25,'(A)')  "Concentrations from: Plume and Meander"
      end if
      write(25,'(A,A)')"Roadway configurations used: ",op_SC
      write(25,'(A,A)')"Roadway #Lanes Option : ",op_width
      
      if (op_Analytical =='Y') then
        write(25,'(A)') "Integraton option: Analytical"
      else
        write(25,'(A)') "Integraton option: Numerical"
      end if
      write(25,*)""   
  
! ----write column headers
      colhead='Year, Julian_Day, Hour, X-Coordinate, Y-Coordinate, Z-Coordinate,'
      do j=1,Number_Groups
        colhead = trim(colhead)//' C_'//trim(Group_Names(j))//','
      end do
      write(25,111)trim(colhead)
111   format (1X,A)

      write(rowfmt,'(A,i5,A)') '(1X,3(I4,'', ''),3(F12.3,'', ''),',Number_Groups,'(E14.6,'', ''))'
      do Imet=1, Surf    
        do Index = 1,Number_Receptors
          write(25,rowfmt)SurfaceMet(Imet)%Year,SurfaceMet(Imet)%J_Day,SurfaceMet(Imet)%Hour, &
          Receptor(Index)%Xr,Receptor(Index)%Yr, Receptor(Index)%Zr, &
          (Concentration(Index, Imet,j),j=1,Number_Groups)      
        end do
      end do

      close(Unit=25)

      end subroutine