'Bsic test'

import pyke as p

phase = p.CompileAndLinkPhase({
    'name': 'simple',
    'sources': ['a.c', 'b.c', 'c.c', 'main.c'],
    'exe_basename': '{name}',
})

p.main_project().set_dependency(phase)
