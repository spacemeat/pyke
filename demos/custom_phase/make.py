'Bsic test with custom phase'

# pylint: disable=wrong-import-position

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))

from custom import ContrivedCodeGenPhase
import pyke as p

gen_src = {
'd.c': r'''
#include "abc.h"

int d()
{
    return 1000;
}''',

'e.c': r'''
#include "abc.h"

int e()
{
	return 10000; 
}'''
}

gen_phase = ContrivedCodeGenPhase({
    'gen_src_origin': __file__,
    'gen_sources': gen_src,
})

build_phase = p.CompileAndLinkPhase({
    'name': 'simple',
    'sources': ['a.c', 'b.c', 'c.c', 'main.c'],
}, gen_phase)

p.main_project().set_dependency(build_phase)
