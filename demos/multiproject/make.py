''' Demo pyke makefile with multiple project phases.'''

import pyke as p


proto = p.CompilePhase()
d = proto.clone({'name': 'd', 'sources': ['d.c']})
e = proto.clone({'name': 'e', 'sources': ['e.c']})

d_e_lib_project = p.CompileAndArchivePhase({
    'name': 'de_lib',
}, [d, e])

abc_nolib_exe = p.CompileAndLinkPhase({
    'name': 'abc_nolib',
    'sources': ['a.c', 'b.c', 'c.c', 'main.c'],
}, [d, e])

abc_withlib_exe = p.CompileAndLinkPhase({
    'name': 'abc_withlib',
    'sources': ['a.c', 'b.c', 'c.c', 'main.c'],
}, d_e_lib_project)

abc_d_e_project = p.ProjectPhase({'name': 'abc_nolib_proj'}, abc_nolib_exe)
abc_de_project = p.ProjectPhase({'name': 'abc_withlib_proj'}, abc_withlib_exe)

main_project = p.main_project().set_dependency([
    abc_d_e_project,
    abc_de_project
])
