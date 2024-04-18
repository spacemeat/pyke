import pyke as p

aaa = p.CompileAndLinkToSharedObjectPhase({'sources': ['aaa.c']})
aas = p.CompileAndLinkToSharedObjectPhase({'sources': ['aas.c']})
asa = p.CompileAndLinkToSharedObjectPhase({'sources': ['asa.c']})
ass = p.CompileAndLinkToSharedObjectPhase({'sources': ['ass.c']})
saa = p.CompileAndLinkToSharedObjectPhase({'sources': ['saa.c']})
sas = p.CompileAndLinkToSharedObjectPhase({'sources': ['sas.c']})
ssa = p.CompileAndLinkToSharedObjectPhase({'sources': ['ssa.c']})
sss = p.CompileAndLinkToSharedObjectPhase({'sources': ['sss.c']})

m = p.CompileAndLinkToExePhase({'sources': ['main.c']},
                     [aaa, aas, asa, ass, saa, sas, ssa, sss])

p.get_main_phase().depend_on(m)
