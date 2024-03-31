'Bsic test with custom phase'

from custom import ContrivedCodeGenPhase
import pyke as p

gen_src = {
        'd.c': r'''
#include \"abc.h\"

int d()
{
	return 1000;
}''',
        'e.c': r'''
#include \"abc.h\"

int e()
{
	return 10000;
}'''
}

gen_phase = ContrivedCodeGenPhase({
    'gen_src_origin': '',
    'gen_sources': gen_src,
})

build_phase = p.CompileAndLinkPhase({
    'sources': ['a.c', 'b.c', 'c.c', 'main.c'],
}, gen_phase)

p.main_project().set_dependency(build_phase)
