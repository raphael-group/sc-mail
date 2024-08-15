from .Base_model import *
from math import *

DEFAULT_max_mu = 10
DEFAULT_max_nu = 10

class PMM_model(Count_base_model):
    # PMM = probabilistic mixed-type missing
    def __init__(self,treeList,data,prior,**params):
    # **params must have 'mu', 'nu', 'phi'
        params = Param(['mu','nu','phi'],[params['mu'],params['nu'],params['phi']],[0,0,0,0,0],[DEFAULT_max_mu,DEFAULT_max_nu,1,1,1])
        super(PMM_model,self).__init__(treeList,data,prior,params)
    
    def Psi(self,c_node,k,j,alpha,beta):
        # Layer 1 transition probabilities  
        # override the Base_model class
        #print("alpha:", alpha, "beta:", beta)
        delta = c_node.edge_length
        nu = self.params.get_value('nu')
        if alpha == 0:
            if beta == 0:
                p = exp(-delta*(1+nu))
            elif beta == -1:
                p = 1-exp(-delta*nu)
            else:
                q = self.Q[k][j][beta]
                p = q*exp(-delta*nu)*(1-exp(-delta))   
        else:
            if alpha == -1 and beta == -1:
                p = 1
            elif alpha == beta:
                p = exp(-delta*nu)
            elif beta == -1:
                p = 1-exp(-delta*nu)
            else:
                p = 0        
        #print("PMM_model Psi", p)
        return p

    def Gamma(self,k,x,c):
        # Layer 2 transition probabilities  
        # override the Base_model class
        # x is a cassette state of length J corresponding to cassette k
        J = self.data['alleleTable'].J
        x_is_silenced = (x == tuple([-1]*J))
        phi = self.params.get_value('phi')
        max_count = 0
        for y in c:
            if c[y] > max_count:
                max_count = c[y]
        if max_count == 0: # all counts in c are 0, dropout
            p = 1 if x_is_silenced else phi
        else:
            p = 1-phi if (c[x] == max_count and not x_is_silenced) else 0
        return p


