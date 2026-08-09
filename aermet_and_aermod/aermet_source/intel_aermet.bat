ifx mod_file_units.f90              /compile_only /traceback /warn:all /check:all  /free 
ifx mod_main1.f90   /compile_only /traceback /warn:all /check:all  /free 
ifx mod_upperair.f90 /compile_only /traceback /warn:all /check:all  /free 
ifx mod_surface.f90 /compile_only /traceback /warn:all /check:all  /free 
ifx mod_onsite.f90 /compile_only /traceback /warn:all /check:all  /free 
ifx mod_pbl.f90 /compile_only /traceback /warn:all /check:all  /free
ifx mod_read_input.f90             /compile_only /traceback /warn:all /check:all  /free 
ifx mod_reports.f90 /compile_only /traceback /warn:all /check:all  /free 
ifx mod_misc.f90 /compile_only /traceback /warn:all /check:all  /free 
ifx aermet.f90             /compile_only /traceback /warn:all /check:all  /free 

ifx /exe:aermet.exe  aermet.obj mod_main1.obj mod_file_units.obj mod_upperair.obj mod_surface.obj mod_onsite.obj ^
 mod_pbl.obj mod_read_input.obj mod_reports.obj mod_misc.obj
 del *.obj *.mod