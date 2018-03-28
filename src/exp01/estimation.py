from numpy import arange,array,ones,linalg
from pylab import plot,show
import numpy as np
import random
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, AdaBoostClassifier

from exp01.evaluation import generate_fv, get_attr, is_continuous, VALUE_CONTINUOUS, RELN_VALUES

class LinearEstimator:

    # wieght threshhold to drop column
    E = 0.001

    def __init__(self):
        self.variables = []
        self.nranges = []
        self.ynrange = []
        self.weights = []
        self.residuals = []

    def normalize(self, value, position):
        base,scale = self.nranges[position]
        if scale == 0: return 0
        return (value - base) / scale

    def ynormalize(self, value):
        base,scale = self.ynrange
        if scale == 0: return 0
        return (value - base) / scale

    def yunnormalize(self, value):
        base,scale = self.ynrange
        return (value*scale) + base

    def train(self, variables, A, Y):
        """A is an array of feature vectors. Y is a vector of target values."""

        # only keep the continuous values ones
        AV = np.array(A).T

        AVkeep = []
        self.variables = []
        for v,vals in zip(variables,AV):
            if is_continuous(v):
                # suitable for linear regression
                self.variables.append(v)
                AVkeep.append(vals)

        # set up for normalization
        self.nranges = []
        for vals in AVkeep:
            mn = min(vals)
            self.nranges.append((mn, max(vals)-mn))
        mn = min(Y)
        self.ynrange = (mn, max(Y)-mn)

        # normalize for training
        AV = [[self.normalize(v, i) for v in vals] for i,vals in enumerate(AVkeep)]
        AV.append(ones(len(Y)))
        AV = np.array(AV)
        Y = [self.ynormalize(y) for y in Y]

        self.weights, self.residuals = linalg.lstsq(AV.T, Y)[:2]

        # drop variables that don't matter
        temp = []
        delct = 0
        for i,w in enumerate(self.weights[:-1]):
            if w < LinearEstimator.E:
                del self.variables[i-delct]
                del self.nranges[i-delct]
                delct += 1
            else:
                temp.append(w)

        temp.append(self.weights[-1])
        self.weights = temp

    def estimate_from_scenario(self, labeled_entities, world):
        fv = generate_fv(world, labeled_entities, self.variables)
        fv = [fv[vname] if vname in fv else None for vname in self.variables]
        return self.estimate(fv)

    def estimate(self, a):
        yn = self.weights[-1] + sum((w*self.normalize(x,i) for i,(w,x) in enumerate(zip(self.weights[:-1],a))))
        return self.yunnormalize(yn)

    def validate(self, variables, A, Y, fold=10):
        test_step = int(len(A)/fold)
        if test_step == 0: test_step = 1
        #print("test step: ", test_step)
        i = 0
        errors = []
        for j in range(fold):
            train = A[0:i] + A[i+test_step:]
            trainy = Y[0:i] + Y[i+test_step:]
            test = A[i:i+test_step]
            testy = Y[i:i+test_step]

            self.train(variables, train, trainy)

            error = 0
            for tx,ty in zip(test,testy):
                p = self.estimate(filter_values(tx, variables, self.variables))
                error += (p - ty)

            mean_error = error/test_step
            relative_error = mean_error/np.mean(testy)
            errors.append(relative_error)

            #print("Fold {}, error: {} (relative: {})".format(i, mean_error, relative_error))
            #print(self.variables)

            i += test_step

        return np.mean(errors)

def filter_values(fv, variables, model_vars):
    """Only keep the values in fv that correspond to vars in model_vars."""
    V = []
    for v,val in zip(variables,fv):
        if v in model_vars:
            V.append(val)
    return V

