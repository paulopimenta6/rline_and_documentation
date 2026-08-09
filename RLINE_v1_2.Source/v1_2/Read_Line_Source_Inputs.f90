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

      subroutine Read_Line_Source_Inputs
! ------------------------------------------------------------------------------
!     Written by AV and MGS
!     RLINE v1.2, November 2013
!
!     Reads inputs from Line_Source_Inputs.txt
!
! ------------------------------------------------------------------------------

      Use Line_Source_Data          
      Implicit None

! Local variables:
      Integer             ::    ReadStatus      ! Integer that indicates read status
! ------------------------------------------------------------------------------
    
      Open(Unit=10, File="Line_Source_Inputs.txt", Status="Old", Action="Read", Iostat=ReadStatus)

! ---- Input files
      Read(10,*)
      Read(10,*)
      Read(10,*)SourceFileName
      Read(10,*)

      Read(10,*)
      Read(10,*)
      Read(10,*)ReceptorFileName

      Read(10,*)
      Read(10,*)
      Read(10,*)InputSurfaceFile
  
      Read(10,*)
      Read(10,*)
      Read(10,*)OutputReceptorFile

! ---- User specified run options
      Read(10,*)
      Read(10,*)
      Read(10,*)Error_Limit
  
      Read(10,*)
      Read(10,*)
      Read(10,*)fac_dispht ! Multiplies roughness length to estimate displacment heights
    
! ---- Output options
      Read(10,*)
      Read(10,*)
      Read(10,*)
      Read(10,*)
      Read(10,*)op_C ! Output Concentration ['P']lume, ['M']eander, ['T']otal
  
      Read(10,*)
      Read(10,*)
      Read(10,*)op_ave ! Output 24 hour average

      Read(10,*)
      Read(10,*)
      Read(10,*)op_monthly ! Monthly Output files
  
      Read(10,*)
      Read(10,*)
      Read(10,*)op_warn ! suppress numerical convergence warnings

! ---- BETA OPTIONS
      Read(10,*)
      Read(10,*)
      Read(10,*)
      Read(10,*)
      Read(10,*)op_Analytical ! Use Analytical solution ALWAYS
  
      Read(10,*)
      Read(10,*)
      Read(10,*)op_SC ! Use source configuration algorithms
  
      Read(10,*)
      Read(10,*)
      Read(10,*)op_width, width! Use roadwidth
  
      Close(Unit=10)
      
      width = abs(width); ! take absolute value of lane width

! --- warn user if NO outputs are selected
      if (op_monthly =='M')then
      else if (op_monthly =='A')then
      else
        write(*,*) "WARNING: User has selected NO hourly output files! "
      end if
 
      if (op_ave =='Y')then
      else 
        write(*,*) "WARNING: User has selected NO daily average output file! "
      end if

      End Subroutine