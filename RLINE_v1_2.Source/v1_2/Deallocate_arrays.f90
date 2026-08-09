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

      subroutine Deallocate_arrays            
! -----------------------------------------------------------------------------------
!     Written by DKH
!     RLINE v1.2, November 2013
!
!     This subroutine deallocates dynamic arrays
! -----------------------------------------------------------------------------------

      Use Line_Source_Data
      Implicit None

! Local variables:
      integer               ::  AllocError

!------------------------------------------------------------------------------------

      if(allocated(SurfaceMet)) then
        deallocate(SurfaceMet,Stat=AllocError)
        if(AllocError .NE. 0) print *,"SurfaceMet deallocation error"
      end if
      
      if(allocated(Profile)) then
        deallocate(Profile,Stat=AllocError)
        if(AllocError .NE. 0) print *,"Profile deallocation error"
      end if
      
      if(allocated(Source)) then
        deallocate(Source,Stat=AllocError)
        if(AllocError .NE. 0) print *,"Source deallocation error"
      end if
      
      if(allocated(Group_Names)) then
        deallocate(Group_Names,Stat=AllocError)
        if(AllocError .NE. 0) print *,"Group_Names deallocation error"
      end if
      
      if(allocated(Group_Array)) then
        deallocate(Group_Array,Stat=AllocError)
        if(AllocError .NE. 0) print *,"Group_Array deallocation error"
      end if
      
      if(allocated(Xrcp_rot)) then
        deallocate(Xrcp_rot,Stat=AllocError)
        if(AllocError .NE. 0) print *,"Xrcp_rot deallocation error"
      end if
      
      if(allocated(Yrcp_rot)) then
        deallocate(Yrcp_rot,Stat=AllocError)
        if(AllocError .NE. 0) print *,"Yrcp_rot deallocation error"
      end if
      
      if(allocated(Xsb_rot)) then
        deallocate(Xsb_rot,Stat=AllocError)
        if(AllocError .NE. 0) print *,"Xsb_rot deallocation error"
      end if
      
      if(allocated(Ysb_rot)) then
        deallocate(Ysb_rot,Stat=AllocError)
        if(AllocError .NE. 0) print *,"Ysb_rot deallocation error"
      end if
      
      if(allocated(Xse_rot)) then
        deallocate(Xse_rot,Stat=AllocError)
        if(AllocError .NE. 0) print *,"Xse_rot deallocation error"
      end if
      
      if(allocated(Yse_rot)) then
        deallocate(Yse_rot,Stat=AllocError)
        if(AllocError .NE. 0) print *,"Yse_rot deallocation error"
      end if

      if(allocated(Receptor)) then
        deallocate(Receptor,Stat=AllocError)
        if(AllocError .NE. 0) print *,"Receptor deallocation error"
      end if
      
      if(allocated(Concentration)) then
        deallocate(Concentration,Stat=AllocError)
        if(AllocError .NE. 0) print *,"Concentration deallocation error"
      end if

      end subroutine
! -----------------------------------------------------------------------------------

