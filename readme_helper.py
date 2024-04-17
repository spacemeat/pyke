''' Parses option strings from a phase class for the README.'''

from pathlib import Path

def parse_phase(filename):
    ''' Read for optsions.'''
    print (f'{filename}:')
    with open(filename, 'rt', encoding='utf-8') as f:
        reading = False
        comment = ''
        for line in f.readlines():
            if line.strip() == 'self.options |= {':
                reading = True
                continue
            if reading:
                line = line.strip()
                if line == '}':
                    break
                if line.startswith('##'):
                    comment = ''
                elif line.startswith('#'):
                    comment += line[1:]
                elif line != '':
                    if comment != '':
                        k, v = line.split(':')
                        k = k.strip()[1:-1]
                        v = v.strip().replace('|', '\\|')
                        if v.endswith(','):
                            v = v[:-1]
                        print (f'|{k}   |{v}   |{comment.strip()}')
                    comment = ''
    print ()

parse_phase(f"{Path(__file__).parent / 'src' / 'pyke' / 'phases' / 'phase.py'}")
parse_phase(f"{Path(__file__).parent / 'src' / 'pyke' / 'phases' / 'c_family_build.py'}")
