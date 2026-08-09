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

      subroutine Analytical_Line_Source(Conc_AL)
! -----------------------------------------------------------------------------------
!     Written by AV, MGS and DKH
!     RLINE v1.2, November 2013
!
!     Computes concentrations using an analytical solution 
!     (instead of using Numerical_Line_Source)
!     Equation numbers correspond to those in Venkatram and Horst, AE, 40, 2401-2408
!-------------------------------------------------------------------------------------------------

      use Line_Source_Data
      implicit none

! External functions:
      real(kind=double)    :: sigmay, sigmaz, erf, sign

! Local variables:
      real(kind=double)    :: Conc_AL ! output
      real(kind=double)    :: xrL,yrL,xrU,yrU !  distances from source end points
      real(kind=double)    :: Xrpar,Yrpar,Xsbpar,Ysbpar,Xsepar,length 
      real(kind=double)    :: Xrtmp,Yrtmp,Xsbtmp,Ysbtmp,Xsetmp,Ysetmp 
      real(kind=double)    :: xr_prime,yr_prime
      real(kind=double)    :: erftU, erftL, cost,sint,syL,syU
      real(kind=double)    :: concp,Concp_par,fp 
      real(kind=double)    :: concr, sgn
      real(kind=double)    :: sz,sy,tL,tU, denom,wtth,szvert
      real(kind=double)    :: vert,corr 
      real(kind=double)    :: Xdif,Ydif, Zs, Xtemp,Ytemp, Ztemp , xp, xper, xwd, xwd_lim
      real(kind=double)    :: theta, thlim, rad90 , th_true ,theta_adj
      integer              :: it   
      real(kind=double)    :: Conc
      real(kind=double)    :: MthetaL, MthetaU, al, bl,thperp
      real(kind=double)    :: th, costh, dist, concr_gq

! Parameters
      real(kind=double)   :: a   = 1.0
      integer             :: NGQ = 5
      real(kind=double),dimension(5) :: wt = (/0.2369269,0.4786287,0.5688889,0.4786287,0.2369269/) 
      real(kind=double),dimension(5) :: x  = (/-0.9061798,-0.5384693,0.0, 0.5384693,0.9061798/)  

! -----------------------------------------------------------------------------------
! ---Set variables
     sigmaz0=Source(indq)%init_sigmaz 

! ---Initialize Concentrations
     Conc=0.0
     concp = 0.0
     Concp_par=0.0
     sz=0.0
     vert=0.0
     
! ---Get translated an rotated source information    
     Zs = (Zsbegin+Zsend)/2.0;
     length=sqrt((Xsend-Xsbegin)**2+(Ysend-Ysbegin)**2)
     
! ---orient the end points so the begining has a lower X value
     if (Xsend < Xsbegin) then
       Xtemp = Xsend
       Ytemp = Ysend
       Ztemp = Zsend
       Xsend = Xsbegin
       Ysend = Ysbegin
       Zsend = Zsbegin
       Xsbegin = Xtemp
       Ysbegin = Ytemp
       Zsbegin = Ztemp 
     end if
      
     Xdif      = Xsend-Xsbegin  
     Ydif      = Ysend-Ysbegin
     
     theta     = pi/2.0-(datan2(Ydif,Xdif)+sm_num)
     thlim     = 14.0*pi/180.0
     rad90     = 90.0*pi/180.0
     th_true   = theta

! ---if theta is close to 90 (parallel), adjust coords to an angle corresponding to 90+/-thlim
     if(abs(theta-rad90).LT.thlim)then
       theta     = rad90+thlim*sign(a,theta-rad90)
       theta_adj = theta-th_true
       cost      = cos(theta_adj)
       sint      = sin(theta_adj)
       Xrtmp     = Xr_rot *cost + Yr_rot *sint
       Yrtmp     =-Xr_rot *sint + Yr_rot *cost
       Xsbtmp    = Xsbegin*cost + Ysbegin*sint
       Ysbtmp    =-Xsbegin*sint + Ysbegin*cost
       Xsetmp    = Xsend  *cost + Ysend  *sint
       Ysetmp    =-Xsend  *sint + Ysend  *cost
     else
       Xrtmp     = xr_rot
       Yrtmp     = yr_rot
       Xsbtmp    = Xsbegin
       Ysbtmp    = Ysbegin
       Xsetmp    = Xsend
       Ysetmp    = Ysend
     end if

     Xdif        = Xsetmp-Xsbtmp  
     Ydif        = Ysetmp-Ysbtmp

