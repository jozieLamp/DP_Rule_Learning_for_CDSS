from SignalTemporalLogic.STLFactory import STLFactory
import matplotlib.pyplot as plt
plt.rc('font', size=12)
import copy
import pandas as pd
import seaborn as sns
import numpy as np
from collections import Counter
import operator
import warnings
import treelib
import re
from Client import Client
from Server import Server


# Qualitative → predictive quality of binary outcome(s)
# Using majority vote from each rule, for each patient, kind of like ensemble machine learning
# Calculate Sensitivity, Specificity, Precision, Accuracy and MCR

# This is piece by piece for each patient's data -->
# return confusion matrix summary across all patients
def getSummaryConfusionMatrix(dt, dataLabels, ruleDF, method='AVG'):
    classes = ruleDF['Class']

    totalSlices = len(dt) / 2

    mcrList = []

    TP = 0
    TN = 0
    FP = 0
    FN = 0


    # sort ldpdf by accuracy
    ruleDF = ruleDF.sort_values(by='BalancedAccuracy', ascending=False)

    labelCount = 0
    for i in range(0, len(dt), 2):
        data = dt.iloc[i:i + 2]  # get rows of 2
        label = dataLabels.loc[labelCount].values[0]
        labelCount += 1

        # get majority vote of predicted binary outcome from weighted rules
        mv = majorityVote(data, ruleDF, label, classes, method)

        if label == 1 and mv == True:
            TP += 1
        elif label == -1 and mv == False:
            TN += 1
        elif label == 1 and mv == False:
            FN += 1
        else:  # label == -1 and val == True
            FP += 1

    actualNo = TN + FP
    actualYes = FN + TP
    predictedNo = TN + FN
    predictedYes = TP + FP
    TPR = TP / actualYes if actualYes else 0
    FPR = FP / actualNo if actualNo else 0
    TNR = TN / actualNo if actualNo else 0
    prec = TP / predictedYes if predictedYes else 0
    accuracy = (TP + TN) / totalSlices
    MCR = 1 - accuracy
    bottom = prec + TPR
    F1 = 2 * (prec * TPR) / bottom if bottom else 0  # harmonic mean of sens and precision
    balancedAccuracy = (TPR + TNR) / 2  # (sens + spec) / 2

    mcrList.append(
        [TP, TN, FP, FN, actualYes, actualNo, predictedYes, predictedNo, TPR, TNR, FPR, prec, F1, accuracy, MCR,
         balancedAccuracy])

    mcrDF = pd.DataFrame(mcrList, columns=['TP', 'TN', 'FP', 'FN', 'Actual Yes', 'Actual No', 'Predicted Yes',
                                           'Predicted No', 'TPR/Sens', 'TNR/Spec', 'FPR', 'Precision', 'F1', 'Accuracy',
                                           'MCR', 'BalancedAccuracy'])
    # mcrDF = mcrDF.sort_values(by='Accuracy', ascending=False)

    return mcrDF


# return confusion matrix patient by patient
def getPatientConfusionMatrix(fullData, dataLabels, ruleDF, method='AVG'):
    classes = ruleDF['Class']

    mcrList = []

    for id in sorted(set(fullData.index)):
        dt = fullData.loc[id]

        totalSlices = len(dt) / 2

        TP = 0
        TN = 0
        FP = 0
        FN = 0

        labelCount = 0
        for i in range(0, len(dt), 2):
            data = dt.iloc[i:i + 2]  # get rows of 2
            label = dataLabels.loc[labelCount].values[0]
            labelCount += 1

            # get majority vote of predicted binary outcome from all rules
            mv = majorityVote(data, ruleDF, label, classes, method)

            if label == 1 and mv == True:
                TP += 1
            elif label == -1 and mv == False:
                TN += 1
            elif label == 1 and mv == False:
                FN += 1
            else:  # label == -1 and val == True
                FP += 1

        actualNo = TN + FP
        actualYes = FN + TP
        predictedNo = TN + FN
        predictedYes = TP + FP
        TPR = TP / actualYes if actualYes else 0
        FPR = FP / actualNo if actualNo else 0
        TNR = TN / actualNo if actualNo else 0
        prec = TP / predictedYes if predictedYes else 0
        accuracy = (TP + TN) / totalSlices
        MCR = 1 - accuracy
        bottom = prec + TPR
        F1 = 2 * (prec * TPR) / bottom if bottom else 0  # harmonic mean of sens and precision
        balancedAccuracy = (TPR + TNR) / 2  # (sens + spec) / 2

        mcrList.append(
            [TP, TN, FP, FN, actualYes, actualNo, predictedYes, predictedNo, TPR, TNR, FPR, prec, F1, accuracy, MCR,
             balancedAccuracy])

    # average results from each slice
    finalList = [list(map(lambda x: sum(x) / len(x), zip(*mcrList)))]

    mcrDF = pd.DataFrame(finalList, columns=['TP', 'TN', 'FP', 'FN', 'Actual Yes', 'Actual No', 'Predicted Yes',
                                             'Predicted No', 'TPR/Sens', 'TNR/Spec', 'FPR', 'Precision', 'F1',
                                             'Accuracy',
                                             'MCR', 'BalancedAccuracy'])
    # mcrDF = mcrDF.sort_values(by='Accuracy', ascending=False)

    return mcrDF


