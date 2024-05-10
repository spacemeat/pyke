import pyke as p

pa = p.run_makefile('a-star')
ps = p.run_makefile('s-star')

aaa = pa.find_dep('aaa')
aas = pa.find_dep('aas')
asa = pa.find_dep('asa')
ass = pa.find_dep('ass')

saa = ps.find_dep('saa')
sas = ps.find_dep('sas')
ssa = ps.find_dep('ssa')
sss = ps.find_dep('sss')

m = p.CompileAndLinkToExePhase({'sources': ['main.c']},
                     [aaa, aas, asa, ass, saa, sas, ssa, sss])

p.get_main_phase().depend_on(m)
