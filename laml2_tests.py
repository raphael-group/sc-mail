#! /usr/bin/env python
#from laml_unit_tests.Count_model.unit_tests_PMMN_in_llh import *
#from laml_unit_tests.Count_model.unit_tests_PMMN_out_llh import *
#from laml_unit_tests.Count_model.unit_tests_PMMN_posterior import *
#from laml_unit_tests.Count_model.unit_tests_PMMN_scipy_opt import *
#from laml_unit_tests.Count_model.unit_tests_PMMN_EM_opt import *
#from laml_unit_tests.Count_model.unit_tests_PMMN_TopoSearch import *
#from laml_unit_tests.Count_model.unit_tests_PMMN_TopoSearch_parallel import *

#from laml_unit_tests.Count_model.unit_tests_PMMC_in_llh import *
#from laml_unit_tests.Count_model.unit_tests_PMMC_out_llh import *
#from laml_unit_tests.Count_model.unit_tests_PMMC_posterior import *
#from laml_unit_tests.Count_model.unit_tests_PMMC_scipy_opt import *
#from laml_unit_tests.Count_model.unit_tests_PMMC_EM_opt import *
#from laml_unit_tests.Count_model.unit_tests_PMMC_TopoSearch import *

from laml_unit_tests.IO_handler.unit_tests_proc_data import *
import sys
import os

if __name__ == '__main__':
    sys.path.append(os.path.dirname(__file__))
    sys.path.append(os.path.join(os.path.dirname(__file__), 'helpers'))
    print("Running tests for LAML2...")
    unittest.main()
