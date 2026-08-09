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

      subroutine Write_Daily_Ave(Surf)
! -----------------------------------------------------------------------------------
!     Written by MGS and DKH
!     RLINE v1.2, November 2013
!
!     Writes the calculated 24-hr average (calendar day) concentrations for 
!     each receptor location
!
! -----------------------------------------------------------------------------------

      use Line_Source_Data
      implicit none

! Local variables:
      integer                        :: Surf ! input
      integer                        :: Index, Imet, j
      integer                        :: WriteStatus  
      integer                        :: AllocateStatus, Namelen
      integer                        :: CurrentDay, Nhrs
      real(kind=double), Allocatable :: Ctemp(:,:),Cave(:,:)
      character(4)                   :: suffix                    
      character(500)                 :: colhead, rowfmt
      logical                        :: endofday
! -----------------------------------------------------------------------------------
      Namelen            = len_trim(OutputReceptorFile)
      suffix             = OutputReceptorFile((Namelen-3):Namelen)
      OutputReceptorFile = OutputReceptorFile(1:(Namelen-4))//'_DailyAve'//suffix
      
      open(Unit=25, File=OutputReceptorFile, Status="Replace", Action="Write", Iostat=WriteStatus)   ! Open file for writing output
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
        write(25,'(A)')  "Integraton option: Numerical"
      end if
      write(25,*)""   
  
! ----write column headers
      colhead='Year, Julian_Day, # Hours, X-Coordinate, Y-Coordinate, Z-Coordinate,'
      do j=1,Number_Groups
        colhead = trim(colhead)//' C_'//trim(Group_Names(j))//','
      end do
      write(25,111)trim(colhead)
111   format (1X,A)

      allocate(Ctemp(Number_Receptors,Number_Groups),Stat=AllocateStatus)  
      allocate(Cave(Number_Receptors,Number_Groups),Stat=AllocateStatus)
      Currentday=SurfaceMet(1)%J_Day
      Nhrs=0
      Ctemp=0.0
      write(rowfmt,'(A,i5,A)') '(1X,3(I4,'', ''),3(F12.3,'', ''),',Number_Groups,'(E14.6,'', ''))'

      do Imet=1, Surf    
        Call Fill_Met(Imet)  
        
        endofday = .FALSE.
        if(Imet .EQ. Surf) then
          endofday = .TRUE.
        elseif(SurfaceMet(Imet+1)%J_Day .NE. Currentday) then
          endofday = .TRUE.
        endif
        if(endofday) then ! Last hour in CurrentDay
! --------Averge in the last hour of the day, if met data is okay
          if((ustar.GT.0.0).AND.(SurfaceMet(imet)%Hs.NE.-999.0)) then
            do j=1,Number_Groups
              Ctemp(:,j)=Ctemp(:,j)+Concentration(:,Imet,j) 
            end do
            Nhrs=Nhrs+1
          end if
          if (Nhrs.GT.0) then
            Cave=Ctemp/Nhrs
          else
            Cave=-99.0
          end if

! --------Write output
          do Index = 1,Number_Receptors
            write(25,rowfmt)yr, Currentday, Nhrs, Receptor(Index)%Xr,Receptor(Index)%Yr, &
            Receptor(Index)%Zr, (Cave(Index,j), j=1,Number_Groups)      
          end do
          
! --------Reinitialize variables, advance CurrentDay
          if(Imet .NE. Surf)then
            Nhrs=0
            Ctemp=0.0
            CurrentDay=SurfaceMet(Imet+1)%J_Day
          endif
        else ! Not the end of a day...begin or continue averaging
! --------Check  met data for this hour 
          if((ustar.GT.0.0).AND.(SurfaceMet(imet)%Hs .NE. -999.0)) then
            do j=1,Number_Groups
              Ctemp(:,j)=Ctemp(:,j)+Concentration(:,Imet,j)    
            end do
            Nhrs=Nhrs+1
          end if
        end if
      end do

      deallocate(Ctemp)
      deallocate(Cave)       
      close(Unit=25)

      end subroutine

