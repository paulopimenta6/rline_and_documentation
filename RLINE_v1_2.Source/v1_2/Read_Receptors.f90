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

      subroutine Read_Receptors
! -----------------------------------------------------------------------------------
!     Written by AV, MGS and DKH
!     RLINE v1.2, November 2013
!
!     Reads inputs from receptor file
!
!  ----------------------------------------------------------------------------------

      Use Data_Structures
      Use Line_Source_Data                      ! Include library
      Implicit None

! Local variables:
      Integer             ::    index, Size     ! Index used to read met information
      Integer             ::    AllocateStatus  ! Integer that indicates read status
      Integer             ::    ReadStatus      ! Integer that indicates read status
      Character(len=200)  ::    testread        ! dummy variable for testing input lines for comments
! -----------------------------------------------------------------------------------
    
      Call Compute_File_Size(Size, ReceptorFileName)
      Number_Receptors=Size-3
      Allocate(Receptor(Number_Receptors),Stat=AllocateStatus)
      Allocate(Xrcp_rot(Number_Receptors),Stat=AllocateStatus)
      Allocate(Yrcp_rot(Number_Receptors),Stat=AllocateStatus)
      Open(Unit=11, File=ReceptorFileName, Status="Old", Action="Read", Iostat=ReadStatus)
      Read(11,*)
      Read(11,*)
      Read(11,*)

      index=1
      do while (index.LE.Number_Receptors)
        Read(11,'(A)')testread
        testread = adjustl(testread) 
        if(testread.NE.'')then
          if(testread(1:1).NE.'!')then
            read(testread,*,iostat=readstatus)Receptor(index)
            if(readstatus.ne.0)then
              print *,"Error reading receptor file near index ",index
              stop
            end if
            index=index+1
          end if
        end if
      end do

      Close(Unit=11)

      End Subroutine