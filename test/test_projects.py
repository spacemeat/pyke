import unittest
import shutil
import os
from pyke.projects import projects as p

class projects_tests(unittest.TestCase):
    test_base_path = "/tmp/pyke-test"
    
    def setUp(self):
        self.shelved_wd = os.getcwd()
        tb_path = projects_tests.test_base_path
        
        # rm -rf the test base
        shutil.rmtree(tb_path, True)
        
        self.a1path = os.path.join(tb_path, "a1")
        self.a2path = os.path.join(tb_path, "a2")
        self.a11path = os.path.join(tb_path, "a1", "a11")
        self.a12path = os.path.join(tb_path, "a1", "a12")
        self.a21path = os.path.join(tb_path, "a2", "a21")
        self.a22path = os.path.join(tb_path, "a2", "a22")
        self.a111path = os.path.join(tb_path, "a1", "a11", "a111")

        os.mkdir(tb_path)
        os.mkdir(self.a1path)
        os.mkdir(self.a2path)
        os.mkdir(self.a11path)
        os.mkdir(self.a12path)
        os.mkdir(self.a21path)
        os.mkdir(self.a22path)
        os.mkdir(self.a111path)

        shutil.copyfile(os.path.abspath("test/a.pyke.json"),
                        os.path.join(tb_path, "pyke.json"))
        shutil.copyfile(os.path.abspath("test/a1.pyke.json"),
                        os.path.join(self.a1path, "pyke.json"))
        shutil.copyfile(os.path.abspath("test/a2.pyke.json"),
                        os.path.join(self.a2path, "pyke.json"))
        shutil.copyfile(os.path.abspath("test/a11.pyke.json"),
                        os.path.join(self.a11path, "pyke.json"))
        shutil.copyfile(os.path.abspath("test/a12.pyke.json"),
                        os.path.join(self.a12path, "pyke.json"))
        shutil.copyfile(os.path.abspath("test/a21.pyke.json"),
                        os.path.join(self.a21path, "pyke.json"))
        shutil.copyfile(os.path.abspath("test/a22.pyke.json"),
                        os.path.join(self.a22path, "pyke.json"))
    
    def tearDown(self):
        tb_path = projects_tests.test_base_path
        # rm -rf the test base
        shutil.rmtree(tb_path, True)
        os.chdir(self.shelved_wd)

    def test_load_all_from_top(self):
        tb_path = projects_tests.test_base_path
        os.chdir(tb_path)
        pp = p.projects()
        pp.load_all()

        pio = pp.projects_in_order
 #       print (*pio, sep='\n')
        
        self.assertEqual(len(pio), 15)
        self.assertTrue(pio[ 0][0] == tb_path + "/aproj")
        self.assertTrue(pio[ 1][0] == self.a1path + "/a1-p1")
        self.assertTrue(pio[ 2][0] == self.a1path + "/a1-p2")
        self.assertTrue(pio[ 3][0] == self.a1path + "/a1-p3")
        self.assertTrue(pio[ 4][0] == self.a1path + "/a1-p4")
        self.assertTrue(pio[ 5][0] == self.a11path + "/a11-p1")
        self.assertTrue(pio[ 6][0] == self.a11path + "/a11-p2")
        self.assertTrue(pio[ 7][0] == self.a11path + "/a11-p3")
        self.assertTrue(pio[ 8][0] == self.a11path + "/a11-p4")
        self.assertTrue(pio[ 9][0] == self.a11path + "/a11-p5")
        self.assertTrue(pio[10][0] == self.a12path + "/a12-p1")
        self.assertTrue(pio[11][0] == self.a2path + "/a2-p1")
        self.assertTrue(pio[12][0] == self.a2path + "/a2-p2")
        self.assertTrue(pio[13][0] == self.a21path + "/a21-p1")
        self.assertTrue(pio[14][0] == self.a22path + "/a22-p1")
        
        self.assertTrue(pio[ 0][1].name == "aproj")
        self.assertTrue(pio[ 1][1].name == "a1-p1")
        self.assertTrue(pio[ 2][1].name == "a1-p2")
        self.assertTrue(pio[ 3][1].name == "a1-p3")
        self.assertTrue(pio[ 4][1].name == "a1-p4")
        self.assertTrue(pio[ 5][1].name == "a11-p1")
        self.assertTrue(pio[ 6][1].name == "a11-p2")
        self.assertTrue(pio[ 7][1].name == "a11-p3")
        self.assertTrue(pio[ 8][1].name == "a11-p4")
        self.assertTrue(pio[ 9][1].name == "a11-p5")
        self.assertTrue(pio[10][1].name == "a12-p1")
        self.assertTrue(pio[11][1].name == "a2-p1")
        self.assertTrue(pio[12][1].name == "a2-p2")
        self.assertTrue(pio[13][1].name == "a21-p1")
        self.assertTrue(pio[14][1].name == "a22-p1")
        
    def test_load_until_from_a111_one_level(self):
        os.chdir(self.a111path)
        pp = p.projects()
        pp.load_until("a11-p1")
        
        pio = pp.projects_in_order
 #       print (*pio, sep='\n')

        self.assertEqual(len(pio), 5)
        self.assertTrue(pio[0][0] == self.a11path + "/a11-p1")
        self.assertTrue(pio[1][0] == self.a11path + "/a11-p2")
        self.assertTrue(pio[2][0] == self.a11path + "/a11-p3")
        self.assertTrue(pio[3][0] == self.a11path + "/a11-p4")
        self.assertTrue(pio[4][0] == self.a11path + "/a11-p5")

        self.assertTrue(pio[0][1].name == "a11-p1")
        self.assertTrue(pio[1][1].name == "a11-p2")
        self.assertTrue(pio[2][1].name == "a11-p3")
        self.assertTrue(pio[3][1].name == "a11-p4")
        self.assertTrue(pio[4][1].name == "a11-p5")
        
    def test_load_until_from_a22_one_level(self):
        os.chdir(self.a22path)
        pp = p.projects()
        pp.load_until("a2-p1")
        
        pio = pp.projects_in_order
