'Bsic test'

import pyke as p

phase = p.CompileAndLinkToExePhase({
    'name': 'simple',
    'sources': ['a.c', 'b.c', 'c.c', 'main.c'],
})

p.get_main_phase().depend_on(phase)
