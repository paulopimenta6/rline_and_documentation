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

      subroutine Read_Sources
! -----------------------------------------------------------------------------------
!     Written by AV, MGS and DKH
!     RLINE v1.2, November 2013
!
!     Reads inputs from source file
!
! -----------------------------------------------------------------------------------

      Use Data_Structures
      Use Line_Source_Data                ! Include library
      Implicit None

! Local variables:
      Integer             ::    index, Size        ! Index used to read met information
      Integer             ::    AllocateStatus     ! Integer that indicates read status
      Integer             ::    ReadStatus         ! Integer that indicates read status
      Integer             ::    s                  ! index for storing groups 
      Integer             ::    i,n                ! counting indices
      Character(len=200)  ::    testread           ! dummy variable for testing input lines for comments
      Character(len=40), Allocatable   :: Temp_Names(:)
! -----------------------------------------------------------------------------------

      call Compute_File_Size(Size, SourceFileName)
      Number_Sources=Size-3
      allocate(Source(Number_Sources),Stat=AllocateStatus)
      allocate(Xsb_rot(Number_Sources),Stat=AllocateStatus)
      allocate(Ysb_rot(Number_Sources),Stat=AllocateStatus)
      allocate(Xse_rot(Number_Sources),Stat=AllocateStatus)
      allocate(Yse_rot(Number_Sources),Stat=AllocateStatus)
      Open(Unit=11, File=SourceFileName, Status="Old", Action="Read", Iostat=ReadStatus)
      Read(11,*)
      Read(11,*)
      Read(11,*)
  
      index=1
      do while (index.LE.Number_Sources)
        Read(11,'(A)')testread
        testread = adjustl(testread) 
        if(testread.NE.'')then
          if(testread(1:1).NE.'!')then
            read(testread,*,iostat=readstatus)Source(index)
            if(readstatus.ne.0)then
              print *,"Error reading source file near index ",index
              stop
            end if
            index=index+1
          end if
        end if
      end do

      Close(Unit=11)

! ----Find the number of groups

      allocate(Temp_Names(Number_Sources),Stat=AllocateStatus) 
      
      Temp_Names(1) = Source(1)%group
      s = 1   ! # groups
    
      do index=2, Number_Sources
        n = 1
        i = 1   ! loop index
        do while ((n == 1) .and. (i .le. s)) ! loop over group names
          if (Source(index)%group == Temp_Names(i))then
            n = 0
          end if
          i = i+1
        end do
        if (n .ne. 0)then
          s = s+1
          Temp_Names(s) = Source(index)%group  
        end if
      end do

      Number_Groups = s

      allocate(Group_Names(Number_Groups),Stat=AllocateStatus)
      
      do i = 1,Number_Groups
        Group_Names(i) = Temp_Names(i)
      end do

      deallocate(Temp_Names)

! ----Create array of source indices for each group
      allocate(Group_Array(Number_Sources,Number_Groups),Stat=AllocateStatus)
      Group_Array = 0; ! elements are 0 if not assigned

      do i = 1,Number_Groups
        n = 1; ! counting # in each group
        do index=1, Number_Sources
          if(Source(index)%group == Group_Names(i)) then
            Group_Array(n,i) = index
            n = n+1;
          end if
        end do
      end do 

      end subroutine