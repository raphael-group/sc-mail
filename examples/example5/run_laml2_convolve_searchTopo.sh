#!/bin/bash

python ../../run_laml2.py -c TLS_Bar8.json -t Bar8_newick_noMutationlessEdges_Labeled_resolved.nwk -p priors_Bar8.csv -m -1 --readout_model "PMMC" -o output_s2_convolve_searchTopo -v -s 2 --nInitials 1 --silence_mechanism convolve --topology_search
