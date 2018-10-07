import json
import unittest
from pyke.ObjectData import ObjectData
import pdb
import sys

class TestObjectData(unittest.TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass

    def test_merge(self):
        testSuiteJson = {}
        with open('test/test_json.json') as f:
            testSuiteJson = json.loads(f.read())

        for testName, testJson in testSuiteJson.items():
            with self.subTest(testName):
                initialJson = testJson.get('initial', {})
                modifiersJson = testJson.get('modifiers', [])
                usagesJson = testJson.get('usages', [])
                resolvesJson = testJson.get('resolves', [])
                finalJson = testJson.get('result', {})

                computed = ObjectData(initialJson)
                for mod in modifiersJson:
                    computed.merge(mod)
                
                for usage in usagesJson:
                    computed.use(usage)
                
                for resolve in resolvesJson:
                    computed.resolveGroupDefault(resolve)

                computed.resolveAllGroupDefaults()

                def recurseMatch(lhs, rhs):
                    if type(lhs) != type(rhs):
                        return False

                    if isinstance(rhs, list):
                        if len(lhs) != len(rhs):
                            return False
                        for idx, e in enumerate(rhs):
                            if recurseMatch(lhs[idx], e) == False:
                                return False

                    elif isinstance(rhs, dict):
                        if len(lhs) != len(rhs):
                            return False

                        for k, v in rhs.items():
                            if k not in lhs:
                                return False
                            else:
                                if recurseMatch(lhs[k], v) == False:
                                    return False
                    else:
                        if lhs != rhs:
                            return False
                    
                    return True

                msg ='{}:\nComputed:\n{}\nExpected:\n{}\n'.format(
                    testName,
                    json.dumps(computed.data, indent=2),
                    json.dumps(finalJson, indent=2))

                self.assertTrue(
                    recurseMatch(computed.data, finalJson),
                    msg=msg)
        

#if __name__ == '__main__':
#    unittest.main()
