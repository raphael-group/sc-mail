#! /usr/bin/env python
import os
import pickle
import problin_libs as problin
from problin_libs.sequence_lib import read_sequences
from problin_libs.ML_solver import ML_solver
from problin_libs.EM_solver import EM_solver
from scripts.compute_pars_score import pars_score
from treeswift import *
from sys import argv
import random
import argparse
from sys import argv,exit,stdout
import problin_libs as problin



def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-t","--topology",required=True,help="Binary input tree topology in newick format. Branch lengths will be ignored.") 
    parser.add_argument("-c","--characters",required=True,help="The input character matrix. Must have header.")
    parser.add_argument("-r","--rep",required=False,help="The rep index of the input character matrix.") 
    parser.add_argument("--noSilence",action='store_true',help="Assume there is no gene silencing, but allow missing data by dropout in sc-sequencing.")
    parser.add_argument("--noDropout",action='store_true',help="Assume there is no sc-sequencing dropout, but allow missing data by gene silencing.")
    parser.add_argument("-p","--priors",required=False, default="uniform", help="The input prior matrix Q. Default: if not specified, use a uniform prior.")
    parser.add_argument("--solver",required=False,default="Generic",help="Specify a solver. Options are 'Generic' or 'EM'. Caution: at current stage, EM only works with flag --noSilence. Default: 'Generic'")
    parser.add_argument("--delimiter",required=False,default="tab",help="The delimiter of the input character matrix. Can be one of {'comma','tab','whitespace'} .Default: 'tab'.")
    parser.add_argument("--nInitials",type=int,required=False,default=20,help="The number of initial points. Default: 20.")
    parser.add_argument("--randseeds",required=False,help="Random seeds. Can be a single interger number or a list of intergers whose length is equal to the number of initial points (see --nInitials).")
    parser.add_argument("-m","--maskedchar",required=False,default="-",help="Masked character. Default: if not specified, assumes '-'.")
    parser.add_argument("-o","--output",required=True,help="The output file.")
    parser.add_argument("-od","--outputdir",required=False,default="./", help="The output directory.")
    parser.add_argument("-v","--verbose",required=False,action='store_true',help="Show verbose messages.")
    parser.add_argument("--topology_search",action='store_true', required=False,help="Perform topology search using NNI operations.")
    parser.add_argument("--strategy", required=False, help="Strategy for NNI topology search.")
    parser.add_argument("--randomreps", required=False, default=5, type=int, help="Number of replicates to run for the random strategy of topology search.")
    parser.add_argument("--conv", "--convergence", required=False, default=0.2, type=float, help="The threshold parameter to define whether the nni search has converged. Translates to percentage of branches we assume are bad. Default is 0.2.")

    if len(argv) == 1:
        parser.print_help()
        exit(0)
    
    print("Launching " + problin.PROGRAM_NAME + " version " + problin.PROGRAM_VERSION)
    print(problin.PROGRAM_NAME + " was called as follow: " + " ".join(argv))
    
    args = vars(parser.parse_args())

    try:
        if args['outputdir'] != '.' and not os.path.isdir(args['outputdir']):
            os.mkdir(args['outputdir'])
    except:
        print("Could not create specified output directory.")

    delim_map = {'tab':'\t','comma':',','whitespace':' '}
    delimiter = delim_map[args["delimiter"]]
    msa, site_names = read_sequences(args["characters"],filetype="charMtrx",delimiter=delimiter,masked_symbol=args["maskedchar"])
    prefix = '.'.join(args["output"].split('.')[:-1])

    if args["rep"]:
        print("Using rep:", args["rep"])
        msa = msa[int(args["rep"])]
    with open(args["topology"],'r') as f:
        treeStr = f.read().strip()
        tree = read_tree_newick(treeStr)
        if len(tree.root.child_nodes()) != 2:
            print("Provided topology's root does not have two nodes, resetting root.")
            treeStr = tree.newick()[1:-2] + ";"

        tree = read_tree_newick(treeStr)
        keybranches = []
        containsPolytomies = False
        
        i = 0
        nlabel = "nlabel_"
        for node in tree.traverse_levelorder():
            if not node.is_leaf():
                if node.label == None:
                    node.label = nlabel + str(i)
                    i += 1
                if len(node.child_nodes()) != 2:
                    containsPolytomies = True
                    node.resolve_polytomies()
                    for x in node.child_nodes():
                        if not x.is_leaf():
                            if x.label == None:
                                x.label = nlabel + str(i)
                                i += 1
                            keybranches.append(x.label)
        if containsPolytomies:
            print("Detected polytomies in the provided topology. Randomly resolving these polytomies and prioritizing these branches for topology search if enabled.")
            outfile = args["outputdir"] + prefix +  ".resolvedtree"
            tree.write_tree_newick(outfile)
        treeStr = tree.newick()

        tree = read_tree_newick(treeStr)
        keybranches = []
        containsPolytomies = False
        # if there are polytomies, randomly resolve them
        i = 0
        nlabel = "nlabel_"
        for node in tree.traverse_levelorder():
            if not node.is_leaf():
                #print(node.label)
                if node.label == None:
                    node.label = nlabel + str(i)
                    i += 1
                    #print(None, "reset to", node.label)
                if len(node.child_nodes()) != 2:
                    containsPolytomies = True
                    node.resolve_polytomies()
                    for x in node.child_nodes():
                        if not x.is_leaf():
                            if x.label == None:
                                x.label = nlabel + str(i)
                                i += 1
                            keybranches.append(x.label)
        if containsPolytomies:
            print("Detected polytomies in the provided topology. Randomly resolving these polytomies and prioritizing these branches for topology search if enabled.")
            outfile = args["outputdir"] + prefix +  ".resolvedtree"
            tree.write_tree_newick(outfile)
        treeStr = tree.newick()

    k = len(msa[next(iter(msa.keys()))])
    fixed_phi = 0 if args["noDropout"] else None
    fixed_nu = 0 if args["noSilence"] else None

    if args["randseeds"] is None:
        random_seeds = None
    else:
        random_seeds = [int(x) for x in args["randseeds"].strip().split()]
        if args["nInitials"] != 1 and len(random_seeds) == 1:
            random_seeds = random_seeds[0]

    if args["priors"] == "uniform":
        print("No prior file detected, using uniform prior probabilities for each alphabet on each site.")
        # use the uniform Q matrix
        Q = []
        for i in range(k):
            M_i = set(msa[x][i] for x in msa if msa[x][i] not in [0,"?"])
            m_i = len(M_i)
            q = {x:1/m_i for x in M_i}
            q[0] = 0
            Q.append(q)
    else:
        # read in the Q matrix
        file_extension = args["priors"].strip().split(".")[-1]
        if file_extension == "pkl": # pickled file
            infile = open(args["priors"], "rb")
            priors = pickle.load(infile)
            infile.close()
            Q = []
            priorkeys = sorted(priors.keys())
            if priorkeys != sorted([int(x[1:]) for x in site_names]):
                print("Prior keys mismatch with site names.")
                print("Prior keys:", priorkeys)
                print("Site names:", site_names)

            for i in sorted(priors.keys()):
                q = {int(x):priors[i][x] for x in priors[i]}
                q[0] = 0
                Q.append(q)
        elif file_extension == "csv":
            Q = [{0:0} for i in range(k)]
            seen_sites = set()
            with open(args["priors"],'r') as fin:
                lines = fin.readlines()
                for line in lines[1:]:
                    site_idx,char_state,prob = line.strip().split(',')
                    site_idx = int(site_idx[1:])
                    if site_idx not in seen_sites:
                        seen_sites.add(site_idx)
                    char_state = int(char_state)
                    prob = float(prob)
                    Q[len(seen_sites) - 1][char_state] = prob
            
        else:
            Q = [{0:0} for i in range(k)]
            with open(args["priors"],'r') as fin:
                for line in fin:
                    site_idx,char_state,prob = line.strip().split()
                    site_idx = int(site_idx)
                    char_state = int(char_state)
                    prob = float(prob)
                    Q[site_idx][char_state] = prob

    selected_solver = ML_solver
    em_selected = False
    if args["solver"].lower() == "em": 
        selected_solver = EM_solver   
        em_selected = True
    if em_selected:
        print("Optimization by EM algorithm") 
    else:    
        print("Optimization by Generic solver")        
      
    def record_statistics(params, fout, optimal_llh):
        #fout.write("Optimal topology: " + params.tree.newick() + "\n")
        fout.write("Newick tree: " +  params.tree.newick() + "\n")
        fout.write("Parsimony Score: " + str(pars_score(params.tree, args["characters"], args["maskedchar"], False, "")) + "\n")
        fout.write("Normalized Parsimony Score: " + str(pars_score(params.tree, args["characters"], args["maskedchar"], True, "")) + "\n")
        #fout.write("Weighted Parsimony Score: " + str(pars_score(params.tree, args["characters"], args["maskedchar"], False, args["priors"])) + "\n")
        fout.write("Optimal negative-llh: " +  str(optimal_llh) + "\n")
        fout.write("Optimal dropout rate: " + str(mySolver.params.phi) + "\n")
        fout.write("Optimal silencing rate: " + str(mySolver.params.nu) + "\n")
        
    mySolver = selected_solver(msa,Q,treeStr)
    optimal_llh = mySolver.optimize(initials=args["nInitials"],fixed_phi=fixed_phi,fixed_nu=fixed_nu,verbose=args["verbose"],random_seeds=random_seeds)
    outfile = args["outputdir"] + "/" + args["output"]
    if args["topology_search"]:
        if containsPolytomies:
            # resolve that tree first
            mySolver.topology_search(maxiter=1000, verbose=True, prefix=prefix, trynextbranch=True, strategy=args["strategy"], keybranches=keybranches, nreps=args['randomreps'], outdir=args['outputdir'], conv=args['conv'])
            optimal_llh = mySolver.optimize(initials=args["nInitials"],fixed_phi=fixed_phi,fixed_nu=fixed_nu,verbose=args["verbose"],random_seeds=random_seeds)
            print("Finished resolving polytomy tree.")
            if args["verbose"]:
                print("Polytomy-resolved tree: ", params.tree.newick() + "\n")
            # record the starting tree statistics
            with open(outfile,'w') as fout:
                fout.write("Optimal polytomy-resolved tree:\n")
                record_statistics(mySolver.params, fout, optimal_llh)
        # run topology search
        mySolver.topology_search(maxiter=1000, verbose=True, prefix=prefix, trynextbranch=True, strategy=args["strategy"], keybranches=[], nreps=args['randomreps'], outdir=args['outputdir'], conv=args['conv'])
        optimal_llh = mySolver.optimize(initials=args["nInitials"],fixed_phi=fixed_phi,fixed_nu=fixed_nu,verbose=args["verbose"],random_seeds=random_seeds)
    
    with open(outfile,'a') as fout:
        fout.write("Final optimal tree:\n")
        record_statistics(mySolver.params, fout, optimal_llh)

if __name__ == "__main__":
    main()