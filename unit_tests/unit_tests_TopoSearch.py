import os 
import unittest
from problin_libs.EM_solver import EM_solver
from problin_libs.ML_solver import ML_solver
from problin_libs.Topology_search import Topology_search
from treeswift import *

class TopoSearchTest(unittest.TestCase):
    def __list_topologies__(self,leafset):
        def __triplet__(a,b,c):
            return "((("+a+","+b+"),"+c+"));"
        def __add_one__(tree,new_leaf):    
            new_topos = []
            nodes = [node for node in tree.traverse_preorder() if not node.is_root()]
            for node in nodes:
                # create new topology
                new_node1 = Node()
                new_node2 = Node()
                new_node2.label = new_leaf
                pnode = node.parent
                pnode.remove_child(node)
                pnode.add_child(new_node1)
                new_node1.add_child(node)
                new_node1.add_child(new_node2)
                new_topos.append(tree.newick())
                # turn back
                pnode.remove_child(new_node1)
                pnode.add_child(node)
            return new_topos            

        # initialization
        a,b,c = leafset[-3:]
        T1 = __triplet__(a,b,c)
        T2 = __triplet__(a,c,b)
        T3 = __triplet__(b,c,a)
        topos = [T1,T2,T3]
        L = leafset[:-3]
        # elaborate
        while L:
            new_leaf = L.pop()
            new_topos = []
            for T in topos:
                tree = read_tree_newick(T)
                new_topos += __add_one__(tree,new_leaf)
            topos = new_topos    
        out_topos = [topo[1:-2]+";" for topo in topos]
        return out_topos    

    def __brute_force_search__(self,msa,Q,L,solver=EM_solver,ultra_constr=False,initials=1):
        topos = self.__list_topologies__(L)
        best_nllh = float("inf")
        best_tree = ""
        for T in topos:
            mySolver = solver(T,{'charMtrx':msa},{'Q':Q})
            nllh = mySolver.optimize(initials=initials,verbose=-1,ultra_constr=ultra_constr)
            print(T,nllh)
            if nllh < best_nllh:
                best_nllh = nllh
                best_tree = mySolver.tree.newick()
        return best_nllh,best_tree 
    
    # topology search with EM_solver
    def test_1(self):
        Q = [{0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}]
        msa = {'a':[1, 1, 0, 0, 0], 'b':[1, 1, 1, 0, 0], 'c':[0, 0, 0, 1, 0], 'd':[0, 0, 0, 1, 0]}
        #best_nllh,best_tree = self.__brute_force_search__(msa,Q,['a','b','c','d'],solver=ML_solver)
        
        nllh_bf = 7.776628108742671 # precomputed from brute-force
        
        T0 = '((a,c),(b,d));'
        data = {'charMtrx':msa}
        prior = {'Q':Q}
        params = {'phi':0,'nu':0}
        
        # topology search with EM_solver
        myTopoSearch_EM = Topology_search(T0,EM_solver,data=data,prior=prior,params=params)
        nni_replicates = myTopoSearch_EM.search(maxiter=200,nreps=1,verbose=False)

        max_score = -float("inf")
        T1 = ""
        for score,tree_topos in nni_replicates:
            if score > max_score:
                max_score = score
                T1,_,_ = tree_topos[-1]
        nllh_nni_EM = -max_score
        
        self.assertAlmostEqual(nllh_bf,nllh_nni_EM,places=4,msg="TopoSearchTest: test_1 failed.")
    
    # topology search with ML_solver
    def test_2(self):
        Q = [{0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}]
        msa = {'a':[1, 1, 0, 0, 0], 'b':[1, 1, 1, 0, 0], 'c':[0, 0, 0, 1, 0], 'd':[0, 0, 0, 1, 0]}
        nllh_bf = 7.776628108742671 # precomputed from brute-force
        
        T0 = '((a,c),(b,d));'
        data = {'charMtrx':msa}
        prior = {'Q':Q}
        params = {'nu':0,'phi':0}
        
        # topology search with ML_solver
        myTopoSearch_ML = Topology_search(T0,ML_solver,data=data,prior=prior,params=params)
        nni_replicates = myTopoSearch_ML.search(maxiter=200,verbose=False,nreps=1)

        max_score = -float("inf")
        T1 = ""
        for score,tree_topos in nni_replicates:
            if score > max_score:
                max_score = score
                T1,_,_ = tree_topos[-1]
        nllh_nni_ML = -max_score
        
        self.assertAlmostEqual(nllh_bf,nllh_nni_ML,places=4,msg="TopoSearchTest: test_2 failed.")
    
    # resolve polytomies and continue beyond that
    def test_3(self):
        Q = [{0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}]
        msa = {'a':[1, 1, 0, 0, 0], 'b':[1, 1, 1, 0, 0], 'c':[0, 0, 0, 1, 0], 'd':[0, 0, 0, 1, 0]}
        nllh_bf = 7.776628108742671 # precomputed from brute-force
        
        T0 = '(a,b,c,d);'
        data = {'charMtrx':msa}
        prior = {'Q':Q}
        params = {'nu':0,'phi':0}
        
        myTopoSearch = Topology_search(T0,EM_solver,data=data,prior=prior,params=params)
        nni_replicates = myTopoSearch.search(maxiter=200,verbose=False,strategy={'resolve_polytomies':True,'only_marked':False,'optimize':True,'ultra_constr':False},nreps=1)
        max_score = -float("inf")
        T1 = ""
        for score,tree_topos in nni_replicates:
            if score > max_score:
                max_score = score
                T1,_,_ = tree_topos[-1]
        nllh_nni = -max_score
        
        self.assertAlmostEqual(nllh_bf,nllh_nni,places=4,msg="TopoSearchTest: test_3 failed.")

    # only resolve polytomies
    def test_4(self):
        Q = [{0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}]
        msa = {'a':[1, 1, 0, 0, 0], 'b':[1, 1, 1, 0, 0], 'c':[0, 0, 0, 1, 0], 'd':[0, 0, 0, 1, 0]}
        nllh_bf = 7.776628108742671 # precomputed from brute-force
        
        T0 = '((a,b),c,d);'
        data = {'charMtrx':msa}
        prior = {'Q':Q}
        params = {'nu':0,'phi':0}
        
        myTopoSearch = Topology_search(T0,EM_solver,data=data,prior=prior,params=params)
        nni_replicates = myTopoSearch.search(maxiter=200,verbose=False,strategy={'resolve_polytomies':True,'only_marked':True,'ultra_constr':False},nreps=5)
        max_score = -float("inf")
        T1 = ""
        for score,tree_topos in nni_replicates:
            if score > max_score:
                max_score = score
                T1,_,_ = tree_topos[-1]
        nllh_nni = -max_score
        
        self.assertAlmostEqual(nllh_bf,nllh_nni,places=4,msg="TopoSearchTest: test_4 failed.")
    
    # only resolve polytomies
    def test_5(self):
        Q = [{0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}]
        msa = {'a':[1, 1, 0, 0, 0], 'b':[1, 1, 1, 0, 0], 'c':[0, 0, 0, 1, 0], 'd':[0, 0, 0, 1, 0]}
        nllh_bf = 11.734156069913272 # precomputed from brute-force
        
        T0 = '((a,c),(b,d));'
        data = {'charMtrx':msa}
        prior = {'Q':Q}
        params = {'phi':0,'nu':0}
        
        # topology search with EM_solver
        myTopoSearch = Topology_search(T0,EM_solver,data=data,prior=prior,params=params)
        nni_replicates = myTopoSearch.search(maxiter=200,verbose=False,strategy={'resolve_polytomies':True,'only_marked':True,'ultra_constr':False},nreps=1)

        max_score = -float("inf")
        T1 = ""
        for score,tree_topos in nni_replicates:
            if score > max_score:
                max_score = score
                T1,_,_ = tree_topos[-1]
        nllh_nni = -max_score
        
        self.assertAlmostEqual(nllh_bf,nllh_nni,places=4,msg="TopoSearchTest: test_5 failed.")
    
    # resolve polytomies set to true on starting tree without polytomies
    def test_6(self):
        Q = [{0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}]
        msa = {'a':[0, 1, 1, 1, 1], 'b':[1, 0, 0, 0, 0], 'c':[1, 0, 0, 0, 0], 'd':[0, 1, 1, 1, 1]}
        nllh_bf = 5.004039260440974
        
        T0 = '((a,b),(c,d));'
        data = {'charMtrx':msa}
        prior = {'Q':Q}
        params = {'phi':0,'nu':0}
        
        myTopoSearch = Topology_search(T0,EM_solver,data=data,prior=prior,params=params)
        nni_replicates = myTopoSearch.search(maxiter=200,verbose=False,strategy={'resolve_polytomies':True,'only_marked':False,'ultra_constr':False},nreps=1)

        max_score = -float("inf")
        T1 = ""
        for score,tree_topos in nni_replicates:
            if score > max_score:
                max_score = score
                T1,_,_ = tree_topos[-1]
        nllh_nni = -max_score
        self.assertAlmostEqual(nllh_bf,nllh_nni,places=4,msg="TopoSearchTest: test_6 failed.")
        
    # resolve polytomies only
    def test_7(self):
        Q = [{0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}]
        msa = {'a':[0, 1, 1, 1, 1], 'b':[1, 0, 0, 0, 0], 'c':[1, 0, 0, 0, 0], 'd':[0, 1, 1, 1, 1]}
        nllh_bf = 10.008063503552208
        
        T0 = '((a,b),c,d);'
        data = {'charMtrx':msa}
        prior = {'Q':Q}
        params = {'phi':0,'nu':0}
        
        myTopoSearch = Topology_search(T0,EM_solver,data=data,prior=prior,params=params)
        nni_replicates = myTopoSearch.search(maxiter=200,verbose=False,strategy={'resolve_polytomies':True,'only_marked':True,'ultra_constr':False},nreps=1)

        max_score = -float("inf")
        T1 = ""
        for score,tree_topos in nni_replicates:
            if score > max_score:
                max_score = score
                T1,_,_ = tree_topos[-1]
        nllh_nni = -max_score
        self.assertAlmostEqual(nllh_bf,nllh_nni,places=4,msg="TopoSearchTest: test_7 failed.")
    
    # resolve polytomies only
    def test_8(self):
        Q = [{0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}]
        msa = {'a':[0, 1, 1, 1, 1], 'b':[1, 0, 0, 0, 0], 'c':[1, 0, 0, 0, 0], 'd':[0, 1, 1, 1, 1]}
        nllh_bf = 10.008063504603857
        
        T0 = '((c,d),a,b);'
        data = {'charMtrx':msa}
        prior = {'Q':Q}
        params = {'phi':0,'nu':0}
        
        myTopoSearch = Topology_search(T0,EM_solver,data=data,prior=prior,params=params)
        nni_replicates = myTopoSearch.search(maxiter=200,verbose=False,strategy={'resolve_polytomies':True,'only_marked':True,'ultra_constr':False},nreps=1)

        max_score = -float("inf")
        T1 = ""
        for score,tree_topos in nni_replicates:
            if score > max_score:
                max_score = score
                T1,_,_ = tree_topos[-1]
        nllh_nni = -max_score
        self.assertAlmostEqual(nllh_bf,nllh_nni,places=4,msg="TopoSearchTest: test_8 failed.")
    
    # enforce ultrametric
    def test_9(self):
        Q = [{0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}]
        msa = {'a':[0, 1, 1, 1, 1], 'b':[1, 0, 0, 0, 0], 'c':[1, 0, 0, 0, 0], 'd':[0, 1, 1, 1, 1]}
        nllh_bf = 6.931486808809165 # pre-computed using brute-force search
        
        T0 = '((a,b),(c,d));'
        data = {'charMtrx':msa}
        prior = {'Q':Q}
        params = {'phi':0,'nu':0}
        
        myTopoSearch = Topology_search(T0,EM_solver,data=data,prior=prior,params=params)
        nni_replicates = myTopoSearch.search(maxiter=200,verbose=False,strategy={'resolve_polytomies':True,'only_marked':False,'ultra_constr':True},nreps=1)

        max_score = -float("inf")
        T1 = ""
        for score,tree_topos in nni_replicates:
            if score > max_score:
                max_score = score
                T1,_,_ = tree_topos[-1]
        nllh_nni = -max_score
        self.assertAlmostEqual(nllh_bf,nllh_nni,places=4,msg="TopoSearchTest: test_9 failed.")
    
    # enforce ultrametric
    def test_10(self):
        Q = [{0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}, {0:0, 1:1.0}]
        msa = {'a':[0, 1, 1, 1, 1], 'b':[1, 0, 0, 0, 0], 'c':[1, 0, 0, 0, 0], 'd':[0, 1, 1, 1, 1]}
        nllh_bf = 6.931486808809165 # pre-computed using brute-force search
        
    # enforce ultrametric
        T0 = '(a,b,c,d);'
        data = {'charMtrx':msa}
        prior = {'Q':Q}
        params = {'phi':0,'nu':0}
        
        myTopoSearch = Topology_search(T0,EM_solver,data=data,prior=prior,params=params)
        nni_replicates = myTopoSearch.search(maxiter=200,verbose=False,strategy={'resolve_polytomies':True,'only_marked':False,'ultra_constr':True},nreps=1)

        max_score = -float("inf")
        T1 = ""
        for score,tree_topos in nni_replicates:
            if score > max_score:
                max_score = score
                T1,_,_ = tree_topos[-1]
        nllh_nni = -max_score
        self.assertAlmostEqual(nllh_bf,nllh_nni,places=4,msg="TopoSearchTest: test_10 failed.")
