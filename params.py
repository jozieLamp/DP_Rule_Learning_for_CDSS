''' PARAMS FILE '''
import math

# GENERAL INPUT PARAMS
popSize = 100  # 8000 #Size of ICU population
#popSize = 40337 #Sepsis size


# PROTOCOL PARAMS
verbose = True
template = None

# MCTS PARAMS
maxQueries = 90 #Maximum number of queries allowed (to define for nonprivate model)
cp = 1/math.sqrt(2) #UCT param to increase or decrease the amount of exploration performed
maxTreeDepth = 17 #Maximum depth of tree
cutoffThresh = 0.001 #Match score cutoff threshold to prune branches

paramPercentile = 85 #Percentile wanted for params - score at or below which (inclusive) x% of the scores in the distribution may be found

# DATA PARAMETERS
dataFilename = "Data/ICU/Best/"
resultsFilename = "Results/ICU_Ruleset_MCTS_Baseline_TEST.csv"
# variables with guess ranges
#NOTE - added time bound as an explicit variable in these

# ICU Dataset
variables = {'LOS': [0.0, 122.0], 'ICU_Pt_Days': [0.0, 120.0], 'Mort': [0.0, 1.0], 'n_evts': [0.0, 5.0],
             'y': [0.0, 1.0], 'tte': [-60, 100], 'death': [0.0, 1.0],
             'direct': [0.0, 1.0], 'MET': [0.0, 1.0], 'Sgy': [0.0, 1.0], 'Glasgow_Coma_Scale_Total': [0, 15.0],
             'O2_Flow': [0.0, 10], 'Resp': [0.0, 50.0], 'SpO2': [80, 100.0], 'SBP': [0.0, 260.0],
             'Pulse': [0.0, 400.0], 'Temp': [30, 50], 'ALBUMIN': [1, 5.0],
             'ALKALINE_PHOSPHATASE': [15, 400], 'ALT_GPT': [6.0, 380], 'AST_GOT': [6.0, 250],
             'BLOOD_UREA_NITROGEN': [1, 120], 'CALCIUM': [2, 15], 'CHLORIDE': [80, 150],
             'CO2': [5.0, 50.0], 'CREATININE': [0, 10.0], 'GLUCOSE': [50.0, 460.0], 'HEMOGLOBIN': [1, 25],
             'LACTIC_ACID': [0, 5], 'MAGNESIUM': [0, 5], 'OXYGEN_SATURATION': [80, 100],
             'PARTIAL_THROMBOPLASTIN_TIME': [20.0, 140.0], 'PCO2': [10, 80], 'PHOSPHORUS': [0, 10],
             'PLATELET_COUNT': [10.0, 700.0], 'POTASSIUM': [1, 10], 'PROTIME_INR': [0, 5.0],
             'SODIUM': [100.0, 200.0], 'TOTAL_BILIRUBIN': [0, 10.0], 'TOTAL_PROTEIN': [2, 10],
             'TROPONIN_I': [0.02, 23.5], 'WHITE_BLOOD_CELL_COUNT': [0.12, 26.0], 'hr': [30.0, 300.0],
             's2_hr': [-1, 1], 's8_hr': [-1, 1], 's24_hr': [-1, 1], 'n_edrk': [0.0, 1.0],
             'edrk': [2, 55], 's2_edrk': [-1, 1], 's8_edrk': [-1, 1], 's24_edrk': [-1, 1], 'srr': [0, 1],
             'dfa': [-1, 5], 'cosen': [-5, 1], 'lds': [0.0, 5], 'af': [0.0, 1.0], 'AF': [0.0, 1.0], 'timeBound':[0.0, 1.0]}

# #Sepsis Dataset
# variables = {'HR': [0.0, 280.0], 'O2Sat': [0.0, 100.0], 'Temp': [0.0, 50.0], 'SBP': [0.0, 300.0], 'MAP': [0.0, 300.0],
#  'DBP': [0.0, 300.0], 'Resp': [0.0, 100.0], 'EtCO2': [0.0, 100.0], 'BaseExcess': [-32.0, 100.0], 'HCO3': [0.0, 55.0],
#  'FiO2': [-50.0, 4000.0], 'pH': [0.0, 7.93], 'PaCO2': [0.0, 100.0], 'SaO2': [0.0, 100.0], 'AST': [0.0, 9961.0],
#  'BUN': [0.0, 268.0], 'Alkalinephos': [0.0, 3833.0], 'Calcium': [0.0, 27.9], 'Chloride': [0.0, 145.0], 'Creatinine': [0.0, 46.6],
#  'Bilirubin_direct': [0.0, 37.5], 'Glucose': [0.0, 988.0], 'Lactate': [0.0, 31.0], 'Magnesium': [0.0, 9.8], 'Phosphate': [0.0, 18.8],
#  'Potassium': [0.0, 27.5], 'Bilirubin_total': [0.0, 49.6], 'TroponinI': [0.0, 440.0], 'Hct': [0.0, 71.7], 'Hgb': [0.0, 32.0],
#  'PTT': [0.0, 250.0], 'WBC': [0.0, 440.0], 'Fibrinogen': [0.0, 1760.0], 'Platelets': [0.0, 2322.0], 'SepsisLabel': [0, 1], 'timeBound':[0.0, 1.0]}



# PRIVACY BUDGET PARAMS
epsilon = 'inf' #set epsilon to 'inf' to run nonprivate model
