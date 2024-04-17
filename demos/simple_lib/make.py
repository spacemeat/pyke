'Bsic test for lib archive'

import pyke as p

ar_phase = p.CompileAndArchivePhase({
    'name': 'simple_archive',
    'sources': ['a.c', 'b.c', 'c.c'],
})

exe_phase = p.CompileAndLinkToExePhase({
    'name': 'simple_exe',
    'sources': ['main.c'],
}, ar_phase)

p.get_main_phase().depend_on(exe_phase)
