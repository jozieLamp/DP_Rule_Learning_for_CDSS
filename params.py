''' PARAMS FILE '''
import math

# GENERAL INPUT PARAMS
popSize = 100
# 8000 #Size of ICU population
#popSize = 40336 #Sepsis size
#popSize = 34013 #T1d size

# PROTOCOL PARAMS
verbose = False
paramPercentile = 85 #Percentile wanted for params - score at or below which (inclusive) x% of the scores in the distribution may be found


# MCTS PARAMS
mctsType = 'baseline' #options are 'baseline', 'coverage'
cp = 1/math.sqrt(2) #UCT param to increase or decrease the amount of exploration performed
maxTreeDepth = 25 #Maximum depth of tree
cutoffThresh = 0.01 #0.0001 #0.01 #V, Match score cutoff threshold to prune branches- was 0.001

# PRIVACY BUDGET PARAMS
epsilon = 1 #set epsilon to 'inf' to run nonprivate model
budgetAllocMethod = 'adaptive' #Options are 'fixed': epsilon/total queries, 'adaptive'
useActiveClients = False # whether to use active clients or not
maxQueries = 5000 #1000 #Maximum number of server queries allowed (to define for nonprivate + baseline model)
# cp = epsilon / maxQueries #UCT param to increase or decrease the amount of exploration performed
theta = 0.5 # acceptable error probability, e.g., 5%

# DATA PARAMETERS
dataFilename = "Data/ICU/Best/"
# dataFilename = "Data/Sepsis/Best/"

# resultsFilename = "Results/ICU_Ruleset_MCTS_Baseline_1000pop_500iters"
# resultsFilename = "Results/ICU/Baseline_1000Q_V1/"
# resultsFilename = "Results/ICU/Baseline_5000Q_V1/"

resultsFilename = "Results/ICU/Adaptive/Queries/"
# resultsFilename = "Results/Sepsis/Baseline_1000Q_V1/"
# resultsFilename = "Results/ICU/Baseline_5000Q_V1/"
# resultsFilename = "Results/TEST/ICU_Base_PRIV"
# resultsFilename = "Results/Sepsis_Base_TEST"
# resultsFilename = "Results/Sepsis_Base_PRIV"

# resultsFilename = "Results/ICU_Ruleset_MCTS_TEST"
# resultsFilename = "Results/Sepsis_Ruleset_MCTS_TEST"


# time bounds
timeBounds = [0.0, 1.0]

# variables with guess ranges
# ICU TESTER Dataset
# variables = {'Pulse': [0.0, 400.0],  'hr': [30.0, 300.0], 'Mort': [0.0, 1.0], 'AF': [0.0, 1.0], 'n_evts': [0.0, 5.0], 'tte': [-60, 100], 'death': [0.0, 1.0]}

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
             'dfa': [-1, 5], 'cosen': [-5, 1], 'lds': [0.0, 5], 'af': [0.0, 1.0], 'AF': [0.0, 1.0]}

# #Sepsis Dataset
# variables = {'HR': [0.0, 280.0], 'O2Sat': [0.0, 100.0], 'Temp': [0.0, 50.0], 'SBP': [0.0, 300.0], 'MAP': [0.0, 300.0],
#  'DBP': [0.0, 300.0], 'Resp': [0.0, 100.0], 'EtCO2': [0.0, 100.0], 'BaseExcess': [-32.0, 100.0], 'HCO3': [0.0, 55.0],
#  'FiO2': [-50.0, 4000.0], 'pH': [0.0, 7.93], 'PaCO2': [0.0, 100.0], 'SaO2': [0.0, 100.0], 'AST': [0.0, 9961.0],
#  'BUN': [0.0, 268.0], 'Alkalinephos': [0.0, 3833.0], 'Calcium': [0.0, 27.9], 'Chloride': [0.0, 145.0], 'Creatinine': [0.0, 46.6],
#  'Bilirubin_direct': [0.0, 37.5], 'Glucose': [0.0, 988.0], 'Lactate': [0.0, 31.0], 'Magnesium': [0.0, 9.8], 'Phosphate': [0.0, 18.8],
#  'Potassium': [0.0, 27.5], 'Bilirubin_total': [0.0, 49.6], 'TroponinI': [0.0, 440.0], 'Hct': [0.0, 71.7], 'Hgb': [0.0, 32.0],
#  'PTT': [0.0, 250.0], 'WBC': [0.0, 440.0], 'Fibrinogen': [0.0, 1760.0], 'Platelets': [0.0, 2322.0], 'SepsisLabel': [0, 1]}

# # T1D Dataset
# variables = {'Pt_CGMUseNumDays': [0.0, 30.0], 'Pt_FatherT1D': [0.0, 1.0], 'Pt_MotherT1D': [0.0, 1.0], 'Pt_SiblingT1D': [0.0, 1.0], 'Pt_ChildT1D': [0.0, 1.0],
#  'Pt_GrandchildT1D': [0.0, 1.0],'Pt_GrandparentT1D': [0.0, 1.0],'BldPrSys': [0.0, 300.0],'BldPrDia': [0.0, 160.0],'SMBGperDayPtMeterCombo': [0.0, 30.0],
#  'WeightKg': [0.0, 242.0],'HeightCm': [0.0, 210.0],'DirectLDL': [0.0, 1.0],'age': [0, 90],'diabDur': [0.0, 83.0],'TotalDailyInsPerKg': [0.0, 12.0],
#  'LDL': [0.0, 400.0],'HDL': [0.0, 200.0],'TotChol': [0.0, 632.0],'Triglyc': [0.0, 3000.0],'BUN': [0.0, 230.0],'AlbCreatRat_mggNew': [-0.1, 9679.0],
#  'UnitsInsBasalOrLongAct': [0.0, 200.0],'BGTestAvgNumMeter': [0.0, 30.0],'BGTestAvgNumPtRep': [0.0, 30.0],'TSH': [0.0, 493.0],'HbA1c': [0.0, 20.0],
#  'AutonomicNeuroCl': [0.0, 1.0],'Pt_InsGov': [0.0, 1.0],'NumPumpBolusOrShortAct': [0.0, 50.0],'HbA1cImputeDtMnC': [-83.0, 92.0],
#  'Pt_SHFlg': [0.0, 1.0],'Pt_DKAFlg': [0.0, 1.0],'bmi': [0.0, 112.0],'bmiPerc': [0.0, 1.0],'bmiZscore': [-32.0, 30],
#  'GFR': [0.0, 424.0],'diagAgeCombo': [0.0, 89.0],'Pt_A1cGoalLev': [0.0, 12.0],'Pt_A1cGoalLevelDsYr5': [0.0, 12.0]}





