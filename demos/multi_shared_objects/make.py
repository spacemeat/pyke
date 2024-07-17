import pyke as p

pa = p.PykeRepoPhase({
    'makefile': 'a-star',
    'use_deps': ['aaa', 'aas', 'asa', 'ass'],
})

ps = p.PykeRepoPhase({
    'makefile': 's-star',
    'use_deps': ['saa', 'sas', 'ssa', 'sss'],
})

m2 = p.CompileAndLinkToExePhase({'sources': ['main.c']},
                     [pa, ps])


p.get_main_phase().depend_on(m2)
