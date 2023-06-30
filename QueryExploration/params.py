''' PARAMS FILE '''
import math

# GENERAL INPUT PARAMS
popSize = 10  # 8000 #Size of ICU population
#popSize = 40337 #Sepsis size


# PROTOCOL PARAMS
verbose = True
paramPercentile = 85 #Percentile wanted for params - score at or below which (inclusive) x% of the scores in the distribution may be found


# MCTS PARAMS
mctsType = 'baseline' #baseline' #'baseline' #options are 'baseline', 'coverage'
maxQueries = 850 #Maximum number of server queries allowed (to define for nonprivate model)
cp = 1/math.sqrt(2) #UCT param to increase or decrease the amount of exploration performed
maxTreeDepth = 25 #Maximum depth of tree
cutoffThresh = 0.01 #Match score cutoff threshold to prune branches


# DATA PARAMETERS
dataFilename = "../Data/Synthetic/"
# dataFilename = "Data/ICU/Test/"
# dataFilename = "Data/Sepsis/Best/"


resultsFilename = "../QueryExploration/Results/QE_Test"


# time bounds
timeBounds = [0.0, 2.0]

# variables with guess ranges
# Synth Test Dataset
variables = {'ft_a': [0.0, 500.0],  'ft_b': [0.0, 500.0], 'ft_c': [0.0, 500.0], 'ft_d': [0.0, 500.0], 'ft_e': [0.0, 500.0]}


# PRIVACY BUDGET PARAMS
epsilon = 'inf' #set epsilon to 'inf' to run nonprivate model
budgetAllocMethod = 'fixed' #Options are 'fixed': epsilon/total queries, 'adaptive'


# cp = epsilon / maxQueries #UCT param to increase or decrease the amount of exploration performed
