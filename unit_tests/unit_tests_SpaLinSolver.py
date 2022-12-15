import unittest
from problin_libs.ML_solver import SpaLin_solver

class SpaLinTest(unittest.TestCase):
    def test_1(self): 
        Q = [{1:1}]
        T = "((a:1,b:1):1,c:1):1;"
        msa = {'a':[1],'b':[1],'c':[1]}
        true_llh = -0.20665578828621584

        mySolver = SpaLin_solver(msa,Q,T,{'a':(0,0),'b':(0,0),'c':(0,0),'d':(0,0)},0)
        mySolver.az_partition(mySolver.params)
        my_llh = -mySolver.negative_llh()
        self.assertAlmostEqual(true_llh,my_llh,places=5,msg="SpaLinTest: test_1 failed.")