# Can choose method of average weights, top rules or majority voting
def majorityVote(dtSlice, ruleDF, label, classes, method='AVG'):
    factory = STLFactory()

    ruleSet = ruleDF['Rule']
    votes = []

    # get predictions for each rule, sorted in order of most acc --> least acc
    for r in range(len(ruleSet)):
        ruleClass = classes[r]
        ft = factory.constructFormulaTree(ruleSet[r])
        val = ft.evaluateTruthValue(dtSlice)

        if label == 1:
            if ruleClass == "Positive":
                if val == True:
                    votes.append(1)
                else:
                    votes.append(-1)
            else:  # ruleClass == "Negative"
                if val == True:
                    votes.append(-1)
                else:
                    votes.append(1)
        else:  # label == -1
            if ruleClass == "Negative":
                if val == True:
                    votes.append(-1)
                else:
                    votes.append(1)
            else:  # ruleClass == "Positive"
                if val == True:
                    votes.append(1)
                else:
                    votes.append(-1)

    weights = ruleDF['BalancedAccuracy'].tolist()

    if method == "AVG":
        # multiply votes by weight
        for v in range(len(votes)):
            votes[v] = votes[v] * weights[v]

        avg = np.mean(votes)

        if avg > 0:
            return True
        else:
            return False

    elif method == "TOP":  # use top rules
        finalVotes = []
        count = 0
        wt = weights[count]

        while wt > 0.6:
            finalVotes.append(votes[count] * wt)

            count += 1
            wt = weights[count]

        if finalVotes == []:
            finalVotes.append(votes[0] * wt)  # just append top 1 rule

        avg = np.mean(votes)

        if avg > 0:
            return True
        else:
            return False

    else:  # method == "MAJORITY":
        lst = Counter(votes)
        res = lst.most_common(1)[0][0]

        if res == 1:
            return True
        else:
            return False

#Get MCR on data for each individual rule in ruleset
def getRulesetMCR(rules, data, labels):
    # Get MCR of Std
    mcrPosDF, slices = getMCRPosOutcome(rules, data, labels)
    # mcrPosDF.to_csv("MCR_Pos.csv")
    mcrNegDF, slices = getMCRNegOutcome(rules, data, labels)
    # mcrNegDF.to_csv("MCR_Neg.csv")

    classes = []
    mcrDF = pd.DataFrame(columns=['Rule',
                                   'TP', 'TN', 'FP', 'FN', 'Actual Yes', 'Actual No', 'Predicted Yes',
                                   'Predicted No',
                                   'TPR/Sens', 'TNR/Spec', 'FPR', 'Precision', 'F1', 'Accuracy', 'MCR',
                                   'BalancedAccuracy'])

    for i in range(len(mcrPosDF)):
        pos = mcrPosDF.iloc[i]
        neg = mcrNegDF.iloc[i]

        if pos['Accuracy'] > neg['Accuracy']:
            mcrDF = mcrDF.append(pos)
            classes.append("Positive")
        else:
            mcrDF = mcrDF.append(neg)
            classes.append("Negative")

    mcrDF["Class"] = classes #add the class this rule is predicting

    # Sort alphabetically by rule
    # mcrDF = mcrDF.sort_values(by='Rule')
    # mcrDF = mcrDF.reset_index(drop=True)

    return mcrDF


def getMCRPosOutcome(posRules, dt, dataLabels):
    factory = STLFactory()
    totalSlices = len(dt) / 2

    mcrList = []
    for p in posRules:
        ft = factory.constructFormulaTree(p)

        TP = 0
        TN = 0
        FP = 0
        FN = 0

        labelCount = 0
        for i in range(0, len(dt), 2):
            data = dt.iloc[i:i + 2]  # get rows of 2
            label = dataLabels.loc[labelCount].values[0]
            labelCount += 1

            val = ft.evaluateTruthValue(data)

            if label == 1 and val == True:
                TP += 1
            elif label == -1 and val == False:
                TN += 1
            elif label == 1 and val == False:
                FN += 1
            else:  # label == -1 and val == True
                FP += 1

        actualNo = TN + FP
        actualYes = FN + TP
        predictedNo = TN + FN
        predictedYes = TP + FP
        TPR = TP / actualYes if actualYes else 0
        FPR = FP / actualNo if actualNo else 0
        TNR = TN / actualNo if actualNo else 0
        prec = TP / predictedYes if predictedYes else 0
        accuracy = (TP + TN) / totalSlices
        MCR = 1 - accuracy
        bottom = prec + TPR
        F1 = 2 * (prec * TPR) / bottom if bottom else 0  # harmonic mean of sens and precision
        balancedAccuracy = (TPR + TNR) / 2  # (sens + spec) / 2

        mcrList.append(
            [p, TP, TN, FP, FN, actualYes, actualNo, predictedYes, predictedNo, TPR, TNR, FPR, prec, F1, accuracy, MCR,
             balancedAccuracy])

    mcrDF = pd.DataFrame(mcrList, columns=['Rule',
                                           'TP', 'TN', 'FP', 'FN', 'Actual Yes', 'Actual No', 'Predicted Yes',
                                           'Predicted No', 'TPR/Sens', 'TNR/Spec', 'FPR', 'Precision', 'F1', 'Accuracy',
                                           'MCR', 'BalancedAccuracy'])
    # mcrDF = mcrDF.sort_values(by='Accuracy', ascending=False)

    return mcrDF, totalSlices


