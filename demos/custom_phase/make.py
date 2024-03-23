'Bsic test with custom phase'

from custom import ContrivedCodeGenPhase
import pyke as p

gen_phase = ContrivedCodeGenPhase('generator')

build_phase = p.CompileAndLinkPhase(
    'simple', {
    'sources': ['a.c', 'b.c', 'c.c', 'gen/d.c', 'gen/e.c', 'main.c'],
}, gen_phase)

p.main_project().set_dependency(build_phase)
