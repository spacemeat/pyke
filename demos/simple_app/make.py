'Bsic test'

import pyke as p

phase = p.CompileAndLinkToExePhase({
    'name': 'simple',
    'sources': ['a.c', 'b.c', 'c.c', 'main.c'],
})

p.main_project().set_dependency(phase)
