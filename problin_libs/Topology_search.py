from math import log,isclose
from random import choice, shuffle
from problin_libs import min_llh, eps, nni_conv_eps
from treeswift import *
from problin_libs.EM_solver import EM_solver

class Topology_search:
    def __init__(self,treeTopo,solver,data={},prior={},params={}):
        self.treeTopo = treeTopo # treeTopo is a newick string
        self.solver = solver     # solver is a solver definition
        self.params = params   
        self.data = data
        self.prior = prior        
        self.tree_obj = read_tree_newick(self.treeTopo)
        self.tree_obj.suppress_unifurcations()
    
    def __renew_tree_obj__(self):
        self.tree_obj = read_tree_newick(self.treeTopo)
    
    def get_solver(self):
        return self.solver(self.treeTopo,self.data,self.prior,self.params)
                
    def update_from_solver(self,mySolver):
        self.treeTopo = mySolver.get_tree_newick()
        self.params = mySolver.get_params()

    def __mark_polytomies__(self,eps_len=1e-3):
        # mark and resolve all polytomies in self.tree_obj
        for node in self.tree_obj.traverse_preorder():
            node.mark = False
            if len(node.children) > 2:
                for c in node.children:
                    c.mark = True
        self.tree_obj.resolve_polytomies()
        for node in self.tree_obj.traverse_preorder():
            if not hasattr(node,'mark'):
                node.mark = True
                node.edge_length = eps_len                
        self.treeTopo = self.tree_obj.newick()        

    def search(self,maxiter=100,verbose=False,nreps=1,strategy={'resolve_polytomies':True,'only_marked':False,'optimize':False,'ultra_constr':False}):
        original_topo = self.treeTopo
        original_params = self.params
        nni_replicates = [(None,None)]*nreps
        for i in range(nreps):
            # resolve polytomies
            self.treeTopo = original_topo
            self.params = original_params
            self.__renew_tree_obj__()
            topo_list = []
            if strategy['resolve_polytomies']:
                self.__mark_polytomies__() 
                topo_list1,best_score = self.__search_one__(strategy,maxiter=maxiter,verbose=verbose,only_marked=True)
                topo_list += topo_list1
            if not strategy['only_marked']:    
                topo_list2,best_score = self.__search_one__(strategy,maxiter=maxiter,verbose=verbose,only_marked=False)
                topo_list += topo_list2
            nni_replicates[i] = (best_score,topo_list)
        return nni_replicates
    
    def __search_one__(self,strategy,maxiter=100,verbose=False,only_marked=False):
        # perform nni search
        mySolver = self.get_solver()
        curr_score = mySolver.score_tree(strategy=strategy)
        self.update_from_solver(mySolver)
        topo_list = [(self.treeTopo,curr_score)]            
        for nni_iter in range(maxiter):
            if verbose:
                print("NNI Iter:", nni_iter)
            new_score,n_attempts,success = self.single_nni(strategy,only_marked=only_marked)
            if not success:
                break
            curr_score = new_score
            topo_list.append((self.treeTopo,curr_score))
        return topo_list,curr_score 
    
    def single_nni(self,strategy,only_marked=False):
        branches = []
        for node in self.tree_obj.traverse_preorder():
            if node.is_leaf() or node.is_root():
                continue
            if not only_marked or node.mark:
                branches.append(node)
        # branch ordering: random 
        shuffle(branches)

        took = False
        score = -float("inf")
        n_attempts = 0
        while not took and branches:
            u = branches.pop()
            took,score = self.apply_nni(u,strategy)
            n_attempts += 1
        return score,n_attempts,took
    
    def apply_nni(self,u,strategy):
        # apply nni [DESTRUCTIVE FUNCTION! Changes tree inside this function.]
        v = u.get_parent()
        for node in v.child_nodes():
            if node != u:
                w = node
                break
        mySolver = self.get_solver()        
        curr_score = mySolver.score_tree(strategy=strategy)
        u_children = u.child_nodes()
        nni_moves = []

        for u_child in u_children:
            u_child.set_parent(v)
            u.remove_child(u_child)
            v.add_child(u_child)

            w.set_parent(u)
            v.remove_child(w)
            u.add_child(w)

            mySolver = self.solver(self.tree_obj.newick(),self.data,self.prior,self.params)
            new_score = mySolver.score_tree(strategy=strategy)

            if new_score > curr_score or isclose(new_score,curr_score,rel_tol=1e-3): # accept the new tree and params
                self.update_from_solver(mySolver)
                return True,new_score
            
            # Score doesn't improve --> reverse to the previous state
            u_child.set_parent(u)
            v.remove_child(u_child)
            u.add_child(u_child)
            
            w.set_parent(v)
            u.remove_child(w)
            v.add_child(w)            

        # no move accepted
        return False,curr_score