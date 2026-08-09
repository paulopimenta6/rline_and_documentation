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

      subroutine Read_Met_Inputs(SizeSurf)
!-----------------------------------------------------------------------------------------------
!     Written by AV
!     RLINE v1.2, November 2013
!
!     Reads inputs from surface meteorological file
!----------------------------------------------------------------------------

      Use Data_Structures
      Use Line_Source_Data
      Implicit None

      Integer    :: SizeSurf   ! Size of surface file
      Integer    :: AllocateStatus, ReadStatus, Index

! -------------------------------------------------------------------------------------  

! ----Calculate size of surface file
      Call Compute_File_Size(SizeSurf,InputSurfaceFile)

! ----Read surface files
      SizeSurf=SizeSurf-1
      Allocate(SurfaceMet(SizeSurf),Stat=AllocateStatus)
      Open(Unit=10, File=InputSurfaceFile, Status="Old", Action="Read", Iostat=ReadStatus)
      Read(10,*)
      Do Index = 1,SizeSurf   
        Read(10,*)SurfaceMet(Index)
      End Do
      Close(Unit=10)

      End Subroutine