#        print (*pio, sep='\n')

        self.assertEqual(len(pio), 3)
        self.assertTrue(pio[0][0] == self.a22path + "/a22-p1")
        self.assertTrue(pio[1][0] == self.a2path + "/a2-p1")
        self.assertTrue(pio[2][0] == self.a2path + "/a2-p2")
        
    def test_load_until_from_a111_one_level(self):
        os.chdir(self.a111path)
        pp = p.projects()
        pp.load_until("a12-p1")
        
        pio = pp.projects_in_order
#        print (*pio, sep='\n')

        self.assertEqual(len(pio), 10)
        self.assertTrue(pio[0][0] == self.a11path + "/a11-p1")
        self.assertTrue(pio[1][0] == self.a11path + "/a11-p2")
        self.assertTrue(pio[2][0] == self.a11path + "/a11-p3")
        self.assertTrue(pio[3][0] == self.a11path + "/a11-p4")
        self.assertTrue(pio[4][0] == self.a11path + "/a11-p5")
        self.assertTrue(pio[5][0] == self.a1path + "/a1-p1")
        self.assertTrue(pio[6][0] == self.a1path + "/a1-p2")
        self.assertTrue(pio[7][0] == self.a1path + "/a1-p3")
        self.assertTrue(pio[8][0] == self.a1path + "/a1-p4")
        self.assertTrue(pio[9][0] == self.a12path + "/a12-p1")

        self.assertTrue(pio[0][1].name == "a11-p1")
        self.assertTrue(pio[1][1].name == "a11-p2")
        self.assertTrue(pio[2][1].name == "a11-p3")
        self.assertTrue(pio[3][1].name == "a11-p4")
        self.assertTrue(pio[4][1].name == "a11-p5")
        self.assertTrue(pio[5][1].name == "a1-p1")
        self.assertTrue(pio[6][1].name == "a1-p2")
        self.assertTrue(pio[7][1].name == "a1-p3")
        self.assertTrue(pio[8][1].name == "a1-p4")
        self.assertTrue(pio[9][1].name == "a12-p1")
    
    def test_load_until_successive(self):
        os.chdir(self.a111path)
        pp = p.projects()
        
#        print ("finding a11-p1:")
        pp.load_until("a11-p1")
        pio = pp.projects_in_order
#        print (*pio, sep='\n')
        self.assertEqual(len(pio), 5)

#        print ("finding a11-p4:")
        pp.load_until("a11-p4")
        pio = pp.projects_in_order
#        print (*pio, sep='\n')
        self.assertEqual(len(pio), 9)

#        print ("finding a1-p2:")
        pp.load_until("a1-p2")
        pio = pp.projects_in_order
#        print (*pio, sep='\n')
        self.assertEqual(len(pio), 9)

#        print ("finding a12-p1:")
        pp.load_until("a12-p1")
        pio = pp.projects_in_order
#        print (*pio, sep='\n')
        self.assertEqual(len(pio), 10)
        
#        print ("finding a22-p1:")
        pp.load_until("a22-p1")
        pio = pp.projects_in_order
#        print (*pio, sep='\n')
        self.assertEqual(len(pio), 15)

