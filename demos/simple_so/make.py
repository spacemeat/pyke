'Bsic test for lib archive'

import pyke as p

obj_phase = p.CompilePhase({
    'name': 'simple_objs',
    'sources': ['a.c', 'b.c', 'c.c'],
})

so_phase = p.LinkToSharedObjectPhase({
    'name': 'simple_so',
}, obj_phase)

exe_phase = p.CompileAndLinkPhase({
    'name': 'simple_exe',
    'sources': ['main.c'],
}, so_phase)

p.main_project().set_dependency(exe_phase)
