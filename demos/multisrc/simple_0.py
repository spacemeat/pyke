'Bsic test'

import pyke as p

phases = []
c_to_o_phases = []

c_to_o_phases.append(p.CompilePhase(
    'compile_src', {
    'include_dirs': ['include'],
    'obj_basename': 'sample',
    'sources': ['a.c', 'b.c', 'c.c', 'main.c']
}))

c_to_o_phases.append(p.CompilePhase(
    'compile_exp', {
    'include_dirs': ['include'],
    'src_dir': 'exp',
    'obj_basename': 'sample_exp',
    'obj_dir': 'int/exp',
    'sources': ['a.c', 'b.c']
}))

phases.extend(c_to_o_phases)

o_to_exe_phase = p.LinkPhase(
    'link', {
    'exe_basename': 'simple_0',
}, c_to_o_phases)

phases.append(o_to_exe_phase)

p.main_project().set_dependency(o_to_exe_phase)