def getMCRNegOutcome(negRules, dt, dataLabels):
    factory = STLFactory()
    totalSlices = len(dt) / 2

    mcrList = []
    for p in negRules:
        ft = factory.constructFormulaTree(p)

        TP = 0
        TN = 0
        FP = 0
        FN = 0

        labelCount = 0
        for i in range(0, len(dt), 2):
            data = dt.iloc[i:i + 2]  # get rows of 2
            label = dataLabels.loc[labelCount].values[0]
            labelCount += 1

            val = ft.evaluateTruthValue(data)

            if label == -1 and val == True:
                TN += 1
            elif label == 1 and val == False:
                TP += 1
            elif label == -1 and val == False:
                FP += 1
            else:  # label == 1 and val == True
                FN += 1

        actualNo = TN + FP
        actualYes = FN + TP
        predictedNo = TN + FN
        predictedYes = TP + FP
        TPR = TP / actualYes if actualYes else 0
        FPR = FP / actualNo if actualNo else 0
        TNR = TN / actualNo if actualNo else 0
        prec = TP / predictedYes if predictedYes else 0
        accuracy = (TP + TN) / totalSlices
        MCR = 1 - accuracy
        bottom = prec + TPR
        F1 = 2 * (prec * TPR) / bottom if bottom else 0  # harmonic mean of sens and precision
        balancedAccuracy = (TPR + TNR) / 2  # (sens + spec) / 2

        mcrList.append(
            [p, TP, TN, FP, FN, actualYes, actualNo, predictedYes, predictedNo, TPR, TNR, FPR, prec, F1, accuracy,
             MCR,
             balancedAccuracy])

    mcrDF = pd.DataFrame(mcrList, columns=['Rule',
                                           'TP', 'TN', 'FP', 'FN', 'Actual Yes', 'Actual No', 'Predicted Yes',
                                           'Predicted No', 'TPR/Sens', 'TNR/Spec', 'FPR', 'Precision', 'F1',
                                           'Accuracy',
                                           'MCR', 'BalancedAccuracy'])
    # mcrDF = mcrDF.sort_values(by='Accuracy', ascending=False)

    return mcrDF, totalSlices

def plotQueryAnalysisCM(df, clientCM, save):
    #Plot Rules
    prec = df["Precision"]
    acc = df['Accuracy']
    queries = df["Queries"]

    plt.figure(figsize=(12, 7))
    plt.title("Rule Quality Query Analysis")
    plt.axhline(y=clientCM['Accuracy'].item(), color='r', linestyle='--', label='Client Accuracy')
    plt.axhline(y=clientCM['Precision'].item(), color='b', linestyle='--', label='Client Precision')

    plt.plot(queries, prec, label='Precision')
    plt.plot(queries, acc, label='Accuracy')
    plt.xlabel("Number of Queries")
    plt.ylabel("Number of Rules")
    plt.legend()
    plt.savefig(save + "_RulesetQuality_Query_Analysis")
    plt.show()

def plotQueryAnalysisPatientCM(df, clientCM, save):
    #Plot Rules
    prec = df["Patient Precision"]
    acc = df['Patient Accuracy']
    queries = df["Queries"]

    plt.figure(figsize=(12, 7))
    plt.title("Rule Quality By Patient Query Analysis")
    plt.axhline(y=clientCM['Accuracy'].item(), color='r', linestyle='--', label='Client Accuracy')
    plt.axhline(y=clientCM['Precision'].item(), color='b', linestyle='--', label='Client Precision')

    plt.plot(queries, prec, label='Precision')
    plt.plot(queries, acc, label='Accuracy')
    plt.xlabel("Number of Queries")
    plt.ylabel("Number of Rules")
    plt.legend()
    plt.savefig(save + "_RulesetQuality_Patient_Query_Analysis")
    plt.show()



#Load original raw data from clients as dataframe
def loadClientData(popSize, dataFilename):
    data = pd.DataFrame()
    labels = pd.DataFrame()
    for i in range(1, popSize+1):

        try:
            dt = pd.read_csv(dataFilename + str(i) + 'DataFrame.csv', index_col=0)
            lbls = pd.read_csv(dataFilename + str(i) + 'Labels.csv', index_col=0)

            data = data.append(dt)
            labels = labels.append(lbls)

        except:
            print("Data file not found for Client %d" % (i))

    labels = labels.reset_index()
    return data, labels