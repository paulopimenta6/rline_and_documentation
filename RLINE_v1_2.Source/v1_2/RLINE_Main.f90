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

      program RLINE_Main
! -----------------------------------------------------------------------------------
!     Written by Akula Venkatram (AV), Michelle G. Snyder (MGS) and David K. Heist (DKH)
!     RLINE v1.2, November 2013
!
!     This program computes the concentration in microgm/m^3 associated with a 
!     an arbitrary number of line sources. Each line source is specified with an 
!     emission rate per unit length of Qemis gm/s/m,(x,y,z) and co-ordinates of the 
!     end points. Each line sources has a different sigmaz0. The line sources are 
!     listed in a text file specified in text file called Line_Source_Inputs.txt

!     The number of receptors is arbitrary. They are specified using coordinates 
!     are Xrecep, Yrecep, Zrecep. The receptors are listed in a text file specified 
!     in a text file called Line_Source_Inputs.txt

!     The meteorology is specified an .sfc file geneerated by AERMET, the met-preprocessor 
!     for AERMOD.  Its name is specified in a text file called Line_Source_Inputs.txt
!
! -----------------------------------------------------------------------------------

      Use Line_Source_Data
      Implicit None

! Local variables:
      Real(kind=double)  :: Error    !  Error in the numerical integration
      Real(kind=double)  :: Concd    !  Dummy concentration at receptor
      Real(kind=double)  :: Zb       !  Release height for barriers
      Integer            :: index, isource, AllocateStatus,imet, igroup
      Integer            :: SizeSurf
      Real(kind=double)  :: start, finish 
! -----------------------------------------------------------------------------------
     
      Call cpu_time(start)
 
      Call Create_Exp_Table

      write(*,*) "Reading Inputs..."
      Call Read_Line_Source_Inputs

      write(*,*) "Reading Receptors..."
      Call Read_Receptors

      write(*,*) "Reading Sources..."
      Call Read_Sources

      write(*,*) "Reading SFC-file..."
      Call Read_Met_Inputs(SizeSurf)

      Allocate(Concentration(Number_Receptors,SizeSurf,Number_Groups),Stat=AllocateStatus)

      Concd=0.0         ! Initialize Concentrations
      Concentration=0.0

      Do imet=1, SizeSurf
        if (op_Analytical =='Y' .AND. imet == 1)then
          write(*,*) "WARNING: The ANALYTICAL solution will be used." 
          write(*,*) "This is less accuarte at small source-recptor distances"
          write(*,*) "and wind angles near parallel to the line source."
        else if (imet == 1)then
          write(*,*) "WARNING: The NUMERICAL solution will be used." 
          write(*,*) "This solution is very accurate, but may take a long"
          write(*,*) "time to compute."
        end if

        write(*,*) "Working on line ", imet, "of", SizeSurf, "in SFC-file..."
        if ((SurfaceMet(imet)%ustar.LE.0.0).OR.(SurfaceMet(imet)%Hs.EQ.-999.0)) then
          Concentration(1:Number_Receptors,imet,:)=-99.0        
        else
          Call Fill_Met(imet)      ! Assign met variables
          Call Compute_Met         ! Compute sigmav and Ueff and thetaw 
          write(*,*) "Rotating to wind-direction coordinates..."
          Call Translate_Rotate    !  Translate and rotate line source to align with wind direction 
          write(*,*) "Computing concentrations..."
          do index=1,Number_Receptors
            Xr_rot=Xrcp_rot(index)
            Yr_rot=Yrcp_rot(index)
            Zrecep=Receptor(index)%Zr
            do igroup=1,Number_Groups
              do isource = 1, Number_Sources
                indq = Group_Array(isource,igroup) ! set global variable for line index

                if(indq .gt. 0)then
! --------------Get translated an rotated source information

                  sigmaz0=Source(indq)%init_sigmaz     
                  Xsbegin=Xsb_rot(indq);
                  Xsend = Xse_rot(indq);
                  Ysbegin=Ysb_rot(indq);
                  Ysend = Yse_rot(indq);
                  if((op_SC.EQ.'Y') .AND. (Source(indq)%hwall .GT. 0.0))then
                    Call Barrier_Displacement(Zb)
                    Zsbegin = Zb
                    Zsend   = Zb
                  else
                    Zsbegin=Source(indq)%Zsb
                    Zsend  =Source(indq)%Zse
                  end if
! ----------------Set roadwidth (initial sigmay)
                  sigmay0 = 0.0 ! initialize intital sigmay
                  if (op_width =='Y')then
                    sigmay0 = abs(0.5*(width*Source(indq)%Nlanes)*sin(thetaw+sm_num));
                  end if
                  if (op_Analytical =='Y')then
                    Call Analytical_Line_Source(Concd)
                    Error = 0.0
                  else
                    Call Numerical_Line_Source(imet,index,Concd,Error)
                  end if
                  Concentration(index,imet,igroup)=Concentration(index,imet,igroup)+Concd*1.0e06*Source(indq)%Qemis
                end if ! group_array loop
              end do ! source loop
            end do ! group loop
          end do ! receptor loop
        end if
      end do ! met loop


      if (op_monthly =='M')then
        write(*,*) "DONE computing"
        write(*,*) "Now writing hourly output file by MONTH... "
        Call Write_Hourly_by_Month(SizeSurf)
      else if (op_monthly =='A')then
        write(*,*) "DONE computing"
        write(*,*) "Now writing hourly output file... "
        Call Write_Hourly_All(SizeSurf)
      else
        write(*,*) "DONE computing... NOT writing hourly output file! "
      end if
 
      if (op_ave =='Y')then
        write(*,*) "Now writing 24-hour average output file... "
        Call Write_Daily_Ave(SizeSurf)
      else 
        write(*,*) "DONE ... NOT writing daily average output file! "
      end if

      Call cpu_time(finish)

      print '("runtime = ", f10.3," seconds.")', finish-start  
      call Deallocate_arrays
      End 