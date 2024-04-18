'multiphase cloned test'

import pyke as p

c_to_o_phases = []

proto = p.CompilePhase()

for src in ('a.c', 'b.c', 'c.c', 'main.c'):
    c_to_o_phases.append(proto.clone({'name': f'compile_{src}', 'sources': [src]}))

proto = p.CompilePhase({
    'src_dir': 'exp',
    'obj_dir': 'int/exp',
})

for src in ('a.c', 'b.c'):
    c_to_o_phases.append(proto.clone({'name': f'compile_exp_{src}', 'sources': [src]}))

o_to_exe_phase = p.LinkToExePhase({
    'name': 'link',
    'exe_basename': 'simple_1',
}, c_to_o_phases)

p.get_main_phase().depend_on(o_to_exe_phase)
