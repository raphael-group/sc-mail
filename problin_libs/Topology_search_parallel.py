from math import log,isclose,exp
import timeit
from random import choice, shuffle, random
from problin_libs import *
from treeswift import *
from problin_libs.EM_solver import EM_solver
from problin_libs.Topology_search import Topology_search
from copy import deepcopy
from problin_libs.lca_lib import find_LCAs
from multiprocessing import Pool

class Topology_search_parallel(Topology_search):
    def single_nni(self,curr_score,nni_iter,strategy,only_marked=False):
        all_nni_moves = self.list_all_nni(strategy,only_marked=only_marked)
        N = len(all_nni_moves)
        batch_size = 16
        curr_start_idx = 0
        curr_end_idx = min(batch_size,N)
        #best_score = curr_score
        retry_nni_moves = []
        checked_all = False
        took = False
        while True:
            if checked_all:
                subset_nni_moves = retry_nni_moves
            else:
                subset_nni_moves = all_nni_moves[curr_start_idx:curr_end_idx]
            #start_time = timeit.default_timer()
            with Pool() as pool:
                nni_results = pool.map(self.apply_nni,subset_nni_moves) 
            #stop_time = timeit.default_timer()
            #print("Time",stop_time-start_time)
            #best_batch_score = -float("inf")  
            #best_batch_result = None  
            for i,nni_result in enumerate(nni_results):
                if nni_result['status'] == "optimal":
                    new_score = nni_result['score']
                    '''
                    if new_score > best_batch_score:
                        best_batch_score = new_score
                        best_batch_result = nni_result '''
                    if self.__accept_proposal__(curr_score,new_score,nni_iter): # accept the new tree and params               
                        print(curr_score,new_score,'accept') 
                        u,v,u_child,w = nni_result['cache']
                        u_child.set_parent(v)
                        u.remove_child(u_child)
                        v.add_child(u_child)
                        w.set_parent(u)
                        v.remove_child(w)
                        u.add_child(w)
                        self.update_from_solver(nni_result['mySolver'])
                        self.tree_obj = nni_result['tree_obj']
                        took = True
                        break
                    print(curr_score,new_score,'reject') 
                elif not checked_all:
                    nwk_str,score_tree_strategy,(u,v,u_child,w) = subset_nni_moves[i]
                    score_tree_strategy['fixed_brlen'] = {}
                    retry_move = (nwk_str,score_tree_strategy,(u,v,u_child,w)) 
                    retry_nni_moves.append(retry_move)
            if checked_all or took:
                break    
            checked_all = (curr_end_idx == N)
            curr_start_idx += batch_size
            curr_end_idx = min(curr_start_idx+batch_size,N)
        print(curr_end_idx,curr_score,new_score,took)   
        return new_score,curr_end_idx,took    
   
    def apply_nni(self,arguments):
        treeTopo,score_tree_strategy,cache = arguments
        mySolver = self.solver(treeTopo,self.data,self.prior,self.params)            
        score,status = mySolver.score_tree(strategy=score_tree_strategy)
        nni_result = {'mySolver':mySolver,'score':score,'status':status,'cache':cache,'tree_obj':self.tree_obj}
        return nni_result

    def list_all_nni(self,strategy,only_marked=False):    
        branches = []
        for node in self.tree_obj.traverse_preorder():
            if node.is_leaf() or node.is_root():
                continue
            if not only_marked or node.mark:
                branches.append(node)
        shuffle(branches)        
        all_nni_moves = []
        for u in branches:        
            v = u.get_parent()
            for node in v.child_nodes():
                if node != u:
                    w = node
                    break                
            u_children = u.child_nodes()
            score_tree_strategy = deepcopy(strategy)
            score_tree_strategy['fixed_brlen'] = {}
            if strategy['local_brlen_opt']:
                score_tree_strategy['fixed_nu'] = self.params['nu'] 
                score_tree_strategy['fixed_phi'] = self.params['phi'] 
                free_branches = set(u.child_nodes() + v.child_nodes() + [v])
                fixed_branches_anchors = []
                for node in self.tree_obj.traverse_postorder():
                    if node.is_leaf():
                        node.anchors = (node.label,node.label)
                    else:
                        C = node.child_nodes()
                        a = C[0].anchors[0]
                        b = C[-1].anchors[0]
                        node.anchors = (a,b)
                    if not node in free_branches:
                        fixed_branches_anchors.append(node.anchors)
                tree = read_tree_newick(self.treeTopo)
                fixed_branches = find_LCAs(tree,fixed_branches_anchors)
                fixed_brlen = {}
                for i,node in enumerate(fixed_branches):
                    fixed_brlen[fixed_branches_anchors[i]] = node.edge_length
                score_tree_strategy['fixed_brlen'] = fixed_brlen
            shuffle(u_children)
            for u_child in u_children:
                # apply the nni move
                u_child.set_parent(v)
                u.remove_child(u_child)
                v.add_child(u_child)

                w.set_parent(u)
                v.remove_child(w)
                u.add_child(w)
                # get the new tree string
                nwk_str = self.tree_obj.newick()
                all_nni_moves.append((nwk_str,score_tree_strategy,(u,v,u_child,w)))
                # turn back the move
                u_child.set_parent(u)
                v.remove_child(u_child)
                u.add_child(u_child)
                
                w.set_parent(v)
                u.remove_child(w)
                v.add_child(w)            
        return all_nni_moves             