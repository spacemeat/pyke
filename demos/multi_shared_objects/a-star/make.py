import pyke as p

b = p.CompileAndArchivePhase({'inc_dir': '..'})
aaa = b.clone({'name': 'aaa', 'sources': ['aaa.c']})
aas = b.clone({'name': 'aas', 'sources': ['aas.c']})
asa = b.clone({'name': 'asa', 'sources': ['asa.c']})
ass = b.clone({'name': 'ass', 'sources': ['ass.c']})

p.get_main_phase().depend_on([aaa, aas, asa, ass])
