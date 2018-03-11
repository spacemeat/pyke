import unittest
#from .context import pyke
from pyke import command as com

#com = pyke.command
#dir (com)


class command_tests(unittest.TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
        
    def check_commands(tested, known):
        if tested.name == known.name:
            if ((tested.parent == None and known.parent == None) or
                (tested.parent.name == known.parent.name)):
                if (len(tested.children) == len(known.children)):
                    for i in range(0, len(tested.children)):
                        if (command_tests.check_commands(tested.children[i], 
                            known.children[i]) == False):
                            return False
                    return True
        return False
        
    def test_empty_args(self):
        commands = com.parser().parse_args("")
        known = com.command()
        self.assertTrue(command_tests.check_commands(commands, known))

    def test_semi_only(self):
        commands = com.parser().parse_args(";")
        known = com.command()
        self.assertTrue(command_tests.check_commands(commands, known))

    def test_tree_basic(self):
        commands = com.parser().parse_args("aaa: bbb1: ccc11, ccc12;, bbb2: ccc21, ccc22; ;, zzz;")
        root = com.command()
        aaa = com.command("aaa", root)
        bbb1 = com.command("bbb1", aaa)
        bbb2 = com.command("bbb2", aaa)
        ccc11 = com.command("ccc11", bbb1)
        ccc12 = com.command("ccc12", bbb1)
        ccc21 = com.command("ccc21", bbb2)
        ccc22 = com.command("ccc22", bbb2)
        aaa.children.append(bbb1)
        aaa.children.append(bbb2)
        bbb1.children.append(ccc11)
        bbb1.children.append(ccc12)
        bbb2.children.append(ccc21)
        bbb2.children.append(ccc22)
        zzz = com.command("zzz", root)
        root.children.append(aaa)
        root.children.append(zzz)
        self.assertTrue(command_tests.check_commands(commands, root))

#if __name__ == '__main__':
#    unittest.main()
