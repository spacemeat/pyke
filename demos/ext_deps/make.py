''' external package test '''

import pyke as p

humon_phase_0_1_0 = p.ExternalPackagePhase({
    'project_name': 'humon',
    'repo_project_name': 'spacemeat/humon',
    'package_version': 'v0.1.0',
})

humon_phase_0_2_2 = p.ExternalPackagePhase({
    'project_name': 'humon',
    'repo_project_name': 'spacemeat/humon',
    'package_version': 'v0.2.2',
})


humon = p.run_makefile('external/humon')

exe = p.CompileAndLinkToExePhase({
    'name': 'hutest',
    'sources': ['main.cpp'],
    'inc_dir': 'external/humon',
}, humon.find_dep('humon_static_lib'))

# 'sync' is the action to get these
p.get_main_phase().depend_on([
    humon_phase_0_1_0,
    humon_phase_0_2_2,
    exe])
