#! /usr/bin/env python

def write_sequences(char_mtrx,nsites,outFile,delimiter=","):
    with open(outFile,'w') as fout:
        # header
        fout.write("cell")
        for i in range(nsites):
            fout.write(delimiter+"r" + str(i+1))
        fout.write("\n")
        # actual data
        for cell in char_mtrx:
            fout.write(cell)
            for x in char_mtrx[cell]:
                fout.write(delimiter+str(x))
            fout.write("\n")

def read_sequences(inFile,filetype="charMtrx",delimiter=",",masked_symbol="-"):
    with open(inFile,'r') as fin:
        if filetype == "fasta":
            return read_fasta(fin)
        elif filetype == "charMtrx":
            return read_charMtrx(fin,delimiter=delimiter,masked_symbol=masked_symbol)

def read_fasta(fin):    
    S = [] # will be a list of dictionaries
    D = {}
    for line in fin:
        if line.startswith(">"):
            name = line.strip()[1:]
        elif line.startswith("_"):
            S.append(D)
            D = {}
        else:
            seq = [int(x) for x in line.strip().split("|")]
            D[name] = seq       
    return S

def read_charMtrx(fin,delimiter=",",masked_symbol="-"):    
    D = {}
    site_names = fin.readline().strip().split()[1:]
    for line in fin:
        line_split = line.strip().split(delimiter)
        name = line_split[0]
        seq = [int(x) if x != masked_symbol else "?" for x in line_split[1:]]
        D[name] = seq
    return D,site_names    

def read_Q(inFile):
    with open(inFile,'r') as fin:
        fin.readline() # skip the header
        Q = {}
        for line in fin:
            char,state,prob = line.strip().split(',')
            if not char in Q:
                Q[char] = {int(state):float(prob)}
            else:
                Q[char][int(state)] = float(prob)
    return [Q[q] for q in sorted(Q)]

from treeswift import *

def extract_brlens(tfile, ofile):

    t = read_newick_tree(tfile)
    t.root.h = 1

    with open(ofile, "w+") as w:
        for nidx, node in enumerate(t.traverse_preorder()):
            if not node.is_root():
                node.h = node.parent.h + 1
                s = nidx + " " + str(node.h) + " " + str(node.edge_length)
                w.write(s)