! ---Set up limits of integration
     xrL         = Xrtmp-Xsbtmp
     yrL         = Yrtmp-Ysbtmp
     xrU         = Xrtmp-Xsetmp
     yrU         = Yrtmp-Ysetmp

! ---Find point on (extended) line directly upwind of receptor
     xp          = Xsbtmp +(yrL*Xdif/(Ydif+sm_num)) 
! ---Find x dist in wind direction between receptor and line    
     xwd         = Xrtmp-xp 
     xwd         = max(abs(xwd),1.0)*sign(a,xwd) 
! ---Shortest distance (perpendicular) between receptor and line
     xper        = abs((-Ydif*xrL+Xdif*yrL))/sqrt(Xdif**2+Ydif**2)

     Call Effective_Wind(xrL,Zs);
     syL         = sigmay(xrL);
     
     Call Effective_wind(xrU,Zs);
     syU         = sigmay(xrU);
     
     if(xrL.GT.0) then

       if(yrL.GT.yrU)then
         if((yrU.gt.0.0).AND.(yrU.lt.5.0*syU))then
           xwd_lim = xrU
         elseif((yrU.le.0.0).AND.(yrL.ge.0.0))then
           xwd_lim = xrL+yrL/(length*cos(theta))*(xrU-xrL)
         elseif((yrL.gt.-5.0*syL).AND.(yrL.lt.0.0))then
           xwd_lim = xrL
         else
          if(xrU>0)then
             xwd_lim = xrtmp-(Xsbtmp+0.75*(Xsetmp-Xsbtmp))
          else
            xwd_lim = 0.25*(Xsetmp-Xsbtmp)
          endif
        endif

      elseif(yrL.le.yrU)then
        if((yrU.gt.-5.0*syU).AND.(yrU.lt.0.0))then
          xwd_lim = xrU
        elseif((yrU.ge.0.0).AND.(yrL.le.0.0))then
          xwd_lim = xrL+yrL/(length*cos(theta))*(xrU-xrL)
        elseif((yrL.ge.0.0).AND.(yrL.lt.5.0*syL))then
          xwd_lim = xrL
        else
          if(xrU>0)then
            xwd_lim = xrtmp-(Xsbtmp+0.75*(Xsetmp-Xsbtmp))
          else
            xwd_lim = 0.25*(Xsetmp-Xsbtmp)
          endif
        end if

        end if

        elseif(xrL.LT.0)then
        xwd_lim = -1000.0
      end if
! -----------------------------------------------------------------------------------

! ----Compute the concentration as if the line is infinite ---------------------------
      call Effective_Wind(xwd_lim,Zs)
      szvert = sigmaz(xwd_lim)

      call Effective_Wind(xwd,Zs)
      sz = sigmaz(xwd)

      vert = (exp(-0.5*((Zrecep-Zs)/szvert)**2)+exp(-0.5*((Zrecep+Zs)/szvert)**2))/2.0;

      denom = sz*ueff*abs(cos(theta))  ! +sm_num
      concp = sqrt(2.0/pi)*vert/denom  ! Equation (7) of AE paper

! ----End infinite--------------------------------------------------------------------

! ----Apply the finite line correction  ----------------------------------------------
! ----Based on Equation (11); sign=+-1 depending on sign of -Xr/sf.

      sgn = sign(a,-xwd/cos(theta))
      if (xrL>0.0) then
        call Effective_Wind(xrL,Zs)
        sy    = sigmay(xrL)
        tL    = yrL/(sqrt(2.0)*sy)  ! Equation  (9)
        erftL = erf(tL)
      else
        erftL = sgn
      endif
     
      if (xrU>0.0) then
        call Effective_wind(xrU,Zs)
        sy    = sigmay(xrU)
        tU    = yrU/(sqrt(2.0)*sy)  ! Equation  (9)
        erftU = erf(tU)
      else
        erftU = sgn
      endif

      corr=abs((erftL-erftU)/2.0)  ! Equation (10)

      concp=concp*corr  ! plume concentration for a finite line source


