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

      subroutine Compute_File_Size(Size, FileName)
! -----------------------------------------------------------------------------------
!     Written by AV and DKH
!     RLINE v1.2, November 2013
!
!     Determines the number of entries in an input file
! -----------------------------------------------------------------------------------

! Arguments:
      Character(len=40), Intent(IN) :: FileName  ! Name of file whose size is required
      Integer(4), Intent(OUT)       :: Size      ! Number of records in file

! Local variables:
      Integer                       :: ReadStatus  ! Integer that indicates read status
      Character(40)                 :: Linetext
! -----------------------------------------------------------------------------------

      Open(Unit=12, File=FileName, Status="Old", Action="Read")

! ----Read input file

      Size=0
      do ! until ReadStatus < 0
        Read(12,*, Iostat=ReadStatus)Linetext
! ----  Check for end of data
        if (ReadStatus<0) then
          Close (Unit=12)
          exit
        end if
        if(index(linetext,'!').EQ.0) then
          Size=Size+1
        end if
      end do

      end subroutine 