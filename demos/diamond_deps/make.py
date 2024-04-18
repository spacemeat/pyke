''' Demo pyke makefile with multiple project phases.'''

import pyke as p


proto = p.CompilePhase({'obj_dir': '{group}'})
d = proto.clone({'name': 'd', 'sources': ['d.c']})
e = proto.clone({'name': 'e', 'sources': ['e.c']})

d_e_lib_project = p.CompileAndArchivePhase({
    'name': 'de_lib',
}, [d, e])

abc_nolib_exe = p.CompileAndLinkToExePhase({
    'name': 'abc_nolib',
    'sources': ['a.c', 'b.c', 'c.c', 'main.c'],
}, [d, e])

abc_withlib_exe = p.CompileAndLinkToExePhase({
    'name': 'abc_withlib',
    'sources': ['a.c', 'b.c', 'c.c', 'main.c'],
}, d_e_lib_project)

abc_d_e_project = p.ProjectPhase({'name': 'abc_nolib_proj'}, abc_nolib_exe)
abc_de_project = p.ProjectPhase({'name': 'abc_withlib_proj'}, abc_withlib_exe)

p.get_main_phase().depend_on([
    abc_d_e_project,
    abc_de_project
])
