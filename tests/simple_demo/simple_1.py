'Bsic test'

import pyke as p

phases = []
c_to_o_phases = []

proto = p.CompilePhase({
    'include_dirs': ['include'],
    'obj_name': '{obj_basename}.o',
    'build_kind': 'debug'
})

for src in ('a.c', 'b.c', 'c.c', 'main.c'):
    c_to_o_phases.append(proto.clone({'name': f'compile_{src}', 'sources': [src]}))

proto = p.CompilePhase({
    'include_dirs': ['include'],
    'src_dir': 'exp',
    'obj_name': '{obj_basename}.o',
    'obj_dir': 'int/exp',
})

for src in ('a.c', 'b.c'):
    c_to_o_phases.append(proto.clone({'name': f'compile_{src}', 'sources': [src]}))

phases.extend(c_to_o_phases)

o_to_exe_phase = p.LinkPhase({
    'name': 'sample',
    'exe_basename': '{name}',
}, c_to_o_phases)

phases.append(o_to_exe_phase)

p.use_phases(phases)
