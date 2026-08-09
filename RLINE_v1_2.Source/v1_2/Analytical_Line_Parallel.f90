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

      subroutine Analytical_Line_Parallel(xL,yrLU,xU,Zs,Conc)
! -----------------------------------------------------------------------------------
!     Written by DKH and MGS
!     RLINE v1.2, November 2013
!
!     This analytical solution to dispersion from a finite line
!     source with wind parallel to the line was derived by Prof. 
!     Akula Venkatram.
!
! -----------------------------------------------------------------------------------

      use Line_Source_Data
      implicit none

! External functions:
      Real(kind=double)  :: sign, erf, sigmay, sigmaz

! Local variables:
      Real(kind=double)  :: xL, xU, xrL, yrec, xrU, Zs, xrtemp, yrLU
      Real(kind=double)  :: pL, pU, AL, AU, BL, dsydxL
      Real(kind=double)  :: pL_refl, pU_refl, AL_refl, AU_refl, BL_refl
      Real(kind=double)  :: sy_xrL, sz_xrL, sy_xrU, sz_xrU 
      Real(kind=double)  :: ueff_xrL, ueff_xrU, ueffave, Rsysz
      Real(kind=double)  :: erfpL, erfpU, Conc
      Real(kind=double)  :: erfpL_refl, erfpU_refl, Conc_refl, Conc1

! Parameters
      Real(kind=double)  :: a=1.0
! -----------------------------------------------------------------------------------
      xrL      = xL
      xrU      = xU
      yrec     = yrLU
      sy_xrL   = 0.0
      sz_xrL   = 0.0
      sy_xrU   = 0.0
      sz_xrU   = 0.0
      Rsysz    = 0.0
      ueff_xrL = 0.0
      ueff_xrU = 0.0
      ueffave  = 0.0
      Conc      =0.0; Conc1     =0.0; Conc_refl=0.0;
      AL        =0.0; AU        =0.0; 
      BL        =0.0
      pL        =0.0; pU        =0.0;
      erfpL     =0.0; erfpU     =0.0;
      AL_refl   =0.0; AU_refl   =0.0; 
      BL_refl   =0.0
      pL_refl   =0.0; pU_refl   =0.0; 
      erfpL_refl=0.0; erfpU_refl=0.0;
      dsydxL=0.0
      
! ----Flip the line around if necessary to make xrU<xrL
      if(xrL<xrU) then
        xrtemp     = xrL
        xrL        = xrU
        xrU        = xrtemp
      end if
! ----If the receptor is on the line, move it to 1m from line  
      if (yrec.EQ.0.0)then
        yrec       = sign(a,yrec)
      end if
      
      if(xrL<=0)then
        Conc       = 0.0
      else
        Call Effective_Wind(xrL,Zs)
        ueff_xrL   = ueff
        sy_xrL     = sigmay(xrL)
        sz_xrL     = sigmaz(xrL)
        Rsysz      = sy_xrL/sz_xrL
! ------Evaluate A at xrL when computing pL
        AL         = sqrt(1.0 + (Zs-Zrecep)**2*(Rsysz/yrec)**2)
        AL_refl    = sqrt(1.0 + (Zs+Zrecep)**2*(Rsysz/yrec)**2)
        pL         = yrec*AL/(sqrt(2.0)*sy_xrL)
        pL_refl    = yrec*AL_refl/(sqrt(2.0)*sy_xrL)
        erfpL      = erf(pL)
        erfpL_refl = erf(pL_refl)

! ------If receptor is upwind of xU (ie xrU<0), cut source 0.5m upwind of receptor
! ------Use 0.5m as cutoff distance
        if(xrU<=0) then
          xrU=0.5
        end if
        call Effective_Wind(xrU,Zs);
        ueff_xrU   = ueff
        sy_xrU     = sigmay(xrU) 
        sz_xrU     = sigmaz(xrU)
        Rsysz      = sy_xrU/sz_xrU
! ------Evaluate A at xrU when computing pU
        AU         = sqrt(1.0 + (Zs-Zrecep)**2*(Rsysz/yrec)**2)
        AU_refl    = sqrt(1.0 + (Zs+Zrecep)**2*(Rsysz/yrec)**2)
        pU         = yrec*AU/(sqrt(2.0)*sy_xrU)
        pU_refl    = yrec*AU_refl/(sqrt(2.0)*sy_xrU)
        erfpU      = erf(pU);
        erfpU_refl = erf(pU_refl);
        
! ------Evaluate B at xrL
        call Effective_Wind(xrL,Zs)
        dsydxL = (sigmay(xrL+1.0)-sigmay(xrL))/1.0
        BL      = sy_xrL/sz_xrL*(1.0/dsydxL)*1.0/AL
        BL_refl = sy_xrL/sz_xrL*(1.0/dsydxL)*1.0/AL_refl

! ------Evaluate ueff at xrL and xrU and average them together
        ueffave   = 0.5*(ueff_xrL+ueff_xrU)        
         
        Conc1     = BL     /(sqrt(2.0*pi)*yrec*ueffave)*(erfpU     -erfpL)
        Conc_refl = BL_refl/(sqrt(2.0*pi)*yrec*ueffave)*(erfpU_refl-erfpL_refl)
        Conc      = (Conc1+Conc_refl)/2.0
      end if
 
      end