! ----When abs(theta-90)<thlim, find soln for parallel and interpolate between that and soln at 90+/-thlim
      if(abs(th_true-rad90).LT.thlim)then 

        theta_adj =  rad90-th_true
        cost      =  cos(theta_adj)
        sint      =  sin(theta_adj)
        Xrpar     =  Xr_rot *cost +Yr_rot *sint
        Yrpar     = -Xr_rot *sint +Yr_rot *cost
        Xsbpar    =  Xsbegin*cost +Ysbegin*sint
        Ysbpar    = -Xsbegin*sint +Ysbegin*cost
        Xsepar    =  Xsend  *cost +Ysend  *sint
        call Analytical_Line_Parallel(Xrpar-Xsbpar,Yrpar-Ysbpar,Xrpar-Xsepar,Zs,Concp_par)
        wtth      =  1.0-abs(th_true-rad90)/thlim
        concp     =  concp*(1.0-wtth)+Concp_par*wtth
        theta     =  th_true ! restore theta to the true value
      end if
! ----End finite correction----------------------------------------------------------

! ----find meander concentration using 5-pt Gaussian quadrature
      fp    = 0.0
      concr = 0.0
      corr  = 0.0
      sz    = 0.0
      sy    = 0.0
      Xdif  = Xsend-Xsbegin  
      Ydif  = Ysend-Ysbegin

! ----Set up limits of integration
      xrL   = Xr_rot-Xsbegin
      yrL   = Yr_rot-Ysbegin
      xrU   = Xr_rot-Xsend
      yrU   = Yr_rot-Ysend

! ----Find point on (extended) line directly upwind of receptor
      xp    = Xsbegin +(yrL*Xdif/(Ydif+sm_num)) 
! ----Find x dist in wind direction between receptor and line    
      xwd   = Xr_rot-xp 

! ---Shortest distance (perpendicular) between receptor and line
      xper  = abs((-Ydif*xrL+Xdif*yrL))/sqrt(Xdif**2+Ydif**2)

! ----If the receptor is in line with or on the line source, shift it 1 m.
      if(abs(xper).LT.1.0E-6) then
        xr_prime = xr_rot+1.0*cos(theta)
        yr_prime = yr_rot-1.0*sin(theta)
        if(abs(theta-pi/2.0).LT. 0.001)then
          xr_prime = xr_rot
          yr_prime = yr_rot-1.0
        end if
        xrL  = xr_prime-Xsbegin
        yrL  = yr_prime-Ysbegin
        xrU  = xr_prime-Xsend
        yrU  = yr_prime-Ysend
        xp   = Xsbegin +(yrL*Xdif/(Ydif+sm_num)) 
        xwd  = xr_prime-xp
        xper = abs((-Ydif*xrL+Xdif*yrL))/sqrt(Xdif**2+Ydif**2)
      end if
     
! ----Find angles (th) to be used to locate integration points
      if(xwd .GT. 0.0) then
        thperp  = acos(xper/abs(xwd))*sign(a,Ysbegin-Ysend)
        MthetaL = atan2(-YrL,(XrL))
        MthetaU = atan2(-YrU,(XrU))
        al      = (MthetaL+MthetaU)/2.0+thperp
        bl      = (MthetaL-MthetaU)/2.0
      else
        thperp  = acos(xper/abs(xwd))*sign(a,Ysbegin-Ysend)
        MthetaL = atan2(-YrL,-XrL)
        MthetaU = atan2(-YrU,-XrU)
        al      = (MthetaL+MthetaU)/2.0-thperp
        bl      = (MthetaL-MthetaU)/2.0
      end if

      concr_gq = 0.0

      do it = 1, NGQ
        th       = al+bl*x(it)
        costh    = cos(th)
        dist     = abs(xper/costh) 
        call Effective_Wind(dist,Zs) 
        sz       = sigmaz(dist)
        vert     = (exp(-0.5*((Zrecep-Zs)/sz)**2)+exp(-0.5*((Zrecep+Zs)/sz)**2))/2
        concr_gq = concr_gq+ wt(it)*vert*sqrt(2/pi)/(sz*ueff)/(2*pi*dist)/(costh*costh)
      end do
      Concr = abs(concr_gq*bl*xper)

      call Effective_Wind(xper,Zs)

      fp = 2.0*(sigmav/ueff)**2

! ----Combine meander and plume concentrations
      if(op_C.EQ.'P')then
        Conc = concp*(1-fp)
      elseif(op_C.EQ.'M')then
        Conc = concr*fp
      else
        Conc = fp*concr + (1-fp)*concp
      endif

! ----Set output for Analytical Line source
      Conc_AL = Conc
      end