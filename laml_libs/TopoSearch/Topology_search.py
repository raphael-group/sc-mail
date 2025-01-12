from math import log,isclose,exp
import timeit
from random import choice, shuffle, random
from laml_libs import *
from treeswift import *
from laml_libs.PMM_original.EM_solver import EM_solver
from copy import deepcopy
from laml_libs.Utils.lca_lib import find_LCAs

class Topology_search:
    def __init__(self,treeTopoList,solver,data={},prior={},params={},T_cooldown=20,alpha_cooldown=0.9):
        self.treeTopoList = treeTopoList # treeTopoList is a list of newick strings
        self.solver = solver     # solver is a solver definition
        self.params = params   
        self.data = data
        self.prior = prior
        #self.compute_cache = [{} for _ in range(len(self.treeTopoList))]
        self.compute_cache = None
        self.__renew_treeList_obj()
        # identify polytomies
        self.has_polytomy = False
        for tree in self.treeList_obj:
            for node in tree.traverse_preorder():
                if len(node.children) > 2:
                    self.has_polytomy = True
                    break        
        self.treeTopoList = []
        for tree in self.treeList_obj:
            self.treeTopoList.append(tree.newick())
        self.T_cooldown = T_cooldown
        self.alpha_cooldown = alpha_cooldown
        self.b = 1/(1-1/self.alpha_cooldown**self.T_cooldown)
        self.a = -self.b/self.alpha_cooldown**self.T_cooldown

    def __renew_treeList_obj(self):
        self.treeList_obj = []
        for treeTopo in self.treeTopoList:
            tree = read_tree_newick(treeTopo)
            tree.suppress_unifurcations()
            self.treeList_obj.append(tree)
    
    def get_solver(self):
        return self.solver(self.treeTopoList,self.data,self.prior,self.params)
                
    def update_from_solver(self,mySolver,collect_cache=True):
        self.treeTopoList = mySolver.get_tree_newick()
        self.params = mySolver.get_params()
        if collect_cache:
            self.compute_cache = mySolver.get_compute_cache()
        else:    
            self.compute_cache = None
            #self.compute_cache = [{} for _ in range(len(self.treeTopoList))]

    def __mark_polytomies(self,eps_len=1e-3):
        # mark and resolve all polytomies in self.treeList_obj
        self.has_polytomy = False
        for tree in self.treeList_obj:
            for node in tree.traverse_preorder():
                node.mark = False
                if len(node.children) > 2:
                    self.has_polytomy = True
            tree.resolve_polytomies()
        
        for tree in self.treeList_obj:
            for node in tree.traverse_preorder():
                if not hasattr(node,'mark'):
                    node.mark = True
                    node.edge_length = eps_len  
        self.treeTopoList = [tree.newick() for tree in self.treeList_obj]

    def accept_proposal(self,curr_score,new_score,t):
        if new_score > curr_score:
            return True
        T = max(1e-12,self.a*self.alpha_cooldown**t + self.b)
        p = min(exp((new_score-curr_score-1e-12)/T),1)
        return random() < p

    def search(self,resolve_polytomies=True,maxiter=100,verbose=False,nreps=1,strategy=DEFAULT_STRATEGY,checkpoint_file=None):
        original_topos = self.treeTopoList
        best_trees = None
        best_score = -float("inf")
        best_params = None
        for i in range(nreps):
            # resolve polytomies
            if verbose:
                print("Performing nni-search " + str(i+1))
            self.treeTopoList = original_topos
            self.__renew_treeList_obj()
            if resolve_polytomies:
                self.__mark_polytomies()
            if strategy['resolve_search_only']:
                if verbose:
                    print("Only perform local nni moves to resolve polytomies")
                if self.has_polytomy:
                    trees,score,params = self.__search_one(strategy,maxiter=maxiter,verbose=verbose,only_marked=True,checkpoint_file=checkpoint_file)
                else: # score this tree topology (optimize all numerical params)
                    if verbose:
                        print("Found no polytomy to resolve. Optimizing numerical parameters without further topology search")
                    mySolver = self.get_solver()
                    score_tree_strategy = deepcopy(strategy)
                    score_tree_strategy['fixed_brlen'] = None
                    score,status = mySolver.score_tree(strategy=score_tree_strategy)
                    self.update_from_solver(mySolver,collect_cache=True)
                    trees = self.treeTopoList
                    params = self.params
            else:    
                if verbose:
                    print("Perform nni moves for full topology search")
                    if self.has_polytomy and resolve_polytomies:                        
                        print("Found polytomies in the input tree(s). Arbitrarily resolving them to obtain fully resolved initial tree(s).") 
                trees,score,params = self.__search_one(strategy,maxiter=maxiter,verbose=verbose,only_marked=False,checkpoint_file=checkpoint_file)
            # The final optimization of parameters
            if verbose:
                print("Optimal topology found. Re-optimizing other parameters ...")
            self.treeTopoList = trees
            self.params = params
            self.__renew_treeList_obj()
            mySolver = self.get_solver()
            score_tree_strategy = deepcopy(strategy)
            score_tree_strategy['fixed_brlen'] = None
            score,status = mySolver.score_tree(strategy=score_tree_strategy)
            self.update_from_solver(mySolver,collect_cache=True)
            trees = self.treeTopoList
            params = self.params
            if verbose:
                print("Optimal score for this search: " + str(score))
            # compare to the best_score of previous searches
            if score > best_score:
                best_score = score
                best_trees = trees    
                best_params = params

        # synchronization        
        self.treeTopoList = best_trees
        self.params = best_params
        
        return best_trees,best_score,best_params
    
    def __search_one(self,strategy,maxiter=100,verbose=False,only_marked=False, checkpoint_file=None):
        # optimize branch lengths and other parameters for the starting tree
        mySolver = self.get_solver()
        score_tree_strategy = deepcopy(strategy)
        score_tree_strategy['fixed_brlen'] = None
        curr_score,status = mySolver.score_tree(strategy=score_tree_strategy)
        if verbose:
            if self.has_polytomy:
                print("Initial score (polytomies were arbitrarily resolved): " + str(curr_score))
            else:
                print("Initial score: " + str(curr_score))
        self.update_from_solver(mySolver,collect_cache=True)
        best_score = curr_score
        best_trees = self.treeTopoList
        best_params = self.params 
        # perform nni search
        for nni_iter in range(maxiter):
            if verbose:
                print("NNI Iter:", nni_iter)
                start_time = timeit.default_timer()
            new_score,n_attempts,success = self.single_nni(curr_score,nni_iter,strategy,only_marked=only_marked)
            if verbose:
                print("Number of trees checked " + str(n_attempts))
                stop_time = timeit.default_timer()
                print("Runtime (s):", stop_time - start_time)
            if not success:
                if verbose:
                    print("None of the NNI neighbor trees was accepted. Stop NNI search")
                break
            curr_score = new_score
            if verbose:
                print("Current score: " + str(curr_score), flush=True)
            if curr_score > best_score:
                best_score = curr_score
                best_trees = self.treeTopoList
                best_params = self.params
            if nni_iter % chkpt_freq == 0 and checkpoint_file is not None:
                with open(checkpoint_file, "a") as fout:
                    fout.write(f"NNI Iteration: {nni_iter}\n")
                    fout.write(f"Current newick tree: {best_trees}\n")
                    fout.write(f"Current negative-llh: {best_score}\n")
                    fout.write(f"Current params: {best_params}\n")
                    fout.write(f"Runtime (s): {stop_time - start_time}\n")
        if verbose:
            print("Best score for this search: " + str(best_score), flush=True)
        return best_trees,best_score,best_params 
    
    def single_nni(self,curr_score,nni_iter,strategy,only_marked=False,verbose=False):
        branches = []
        for tree in self.treeList_obj:
            for node in tree.traverse_preorder():
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
            took,score = self.apply_nni(u,curr_score,nni_iter,strategy)
            n_attempts += 2
        return score,n_attempts,took
    
    def apply_nni(self,u,curr_score,nni_iter,strategy):
        # apply nni [DESTRUCTIVE FUNCTION! Changes tree inside this function.]
        v = u.get_parent()
        for node in v.child_nodes():
            if node != u:
                w = node
                break                
        u_children = u.child_nodes()
        # shuffle the order of the nni moves
        shuffle(u_children)
        score_tree_strategy = deepcopy(strategy)
        score_tree_strategy['fixed_brlen'] = None

        if strategy['local_brlen_opt']:
            for pname in self.params:
                score_tree_strategy['fixed_params'][pname] = self.params[pname]
            free_branches = set(u.child_nodes() + v.child_nodes() + [v])
            fixed_branches_anchors = [[] for _ in range(len(self.treeList_obj))]
            for t,tree in enumerate(self.treeList_obj):
                for node in tree.traverse_postorder():
                    if node.is_leaf():
                        node.anchors = (node.label,node.label)
                    else:
                        C = node.child_nodes()
                        a = C[0].anchors[0]
                        b = C[-1].anchors[0]
                        node.anchors = (a,b)
                    if not node in free_branches:
                        fixed_branches_anchors[t].append(node.anchors)
            fixed_branches = [[] for _ in range(len(self.treeList_obj))]
            for t,treeTopo in enumerate(self.treeTopoList):
                tree = read_tree_newick(treeTopo)
                fixed_branches[t] += find_LCAs(tree,fixed_branches_anchors[t])
            fixed_brlen = [{} for _ in range(len(self.treeList_obj))]
            for t,B in enumerate(fixed_branches):
                for i,node in enumerate(B):
                    fixed_brlen[t][fixed_branches_anchors[t][i]] = node.edge_length
            score_tree_strategy['fixed_brlen'] = fixed_brlen
            score_tree_strategy['compute_cache'] = self.compute_cache

        for u_child in u_children:
            u_child.set_parent(v)
            u.remove_child(u_child)
            v.add_child(u_child)

            w.set_parent(u)
            v.remove_child(w)
            u.add_child(w)

            mySolver = self.solver([tree.newick() for tree in self.treeList_obj],self.data,self.prior,self.params)            
            new_score,status = mySolver.score_tree(strategy=score_tree_strategy)
            
            if status != "optimal" and strategy['local_brlen_opt']: # couldn't optimize, probably due to 'local_brlen_opt'
                print("couldn't optimize, probably due to 'local_brlen_opt'. Remove 'local_brlen_opt' and try again ...")
                score_tree_strategy['fixed_brlen'] = None # remove 'local_brlen_opt' and try again
                mySolver = self.solver([tree.newick() for tree in self.treeList_obj],self.data,self.prior,self.params)            
                new_score,status = mySolver.score_tree(strategy=score_tree_strategy)
            
            if self.accept_proposal(curr_score,new_score,nni_iter): # accept the new tree and params                
                self.update_from_solver(mySolver,collect_cache=True)
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