class RandomForestEstimator:
    # importance threshhold to drop variable
    E = 0.001

    def __init__(self):
        pass

    def train(self, variables, A, Y):
        """A is an array of feature vectors. Y is a vector of target values."""

        self.clf = RandomForestClassifier()
        self.clf.fit(A, Y)

        # drop variables that don't matter
        A = np.array(A).T
        self.variables = []
        temp = []
        for i,(v,impact) in enumerate(zip(variables,self.clf.feature_importances_)):
            if impact >= RandomForestEstimator.E:
                self.variables.append(v)
                temp.append(A[i])

        if len(self.variables) == 0:
            # failure to classify
            self.clf = None

        else:
            # and reclassify
            A = np.array(temp).T
            self.clf = RandomForestClassifier()
            self.clf.fit(A, Y)

    def estimate_from_scenario(self, labeled_entities, world):
        if self.clf is None: return [[0]]

        fv = generate_fv(world, labeled_entities, self.variables)
        fv = [fv[vname] if vname in fv else None for vname in self.variables]
        return self.estimate(fv)

    def estimate(self, a):
        if self.clf is None: return [[0]]

        return self.clf.predict_proba([a])

    def validate(self, variables, A, Y, fold=10):
        test_step = int(len(A)/fold)
        if test_step == 0: test_step = 1
        #print("test step: ", test_step)
        i = 0
        F1 = []
        for j in range(fold):
            train = A[0:i] + A[i+test_step:]
            trainy = Y[0:i] + Y[i+test_step:]
            test = A[i:i+test_step]
            testy = Y[i:i+test_step]

            if trainy.count(1) == 0 or testy.count(1) == 0:
                #print("Bad fold (size: {}), no positive examples".format(test_step))
                i += test_step
                continue

            self.train(variables, train, trainy)

            tp = 0
            fp = 0
            fn = 0
            pos = 0
            pose = 0

            for tx,ty in zip(test,testy):
                p = self.estimate(filter_values(tx, variables, self.variables))
                if p[0][1] > p[0][0]:
                    pos += 1
                    if ty == 1: tp += 1
                    else: fp += 1
                elif ty == 1: fn += 1
                if ty == 1: pose += 1

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0

            #print("Fold {}, pose: {}, posp: {}, prec: {}, rec: {}, f1: {}".format(i, pose, pos, prec, rec, f1))
            #print(self.variables)
            if f1 != 0: F1.append(f1)

            i += test_step

        return np.mean(F1)

class RandomForestRegressionEstimator:
    # importance threshhold to drop variable
    E = 0.001

    def __init__(self):
        pass

    def train(self, variables, A, Y):
        """A is an array of feature vectors. Y is a vector of target values."""

        self.clf = RandomForestRegressor()
        self.clf.fit(A, Y)

        # drop variables that don't matter
        A = np.array(A).T
        self.variables = []
        temp = []
        for i,(v,impact) in enumerate(zip(variables,self.clf.feature_importances_)):
            if impact >= RandomForestEstimator.E:
                self.variables.append(v)
                temp.append(A[i])

        if len(self.variables) == 0:
            # failure to classify
            self.clf = None

        else:
            # and reclassify
            A = np.array(temp).T
            self.clf = RandomForestRegressor()
            self.clf.fit(A, Y)

    def estimate_from_scenario(self, labeled_entities, world):
        if self.clf is None: return [[0]]

        fv = generate_fv(world, labeled_entities, self.variables)
        fv = [fv[vname] if vname in fv else None for vname in self.variables]
        return self.estimate(fv)

    def estimate(self, a):
        if self.clf is None: return 0

        return self.clf.predict([a])[0]

    def validate(self, variables, A, Y, fold=10):
        test_step = int(len(A)/fold)
        if test_step == 0: test_step = 1
        #print("test step: ", test_step)
        i = 0
        errors = []
        for j in range(fold):
            train = A[0:i] + A[i+test_step:]
            trainy = Y[0:i] + Y[i+test_step:]
            test = A[i:i+test_step]
            testy = Y[i:i+test_step]

            self.train(variables, train, trainy)

            error = 0
            for tx,ty in zip(test,testy):
                p = self.estimate(filter_values(tx, variables, self.variables))
                error += (p - ty)

            mean_error = error/test_step
            relative_error = mean_error/np.mean(testy)
            errors.append(relative_error)

            #print("Fold {}, error: {} (relative: {})".format(i, mean_error, relative_error))
            #print(self.variables)

            i += test_step

        return np.mean(errors)

class GBClassifierEstimator:
    # importance threshhold to drop variable
    E = 0.001

    def __init__(self):
        pass

    def train(self, variables, A, Y):
        """A is an array of feature vectors. Y is a vector of target values."""

        self.clf = GradientBoostingClassifier()
        self.clf.fit(A, Y)

        # drop variables that don't matter
        A = np.array(A).T
        self.variables = []
        temp = []
        for i,(v,impact) in enumerate(zip(variables,self.clf.feature_importances_)):
            if impact >= RandomForestEstimator.E:
                self.variables.append(v)
                temp.append(A[i])

        if len(self.variables) == 0:
            # failure to classify
            self.clf = None

        else:
            # and reclassify
            A = np.array(temp).T
            self.clf = GradientBoostingClassifier()
            self.clf.fit(A, Y)

    def estimate_from_scenario(self, labeled_entities, world):
        if self.clf is None: return [[0]]

        fv = generate_fv(world, labeled_entities, self.variables)
        fv = [fv[vname] if vname in fv else None for vname in self.variables]
        return self.estimate(fv)

    def estimate(self, a):
        if self.clf is None: return [[0]]

        return self.clf.predict_proba([a])

    def validate(self, variables, A, Y, fold=10):
        test_step = int(len(A)/fold)
        if test_step == 0: test_step = 1
        #print("test step: ", test_step)
        i = 0
        F1 = []
        for j in range(fold):
            train = A[0:i] + A[i+test_step:]
            trainy = Y[0:i] + Y[i+test_step:]
            test = A[i:i+test_step]
            testy = Y[i:i+test_step]

            if trainy.count(1) == 0 or testy.count(1) == 0:
                #print("Bad fold (size: {}), no positive examples".format(test_step))
                i += test_step
                continue

            self.train(variables, train, trainy)

            tp = 0
            fp = 0
            fn = 0
            pos = 0
            pose = 0

            for tx,ty in zip(test,testy):
                p = self.estimate(filter_values(tx, variables, self.variables))
                if p[0][1] > p[0][0]:
                    pos += 1
                    if ty == 1: tp += 1
                    else: fp += 1
                elif ty == 1: fn += 1
                if ty == 1: pose += 1

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0

            #print("Fold {}, pose: {}, posp: {}, prec: {}, rec: {}, f1: {}".format(i, pose, pos, prec, rec, f1))
            #print(self.variables)
            if f1 != 0: F1.append(f1)

            i += test_step

        return np.mean(F1)

