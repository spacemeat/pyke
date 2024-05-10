import pyke as p

b = p.CompileAndLinkToSharedObjectPhase({'inc_dir': '..'})
saa = b.clone({'name': 'saa', 'sources': ['saa.c']})
sas = b.clone({'name': 'sas', 'sources': ['sas.c']})
ssa = b.clone({'name': 'ssa', 'sources': ['ssa.c']})
sss = b.clone({'name': 'sss', 'sources': ['sss.c']})

p.get_main_phase().depend_on([saa, sas, ssa, sss])
