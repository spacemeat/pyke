''' external package test '''

import pyke as p

humon_repo = p.ExternalRepoPhase({
    'name': 'humon_repo',
    'package_name': 'humon',
    'repo_name': 'spacemeat/humon',
    'repo_version': 'v0.2.3',
    'using_pyke_makefile': 'project',
})

humon = p.PykeRepoPhase({
    'name': 'humon',
    'use_deps': ['static_lib.humon_archive'],
}, humon_repo)


fmt_repo = p.ExternalRepoPhase({
    'name': 'fmt_repo',
    'package_name': 'fmt',
    'repo_name': 'fmtlib/fmt',
    'repo_version': '11.0.1',
    'using_cmake_makefile': 'project',
})

fmt = p.CMakeRepoPhase({
    'name': 'fmt',
    'lib_kind': 'static',   # shared, static_pic
    'static_arg': '',
    'shared_arg': ' -DBUILD_SHARED_LIBS=TRUE',
    'static_pic_arg': ' -DCMAKE_POSITION_INDEPENDENT_CODE=TRUE',
    'cmake_args': '{{lib_kind}_arg} -DFMT_TEST=FALSE',
}, fmt_repo)

exe = p.CompileAndLinkToExePhase({
    'name': 'hutest',
    'sources': ['main.cpp'],
    'include_dirs': ['external/humon/include',
                     'external/fmt/include'],
    'lib_dirs': ['{external_anchor}/external/fmt/build/ext_deps.gnu.debug'],
    'libs': {'fmt': 'archive'}
}, [humon, fmt])

p.get_main_phase().depend_on([exe])
