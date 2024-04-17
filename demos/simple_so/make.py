'Bsic test for shared object'

import pyke as p

obj_phase = p.CompilePhase({
    'name': 'simple_objs',
    'sources': ['a.c', 'b.c', 'c.c'],
})

so_phase = p.LinkToSharedObjectPhase({
    'name': 'simple_so',
}, obj_phase)

exe_phase = p.CompileAndLinkToExePhase({
    'name': 'simple_exe',
    'sources': ['main.c'],
}, so_phase)

p.get_main_phase().depend_on(exe_phase)