class ABClassifierEstimator:
    # importance threshhold to drop variable
    E = 0.01

    def __init__(self):
        pass

    def train(self, variables, A, Y):
        """A is an array of feature vectors. Y is a vector of target values."""

        self.clf = AdaBoostClassifier()
        self.clf.fit(A, Y)

        # drop variables that don't matter
        A = np.array(A).T
        self.variables = []
        temp = []
        for i,(v,impact) in enumerate(zip(variables,self.clf.feature_importances_)):
            if impact >= RandomForestEstimator.E:
                self.variables.append(v)
                temp.append(A[i])

        if len(self.variables) == 0:
            # failure to classify
            self.clf = None

        else:
            # and reclassify
            A = np.array(temp).T
            self.clf = AdaBoostClassifier()
            self.clf.fit(A, Y)

    def estimate_from_scenario(self, labeled_entities, world):
        if self.clf is None: return [[0]]

        fv = generate_fv(world, labeled_entities, self.variables)
        fv = [fv[vname] if vname in fv else None for vname in self.variables]
        return self.estimate(fv)

    def estimate(self, a):
        if self.clf is None: return [[0]]

        return self.clf.predict_proba([a])

    def validate(self, variables, A, Y, fold=10):
        test_step = int(len(A)/fold)
        if test_step == 0: test_step = 1
        #print("test step: ", test_step)
        i = 0
        F1 = []
        E = []
        for j in range(fold):
            train = A[0:i] + A[i+test_step:]
            trainy = Y[0:i] + Y[i+test_step:]
            test = A[i:i+test_step]
            testy = Y[i:i+test_step]

            if trainy.count(1) == 0 or testy.count(1) == 0:
                #print("Bad fold (size: {}), no positive examples".format(test_step))
                i += test_step
                continue

            self.train(variables, train, trainy)

            tp = 0
            fp = 0
            fn = 0
            pos = 0
            pose = 0
            error = 0

            if len(set(testy)) == 1: continue

            for tx,ty in zip(test,testy):
                p = self.estimate(filter_values(tx, variables, self.variables))
                if p[0][1] > p[0][0]:
                    pos += 1
                    if ty == 1: tp += 1
                    else: fp += 1
                elif ty == 1: fn += 1
                if ty == 1: pose += 1

                # try error metric for bad predictions
                if p[0][1] > p[0][0] and ty == 0:
                    error += abs(p[0][1] - 0.5)
                elif p[0][1] <= p[0][0] and ty == 1:
                    error += abs(p[0][0] - 0.5)

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0

            #print("Fold {}, pose: {}, posp: {}, fp: {}, fn: {}, prec: {}, rec: {}, f1: {}".format(i, pose, pos, fp, fn, prec, rec, f1))
            #print(self.variables)
            if f1 != 0: F1.append(f1)
            E.append(error)

            i += test_step

        print("E:", np.mean(E))
        return np.mean(F1)

if __name__ == '__main__':
    x0 = np.array([1.,2,3,4,5,6,7,8,9])
    x1 = np.array([random.random()*8+1 for i in range(len(x0))])
    y = np.array([17*x0e + 2*x1e + 8 for x0e,x1e in zip(x0,x1)])
    print(y)
    le = LinearEstimator()
    le.train([x0,x1], y)
    print(le.weights)

    x0n = np.array([le.normalize(x, 0) for x in x0])
    x1n = np.array([le.normalize(x, 1) for x in x1])
    yn = np.array([le.ynormalize(y) for y in y])

    for i in range(len(y)):
        print("{} => {}".format(le.estimate((x0[i],x1[i])), y[i]))

    # print(le.nranges)
    # print(x0)
    # print(x0n)
    #
    # line = le.weights[0] * x0n + le.weights[1] * x1n + le.weights[2]
    #
    # print(le.residuals)
    #
    # plt.plot(x0n, yn, 'o', label='Original data', markersize=10)
    # plt.plot(x0n, line, 'r', label='Fitted line')
    # plt.legend()
    # plt.show()

