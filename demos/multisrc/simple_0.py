'Bsic test'

import pyke as p

phases = []
c_to_o_phases = []

c_to_o_phases.append(p.CompilePhase({
    'name': 'compile_src',
    'include_dirs': ['include'],
    'obj_basename': 'sample',
    'sources': ['a.c', 'b.c', 'c.c', 'main.c']
}))

c_to_o_phases.append(p.CompilePhase({
    'name': 'compile_exp',
    'include_dirs': ['include'],
    'src_dir': 'exp',
    'obj_basename': 'sample_exp',
    'obj_dir': 'int/exp',
    'sources': ['a.c', 'b.c']
}))

phases.extend(c_to_o_phases)

o_to_exe_phase = p.LinkToExePhase({
    'name': 'link',
    'exe_basename': 'simple_0',
}, c_to_o_phases)

phases.append(o_to_exe_phase)

p.get_main_phase().depend_on(o_to_exe_phase)
