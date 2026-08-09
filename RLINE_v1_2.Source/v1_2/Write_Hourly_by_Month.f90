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

      subroutine Write_Hourly_by_Month(Surf)
! -----------------------------------------------------------------------------------
!     Written by MGS and DKH
!     RLINE v1.2, November 2013
!
!     Writes the calculated hourly concentrations for each receptor location 
!     and each hour of meteorology (in files organized by month).
!
! -----------------------------------------------------------------------------------

      Use Line_Source_Data
      Implicit None

! Local variables:
      Integer           :: Surf ! input
      Integer           :: Index, Imet,j
      Integer           :: oldmo, mon, lenName
      Integer           :: WriteStatus
      Character(len=40) :: WriteFile
      Character(len=5)  :: ci, ci2
      Character(len=4)  :: suffix
      Character(500)    :: colhead, rowfmt
! -----------------------------------------------------------------------------------
! ----Ititalize
      oldmo = 0 
      mon = 0
  
      do Imet=1, Surf    
        mon = SurfaceMet(Imet)%Month
        if (oldmo .ne. mon) then      
          if (Imet .ne. 1) Close(Unit=25)
! --------create file name
          lenName = len_trim(OutputReceptorFile)
          suffix  = OutputReceptorFile((lenName-3):(lenName+1))
          write(ci,160) mon 
          write(ci2,160) SurfaceMet(Imet)%Year
160       format(I2.2)    
          WriteFile = OutputReceptorFile(1:(lenName-4))// '_' // trim(ci) // '-' // trim(ci2)  //suffix  
    
! --------write header lines
          open(Unit=25, File=WriteFile, Status="Replace", Action="Write", Iostat=WriteStatus)   ! Open file for wriring output

          Write(25,'(A)')RLINEver
          Write(25,'(A,A,A,I0,A)')"SOURCE FILE: ",trim(SourceFileName), " (",Number_Sources, " Sources)"
          Write(25,'(A,A,A,I0,A)')"RECEPTOR FILE: ",trim(ReceptorFileName), " (",Number_Receptors, " Receptors)"
          Write(25,'(A,A)')"SURFACE FILE: ",trim(InputSurfaceFile)
          Write(25,'(A,ES10.3)')"Error Limit: ",Error_Limit
          Write(25,'(A,F10.3,A)')"Displacement Height: ",fac_dispht,"*z0"
          if (op_C =='P') then
            write(25,'(A)') "Concentrations from: Plume"
          elseif (op_C =='M') then
            write(25,'(A)')  "Concentrations from: Meander"
          else
            write(25,'(A)')  "Concentrations from: Plume and Meander"
          end if
          Write(25,'(A,A)')"Roadway configurations used: ",op_SC
          Write(25,'(A,A)')"Roadway #Lanes Option : ",op_width
          if (op_Analytical =='Y') then
            Write(25,'(A)') "Integraton option: Analytical"
          else
            Write(25,'(A)')  "Integraton option: Numerical"
          end if
          Write(25,*)"" 
  
! --------write column headers
          colhead='Year, Julian_Day, Hour, X-Coordinate, Y-Coordinate, Z-Coordinate,'
          do j=1, Number_Groups
            colhead = trim(colhead)//' C_'//trim(Group_Names(j))//','
          end do
          write(25,111)trim(colhead)
111       format (1X,A)
        end if ! end writing headers
    
        write(rowfmt,'(A,i5,A)') '(1X,3(I4,'', ''),3(F12.3,'', ''),',Number_Groups,'(E14.6,'', ''))'
        do Index = 1, Number_Receptors
          write(25,rowfmt)SurfaceMet(Imet)%Year,SurfaceMet(Imet)%J_Day,SurfaceMet(Imet)%Hour, &
                          Receptor(Index)%Xr,Receptor(Index)%Yr, Receptor(Index)%Zr, &
                          (Concentration(Index, Imet,j),j=1,Number_Groups)  
        end do ! end receptor number
        oldmo = SurfaceMet(Imet)%Month
      end do ! end iMet

      end subroutine