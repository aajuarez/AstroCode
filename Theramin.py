import SpectralTools
import SEDTools
import scipy
import numpy
import scipy.interpolate
import scipy.integrate
import Gnuplot
import pickle
import time
import copy
import os
import matplotlib.pyplot as pyplot


class gridPoint( object ):    # Object which contains information about a Chi-Squared grid point
    def __init__(self, TGBcoords, contLevel, veiling):
        self.limits = {"T":[2500.0, 6000.0], "G":[300.0, 500.0], "B":[0.0,4.0], "dy":[0.95, 1.05], "r":[0.0, 10.0]}
        self.TGB = {"T":TGBcoords["T"], "G":TGBcoords["G"], "B":TGBcoords["B"]}
        self.contLevel = {}
        self.veiling = veiling
        self.n_dims = 4
        for i in contLevel.keys():
            self.contLevel[i] = contLevel[i]
            self.n_dims += 1

    def dump(self):
        retval = 'T='+str(int(self.TGB["T"]))+', G='+str(int(self.TGB["G"]))+', B='+str(float(self.TGB["B"]))+'\n'
        for i in self.contLevel.keys():
            retval += 'Feature '+str(i)+', dy = '+str(self.contLevel[i])+'\n'

        retval += 'r_2.2 = '+str(self.veiling)+'\n'

        return retval

    def difference(self, other):
        retval = 'dT='+str(int(self.TGB["T"])-int(other.TGB["T"]))+'\n'
        retval += 'dG='+str(int(self.TGB["G"])-int(other.TGB["G"]))+'\n'
        retval += 'dB='+str(int(self.TGB["B"])-int(other.TGB["B"]))+'\n'
        for i in self.contLevel.keys():
            retval += 'Feature '+str(i)+', dy = '+str(self.contLevel[i]-other.contLevel[i])+'\n'

        retval += 'dr_2.2 = '+str(self.veiling/other.veiling)+'\n'

        return retval
    
    def checkLimits(self):
        for key in ["T", "G", "B"]:
            if ( self.TGB[key] >= self.limits[key][0] ):
                if ( self.TGB[key] <= self.limits[key][1]):
                    pass
                else:
                    self.TGB[key] =self.limits[key][1]
            else:
                self.TGB[key] = self.limits[key][0]

        if (self.veiling < 0.0):
            self.veiling = 0.0025

class spectralSynthesizer( object ):
    def __init__(self):
        feat_num = [1, 2, 3, 4, 5]
        xstart = [1.150, 1.480, 1.57, 2.170, 2.240]
        xstop = [1.2200, 1.520, 1.60, 2.230, 2.310]
        slope_start = [1.13, 1.47, 1.55, 2.100, 2.23]
        slope_stop = [1.25, 1.54, 1.62, 2.25, 2.31]
        strongLines = [[1.16, 1.168, 1.176, 1.1828, 1.1884, 1.198], [1.488, 1.503, 1.5045], [1.5745, 1.5770],
        [2.166,2.2066], [2.263, 2.267, 2.30]]
        lineWidths = [[0.003, 0.003, 0.003, 0.0025, 0.0025, 0.0025], [0.005, 0.005, 0.01], [0.005, 0.005],[0.005, 0.005],[0.005, 0.005,0.01]]
        #comparePoints = [[[1.1816,1.1838],[1.1871,1.1900],[1.1942,1.1995],[1.2073,1.2087]], [[2.1765, 2.18], [2.1863,2.1906], [2.199, 2.2015], [2.2037, 2.210]], [[2.2525,2.2551],[2.2592, 2.2669], [2.2796, 2.2818]]]
        comparePoints = [[[1.157,1.17],[1.175,1.1995],[1.2073,1.212]],[[1.482, 1.519]],[[1.571,1.599]],
        [[2.1765,2.18],[2.1863,2.2015], [2.203, 2.23]], [[2.2425,2.258],[2.270,2.287]]]#[2.2425,2.31]]]
        #[[2.1765,2.18],[2.1863,2.2015], [2.203, 2.23]], [[2.2425,2.258]]]
        continuumPoints = [[[1.165,1.168],[1.171,1.174],[1.19,1.195],[1.211, 1.22]],[[1.49,1.50],[1.508,1.52]],[[1.57, 1.60]],[[2.192,2.196],[2.211,2.218]],[[2.24, 2.258],[2.27, 2.277],[2.86,2.291]]]

        self.modelBaseDir='/home/deen/Data/StarFormation/MOOG/zeeman/smoothed/'
        self.dataBaseDir='/home/deen/Data/StarFormation/TWA/bfields/'
        self.delta = {"T":200.0, "G":50.0, "B":0.75, "dy":0.0025, "r":1.25}    # [dT, dG, dB, d_dy, dr]
        self.limits = {"T":[2500.0, 6000.0], "G":[300.0, 500.0], "B":[0.0,4.0], "dy":[0.95, 1.05], "r":[0.0, 10.0]}
        self.floaters = {"T":True, "G":True, "B":True, "dy":True, "r":True}
        self.features = {}

        self.calc_VeilingSED(8000.0, 2500.0, 1400.0, 62.0, 910.0)

        #for i in range(len(xstart)):
        #for i in [4]:
        for i in [0,1,3,4]:
            feat = dict()
            print feat_num[i]
            feat["num"] = feat_num[i]
            feat["xstart"] = xstart[i]
            feat["xstop"] = xstop[i]
            feat["slope_start"] = slope_start[i]
            feat["slope_stop"] = slope_stop[i]
            feat["strongLines"] = strongLines[i]
            feat["lineWidths"] = lineWidths[i]
            feat["comparePoints"] = comparePoints[i]
            feat["continuumPoints"] = continuumPoints[i]
            self.features[feat_num[i]] = feat

        self.temps = numpy.array(range(2500, 4000, 100)+range(4000,6250, 250))
        self.gravs = numpy.array(range(300, 600, 50))
        self.bfields = numpy.array(numpy.arange(0, 4.5, 0.5))
        self.ranges = {"T":self.temps, "G":self.gravs, "B":self.bfields}

    def calc_VeilingSED(self, Thot, Tint, Tcool, fi_fh, fc_fh):
        wave = numpy.arange(1.0, 2.5, 0.01)
        bm = numpy.argsort(abs(wave-2.2))[0]
        Bhot = SpectralTools.blackBody(wl = wave/10000.0, T=Thot, outUnits='Energy')
        Bint = SpectralTools.blackBody(wl = wave/10000.0, T=Tint, outUnits='Energy')*fi_fh
        Bcool = SpectralTools.blackBody(wl = wave/10000.0, T=Tcool, outUnits='Energy')*fc_fh
        composite = Bhot+Bint+Bcool
        composite /= composite[bm]
        self.veiling_SED = scipy.interpolate.interp1d(wave, composite)

    def binMOOGSpectrum(self, spectrum, native_wl, new_wl):
        retval = numpy.zeros(len(new_wl))
        for i in range(len(new_wl)-1):
            bm = scipy.where( (native_wl > new_wl[i]) & (native_wl <= new_wl[i+1]) )[0]
            if (len(bm) > 0):
                num = scipy.integrate.simps(spectrum[bm], x=native_wl[bm])
                denom = max(native_wl[bm]) - min(native_wl[bm])
                retval[i] = num/denom
            else:
                retval[i] = retval[-1]

        bm = scipy.where (native_wl > new_wl[-1])[0]
        if len(bm) > 1:
            num = scipy.integrate.simps(spectrum[bm], x=native_wl[bm])
            denom = max(native_wl[bm]) - min(native_wl[bm])
            retval[-1] = num/denom
        else:
            retval[-1] = spectrum[bm]

        return retval

    def calcError(self, y1, y2, z, x, comparePoints, **kwargs):
        error = 0.0
        if ("plt" in kwargs):
            obs = Gnuplot.Data(x, y1, with_='lines')
            new = Gnuplot.Data(x, y2, with_='lines')
            kwargs["plt"].plot(obs, new)
        bm = []
        for region in comparePoints:
            bm.extend(scipy.where( (x > region[0]) & (x < region[1]) )[0])
                
        for dat in zip(y1[bm], y2[bm], z[bm]):
            error += ((dat[0]-dat[1])/dat[2])**2
            
        #return error/len(y1[bm])
        return error


    def findWavelengthShift(self, x_window, flat, x_sm, y_sm):
        if self.currFeat == 2:
            y_sm *= 0.95
        orig_bm = scipy.where( (x_window > min(x_sm)) & (x_window < max(x_sm)) )[0]
        feature_x = x_window[orig_bm]
        model = scipy.interpolate.interpolate.interp1d(x_sm, y_sm, kind = 'linear', bounds_error = False)
        ycorr = scipy.correlate((1.0-flat[orig_bm]), (1.0-model(feature_x)), mode ='full')
        xcorr = scipy.linspace(0, len(ycorr)-1, num=len(ycorr))

        fitfunc = lambda p, x: p[0]*scipy.exp(-(x-p[1])**2/(2.0*p[2]**2)) + p[3]
        errfunc = lambda p, x, y: fitfunc(p, x) - y
        
        x_zoom = xcorr[len(ycorr)/2 - 3: len(ycorr)/2+5]
        y_zoom = ycorr[len(ycorr)/2 - 3: len(ycorr)/2+5]
        
        p_guess = [ycorr[len(ycorr)/2], len(ycorr)/2, 3.0, 0.0001]
        p1, success = scipy.optimize.leastsq(errfunc, p_guess, args = (x_zoom, y_zoom))
        
        fit = p1[0]*scipy.exp(-(x_zoom- p1[1])**2/(2.0*p1[2]**2)) + p1[3]
        
        xcorr = p1[1]
        nLags = xcorr-(len(orig_bm)-1.5)
        offset_computed = nLags*(feature_x[0]-feature_x[1])
        if abs(offset_computed) > 20:
            offset_computed = 0
            
        self.features[self.currFeat]["x_offset"] = offset_computed

    def calcVeiling(self, y_obs, y_calc, x, comparePoints):
        bm = []
        for region in comparePoints:
            bm.extend(scipy.where( (x > region[0]) & (x <region[1]) )[0])
            
        rk_guess = [0.01]
        ff = lambda p, y_c: (y_c+p[0])/(abs(p[0])+1.0)
        ef = lambda p, y_c, y_o: ff(p, y_c)-y_o
        veil, success = scipy.optimize.leastsq(ef, rk_guess, args = (y_calc[bm], y_obs[bm]))
        
        '''
        plt = Gnuplot.Gnuplot()
        a = Gnuplot.Data(x[bm], y_obs[bm], with_='lines')
        b = Gnuplot.Data(x[bm], y_calc[bm], with_='lines')
        c = Gnuplot.Data(x[bm], (y_calc[bm]+veil[0])/(1.0+veil[0]), with_='lines')
        plt.plot(a, b, c)
        #raw_input()
        '''

        return veil[0]

    def interpolatedModel(self, T, G, B):
        if ( (abs(self.interpolated_model[self.currFeat]["T"]- T) > 2.0) |
        (abs(self.interpolated_model[self.currFeat]["G"]- G) > 2.0) |
        (abs(self.interpolated_model[self.currFeat]["B"]-B)>0.05) ):
            
            self.interpolated_model[self.currFeat]["T"] = T
            self.interpolated_model[self.currFeat]["G"] = G
            self.interpolated_model[self.currFeat]["B"] = B
            #choose bracketing temperatures
            if not(T in self.temps):
                Tlow = max(self.temps[scipy.where(self.temps <= T)])
                Thigh = min(self.temps[scipy.where(self.temps >= T)])
            else:
                Tlow = Thigh = T

            #choose bracketing surface gravities
            if not(G in self.gravs):
                Glow = max(self.gravs[scipy.where(self.gravs <= G)])
                Ghigh = min(self.gravs[scipy.where(self.gravs >= G)])
            else:
                Glow = Ghigh = G

            #choose bracketing B-fields
            if not(B in self.bfields):
                Blow = max(self.bfields[scipy.where(self.bfields <= B)])
                Bhigh  = min(self.bfields[scipy.where(self.bfields >= B)])
            else:
                Blow = Bhigh = B

            #interpolate 
            y1 = self.readMOOGModel(Tlow, Glow, Blow, axis ='y')
            y2 = self.readMOOGModel(Thigh, Glow, Blow, axis ='y')
            y3 = self.readMOOGModel(Tlow, Ghigh, Blow, axis ='y')
            y4 = self.readMOOGModel(Thigh, Ghigh, Blow, axis ='y')
            y5 = self.readMOOGModel(Tlow, Glow, Bhigh, axis ='y')
            y6 = self.readMOOGModel(Thigh, Glow, Bhigh, axis ='y')
            y7 = self.readMOOGModel(Tlow, Ghigh, Bhigh, axis ='y')
            y8 = self.readMOOGModel(Thigh, Ghigh, Bhigh, axis ='y')

            new_y = numpy.zeros(len(y1))
            for i in range(len(y1)):
                if y1[i] == y2[i]:
                    y12 = y1[i]
                else:
                    y12 = scipy.interpolate.interp1d([Tlow, Thigh], [y1[i], y2[i]])(T)
                if y3[i] == y4[i]:
                    y34 = y3[i]
                else:
                    y34 = scipy.interpolate.interp1d([Tlow, Thigh], [y3[i], y4[i]])(T)
                if y5[i] == y6[i]:
                    y56 = y5[i]
                else:
                    y56 = scipy.interpolate.interp1d([Tlow, Thigh], [y5[i], y6[i]])(T)
                if y7[i] == y8[i]:
                    y78 = y7[i]
                else:
                    y78 = scipy.interpolate.interp1d([Tlow, Thigh], [y7[i], y8[i]])(T)

                if (y12==y34):
                    y1234 = y12
                else:
                    y1234 = scipy.interpolate.interp1d([Glow, Ghigh], [y12, y34])(G)
                if (y56 == y78):
                    y5678 = y56
                else:
                    y5678 = scipy.interpolate.interp1d([Glow, Ghigh], [y56, y78])(G)
                if (y1234==y5678):
                    new_y[i] = y1234
                else:
                    new_y[i] = scipy.interpolate.interp1d([Blow, Bhigh], [y1234, y5678])(B)

            self.interpolated_model[self.currFeat]["new_y"] = new_y
        else:
            new_y = self.interpolated_model[self.currFeat]["new_y"]
        return new_y

    def readMOOGModel(self, T, G, B, **kwargs):
        df = self.modelBaseDir+'B_'+str(B)+'kG/f'+str(self.features[self.currFeat]["num"])+'_MARCS_T'+str(int(T))+'G'+str(int(G))+'_R2000'
        x_sm, y_sm = SpectralTools.read_2col_spectrum(df)
        if "axis" in kwargs:
            if kwargs["axis"] == 'y':
                return y_sm
            elif kwargs["axis"] == 'x':
                return x_sm
        else:
            return x_sm, y_sm

    def computeS(self, coordinates, **kwargs):
        try:
           if kwargs["returnSpectra"] == True:
               retval = {}
        except:
            retval = 0.0
        for num in coordinates.contLevel.keys():
            self.currFeat = num
            y_new = self.interpolatedModel(coordinates.TGB["T"], coordinates.TGB["G"], coordinates.TGB["B"])
            x_sm = self.features[self.currFeat]["wl"]

            new_wl = self.x_window[self.currFeat] + self.features[self.currFeat]["x_offset"]
            overlap = scipy.where( (new_wl > min(x_sm)) & (new_wl < max(x_sm)) )[0]

            synthetic_spectrum = self.binMOOGSpectrum(y_new, x_sm, new_wl[overlap])*coordinates.contLevel[num]
            excess = self.compute_Excess(new_wl[overlap], coordinates.TGB["T"], coordinates.veiling)
            veiled = (synthetic_spectrum+excess)/(excess+1.0)

            try:
                if kwargs["returnSpectra"] == True:    # We are simply returning the different spectra
                    retval[num] = {"wl":new_wl[overlap], "obs":self.flat[self.currFeat][overlap], "veiled":veiled,
                    "noise":self.z[self.currFeat][overlap]}
            except:
                #'''
                if "plot" in kwargs:
                    obs = Gnuplot.Data(new_wl[overlap], self.flat[num][overlap], with_='lines')
                    sim = Gnuplot.Data(new_wl[overlap], synthetic_spectrum, with_='lines')
                    veil = Gnuplot.Data(new_wl[overlap], veiled, with_='lines')
                    kwargs["plot"].plot(obs, sim, veil)
                    time.sleep(2.0)
                #'''
                if (self.compareMode == 'LINES'):
                    retval += self.calcError(self.flat[self.currFeat][overlap],veiled,self.z[self.currFeat][overlap], new_wl[overlap], self.features[self.currFeat]["comparePoints"])
                elif (self.compareMode == 'CONTINUUM'):
                    retval += self.calcError(self.flat[self.currFeat][overlap],veiled,self.z[self.currFeat][overlap],
                    new_wl[overlap], self.features[self.currFeat]["continuumPoints"])

        return retval
    
    def compute_Excess(self, wl, Teff, veiling):
        excess_BB = self.veiling_SED(wl)
        star_BB = SpectralTools.blackBody(wl = wl/10000.0, T=Teff, outUnits="Energy")
        zp = SpectralTools.blackBody(wl=2.2/10000.0, T=Teff, outUnits="Energy")
        star_BB /= zp
        excess = excess_BB/star_BB*veiling
        
        return excess
    
    def computeDeriv(self, coords, index):
        coords[index] += self.delta[index]
        S1 = self.computeS(coords)

        coords[index] -= 2.0*self.delta[index]
        S2 = self.computeS(coords)

        coords[index] += self.delta[index]

        return (S1-S2)/(2*self.delta[index])

    def compute2ndDeriv(self, coords, keys, i, j):
        key_i = keys[i]
        key_j = keys[j]
        if( key_i == key_j ):
            if ( key_i in ["T", "G", "B"]):
                ifactor = 1.0
                while (((coords.TGB[key_i] - self.delta[key_i]*ifactor) < self.limits[key_i][0]) |
                ((coords.TGB[key_i]+self.delta[key_i]*ifactor) > self.limits[key_i][1])):
                    ifactor *= 0.8
                coord_plus = copy.deepcopy(coords)
                coord_plus.TGB[key_i] += self.delta[key_i]*ifactor
                S_plus = self.computeS(coord_plus)
                coord = copy.deepcopy(coords)
                S = self.computeS(coord)
                coord_minus = copy.deepcopy(coords)
                coord_minus.TGB[key_i] -= self.delta[key_i]*ifactor
                S_minus = self.computeS(coord_minus)
                denominator = (self.delta[key_i]*ifactor)**2.0
            elif ( key_i == 'r'):
                ifactor = 1.0
                while (((coords.veiling/(self.delta[key_i]*ifactor)) < self.limits[key_i][0]) |
                ((coords.veiling*(self.delta[key_i]*ifactor)) > self.limits[key_i][1])):
                    ifactor *= 0.8
                coord_plus = copy.deepcopy(coords)
                coord_plus.veiling *= self.delta[key_i]*ifactor
                S_plus = self.computeS(coord_plus)
                coord = copy.deepcopy(coords)
                S = self.computeS(coord)
                coord_minus = copy.deepcopy(coords)
                coord_minus.veiling /= self.delta[key_i]*ifactor
                S_minus = self.computeS(coord_minus)
                denominator = (coords.veiling* (1.0-self.delta[key_i]*ifactor))**2.0
            elif ( key_i in coords.contLevel.keys() ):
                ifactor = 1.0
                while (((coords.contLevel[key_i] - self.delta['dy']*ifactor) < self.limits['dy'][0]) |
                ((coords.contLevel[key_i]+self.delta['dy']*ifactor) > self.limits['dy'][1])):
                    ifactor *= 0.8
                coord_plus = copy.deepcopy(coords)
                coord_plus.contLevel[key_i] += self.delta['dy']*ifactor
                S_plus = self.computeS(coord_plus)
                coord = copy.deepcopy(coords)
                S = self.computeS(coord)
                coord_minus = copy.deepcopy(coords)
                coord_minus.contLevel[key_i] -= self.delta['dy']*ifactor
                S_minus = self.computeS(coord_minus)
                denominator = (self.delta['dy']*ifactor)**2.0

            return (S_plus-2*S+S_minus)/denominator
        else:
            ifactor = 1.0
            if ( key_i in ["T", "G", "B"]):
                while (((coords.TGB[key_i] - self.delta[key_i]*ifactor) < self.limits[key_i][0]) |
                ((coords.TGB[key_i]+self.delta[key_i]*ifactor) > self.limits[key_i][1])):
                    ifactor *= 0.8
                coord_one = copy.deepcopy(coords)
                coord_two = copy.deepcopy(coords)
                coord_three = copy.deepcopy(coords)
                coord_four = copy.deepcopy(coords)
                coord_one.TGB[key_i] += self.delta[key_i]*ifactor
                coord_three.TGB[key_i] += self.delta[key_i]*ifactor
                coord_two.TGB[key_i] -= self.delta[key_i]*ifactor
                coord_four.TGB[key_i] -= self.delta[key_i]*ifactor
                denominator = self.delta[key_i]*ifactor
            elif ( key_i == 'r'):
                while (((coords.veiling/(self.delta[key_i]*ifactor)) < self.limits[key_i][0]) |
                ((coords.veiling*(self.delta[key_i]*ifactor)) > self.limits[key_i][1])):
                    ifactor *= 0.8
                coord_one = copy.deepcopy(coords)
                coord_two = copy.deepcopy(coords)
                coord_three = copy.deepcopy(coords)
                coord_four = copy.deepcopy(coords)
                coord_one.veiling *= self.delta[key_i]*ifactor
                coord_three.veiling *= self.delta[key_i]*ifactor
                coord_two.veiling /= self.delta[key_i]*ifactor
                coord_four.veiling /= self.delta[key_i]*ifactor
                denominator = coords.veiling*(1.0-self.delta[key_i]*ifactor)
            elif ( key_i in coords.contLevel.keys() ):
                while (((coords.contLevel[key_i] - self.delta['dy']*ifactor) < self.limits['dy'][0]) |
                ((coords.contLevel[key_i]+self.delta['dy']*ifactor) > self.limits['dy'][1])):
                    ifactor *= 0.8
                coord_one = copy.deepcopy(coords)
                coord_two = copy.deepcopy(coords)
                coord_three = copy.deepcopy(coords)
                coord_four = copy.deepcopy(coords)
                coord_one.contLevel[key_i] += self.delta['dy']*ifactor
                coord_three.contLevel[key_i] += self.delta['dy']*ifactor
                coord_two.contLevel[key_i] -= self.delta['dy']*ifactor
                coord_four.contLevel[key_i] -= self.delta['dy']*ifactor
                denominator = self.delta['dy']*ifactor

            jfactor = 1.0
            if ( key_j in ["T", "G", "B"]):
                while (((coords.TGB[key_j] - self.delta[key_j]*jfactor) < self.limits[key_j][0]) |
                ((coords.TGB[key_j]+self.delta[key_j]*jfactor) > self.limits[key_j][1])):
                    jfactor *= 0.8
                coord_one.TGB[key_j] += self.delta[key_j]*jfactor
                coord_two.TGB[key_j] += self.delta[key_j]*jfactor
                coord_three.TGB[key_j] -= self.delta[key_j]*jfactor
                coord_four.TGB[key_j] -= self.delta[key_j]*jfactor
                denominator *= self.delta[key_j]*jfactor
            elif ( key_j == 'r'):
                while (((coords.veiling/(self.delta[key_j]*jfactor)) < self.limits[key_j][0]) |
                ((coords.veiling*(self.delta[key_j]*jfactor)) > self.limits[key_j][1])):
                    jfactor *= 0.8
                coord_one.veiling *= self.delta[key_j]*jfactor
                coord_two.veiling *= self.delta[key_j]*jfactor
                coord_three.veiling /= self.delta[key_j]*jfactor
                coord_four.veiling /= self.delta[key_j]*jfactor
                denominator *= coords.veiling*(1.0-self.delta[key_j]*jfactor)
            elif ( key_j in coords.contLevel.keys() ):
                while (((coords.contLevel[key_j] - self.delta['dy']*jfactor) < self.limits['dy'][0]) |
                ((coords.contLevel[key_j]+self.delta['dy']*jfactor) > self.limits['dy'][1])):
                    jfactor *= 0.8
                coord_one.contLevel[key_j] += self.delta['dy']*jfactor
                coord_two.contLevel[key_j] += self.delta['dy']*jfactor
                coord_three.contLevel[key_j] -= self.delta['dy']*jfactor
                coord_four.contLevel[key_j] -= self.delta['dy']*jfactor
                denominator *= self.delta['dy']*jfactor

            S1 = self.computeS(coord_one)
            S2 = self.computeS(coord_two)
            S3 = self.computeS(coord_three)
            S4 = self.computeS(coord_four)

            return (S1 - S2 - S3 + S4)/(4*denominator)

    def computeGradient(self, coords):
        G = numpy.zeros(len(coords))

        for i in range(len(coords)):
            G[i] = self.computeDeriv(coords, i)

        return numpy.matrix(G)

    def computeHessian(self, coords):
        new_coords = copy.deepcopy(coords)
        '''
             i = 0, 1, 2 -> T, G, B
             i = 3 = veiling
             i = 4 ... n -> dy_i, dy_(n-4)
        '''
        keys = {}
        n = 0
        for i in ["T", "G", "B", "r"]:
            if self.floaters[i] == True:
                keys[n] = i
                n += 1
        if self.floaters["dy"] == True:
            for key in coords.contLevel.keys():
                keys[n] = key
                n += 1
        H = numpy.zeros([n,n])

        for i in range(n):
            for j in numpy.arange(n - i) + i:
                H[i,j] = H[j,i] = self.compute2ndDeriv(new_coords, keys, i, j)
                print i, j, H[i,j]

        self.Hessian = numpy.matrix(H)

    def countPoints(self, minimum):
        points = 0.0
        for feat in minimum.contLevel.keys():
            wl = self.features[feat]["wl"]
            comparePoints = self.features[feat]["comparePoints"]
            
            bm = []
            for region in comparePoints:
                bm.extend(scipy.where( (wl > region[0]) & (wl < region[1]) )[0])

            points += len(bm)

        return points


    def computeCovariance(self, minimum):
        self.computeHessian(minimum)
        self.covariance = 2*self.Hessian.getI()*(self.computeS(minimum)/(self.countPoints(minimum)-minimum.n_dims))
        
        return self.covariance

    def marquardt(self, chisq):
        self.alpha = 0.01
        old_chisq = chisq[0][0]
        old_coordinates = chisq[0][1]
        
        while( old_chisq > 10):
            print old_chisq
            print old_coordinates
            G = self.computeGradient(old_coordinates)
            H = self.computeHessian(old_coordinates)
            H_prime = H*numpy.matrix(numpy.eye(len(old_coordinates), len(old_coordinates))*(1.0+self.alpha))
            
            vect = H_prime.I*G.transpose()
            new_coordinates = old_coordinates+vect.transpose()
            old_chisq = self.computeS(numpy.array(new_coordinates)[0])
            old_coordinates = numpy.array(new_coordinates)[0]

    def gridSearch(self, **kwargs):
        Tval = []
        Gval = []
        Bval = []
        veiling = []
        S = []

        outfile = kwargs["outfile"]
        
        if kwargs["mode"] == 'FINAL':
            infile = open(outfile)
            for line in infile.readlines()[1:]:
                l = line.split()
                Tval.append(float(l[0]))
                Gval.append(float(l[1]))
                Bval.append(float(l[2]))
                veiling.append(float(l[4]))
                S.append(float(l[5]))
            x_offset = float(l[3])
            infile.close()
        elif kwargs["mode"] == 'PREP':
            out = open(outfile, 'w')
            x_sm = self.features[self.currFeat]["wl"]
            x_offset = self.features[self.currFeat]["x_offset"]
            new_wl = self.x_window+x_offset
            out.write('#%10s %10s %10s %10s %10s %10s\n' % ('Temp', 'Grav', 'Bfield', 'X offset', 'Veiling', 'Chi-Square'))

            overlap = scipy.where( (new_wl > min(x_sm)) & (new_wl < max(x_sm)) )[0]

            for B in self.bfields:
                for T in self.temps:
                    print B, T
                    for G in self.gravs:
                        flag = False
                        if (T < 3900.0):
                            flag = True
                        elif (G < 500):
                            flag = True
                        if flag == True:
                            y_sm = self.readMOOGModel(T, G, B, axis ='y')
                            synthetic_spectrum = self.binMOOGSpectrum(y_sm, x_sm, new_wl[overlap])
                            #Calculate the initial guess for the veiling
                            veiling.append(self.calcVeiling(self.flat[overlap], synthetic_spectrum,new_wl[overlap],self.features[self.currFeat]["comparePoints"]))
                            S.append(self.calcError(self.flat[overlap], (synthetic_spectrum+veiling[-1])/(veiling[-1]+1.0),
                            self.z[overlap], new_wl[overlap], self.features[self.currFeat]["comparePoints"]))#,
                            #p#lt=kwargs["plt"]))
                            Tval.append(T)
                            Gval.append(G)
                            Bval.append(B)
                            out.write('%10.3f %10.3f %10.3f %10.4e %10.4e %10.3e\n' % (T,G,B,x_offset,veiling[-1], S[-1]) )

            out.close()
            
        Tval = numpy.array(Tval)
        Gval = numpy.array(Gval)
        Bval = numpy.array(Bval)
        S = numpy.array(S)
        veiling = numpy.array(veiling)
        try:
            if "noBField" in kwargs:
                bm = scipy.where(Bval == 0.0)
                Tval = Tval[bm]
                Gval = Gval[bm]
                Bval = Bval[bm]
                veiling = veiling[bm]
                S = S[bm]
        except:
            pass

        order = numpy.argsort(S)

        self.features[self.currFeat]["x_offset"] = x_offset

        '''
        for B in self.bfields:
            for G in self.gravs:
                bm = scipy.where( (Gval==G) & (Bval==B) )[0]
                a = Gnuplot.Data(Tval[bm], S[bm], with_='lines')
                kwargs["plot"].plt('set title "B='+str(B)+', G ='+str(G)+'"')
                kwargs["plot"].plt.plot(a)
                raw_input()'''

        #initial_guess = [numpy.mean(Tval[order[0:20]]), numpy.mean(Gval[order[0:20]]), numpy.mean(Bval[order[0:20]]), x_offset, 1.00,0.00]
        initial_guess={"T":numpy.mean(Tval[order[0:10]]),"G":numpy.mean(Gval[order[0:10]]),"B":numpy.mean(Bval[order[0:10]])}
        return initial_guess

    def findCentroid(self, coords):
        T = 0.0
        G = 0.0
        B = 0.0
        n_coords = float(len(coords))
        n_feat = len(coords[0].contLevel.keys())
        dy = {key:0.0 for key in coords[0].contLevel.keys()}
        r = 0.0
        for coord in coords:
            T += coord.TGB["T"]/n_coords
            G += coord.TGB["G"]/n_coords
            B += coord.TGB["B"]/n_coords
            r += coord.veiling/n_coords
            for i in coord.contLevel.keys():
                dy[i] += coord.contLevel[i]/n_coords

        TGB = {"T":T, "G":G, "B":B}
        cL = {}
        for i in coords[0].contLevel.keys():
            cL[i] = dy[i]

        retval = gridPoint(TGB, cL, r)
        return retval
            
    def reflect(self, centroid, coord, **kwargs):
        if kwargs["trial"] == 1:
            print "Trial 1"
            new_T = 2.0*centroid.TGB["T"] - coord.TGB["T"]
            new_G = 2.0*centroid.TGB["G"] - coord.TGB["G"]
            new_B = 2.0*centroid.TGB["B"] - coord.TGB["B"]
            new_dy = {key:0.0 for key in coord.contLevel.keys()}
            new_r = 2.0*centroid.veiling - coord.veiling
            for i in coord.contLevel.keys():
                new_dy[i] = 2.0*centroid.contLevel[i] - coord.contLevel[i]

            TGB = {"T":new_T, "G":new_G, "B":new_B}
            cL = {key:0.0 for key in coord.contLevel.keys()}
            for i in coord.contLevel.keys():
                cL[i] = new_dy[i]

            retval = gridPoint(TGB, cL, new_r)

        elif kwargs["trial"] == 2:
            print "Trial 2"
            new_T = 3.0*centroid.TGB["T"] - 2.0*coord.TGB["T"]
            new_G = 3.0*centroid.TGB["G"] - 2.0*coord.TGB["G"]
            new_B = 3.0*centroid.TGB["B"] - 2.0*coord.TGB["B"]
            n_feat = len(coord.contLevel)
            new_dy = {key:0.0 for key in coord.contLevel.keys()}
            new_r = 3.0*centroid.veiling - 2.0*coord.veiling
            for i in coord.contLevel.keys():
                new_dy[i] = 3.0*centroid.contLevel[i] - 2.0*coord.contLevel[i]

            TGB = {"T":new_T, "G":new_G, "B":new_B}
            cL = {key:0.0 for key in coord.contLevel.keys()}
            for i in coord.contLevel.keys():
                cL[i] = new_dy[i]
            retval = gridPoint(TGB, cL, new_r)

        elif kwargs["trial"] == 3:
            print "Trial 3"
            new_T = centroid.TGB["T"] - (centroid.TGB["T"] - coord.TGB["T"])/2.0
            new_G = centroid.TGB["G"] - (centroid.TGB["G"]-coord.TGB["G"])/2.0
            new_B = centroid.TGB["B"] - (centroid.TGB["B"]-coord.TGB["B"])/2.0
            n_feat = len(coord.contLevel)
            new_dy = {key:0.0 for key in coord.contLevel.keys()}
            new_r = centroid.veiling - (centroid.veiling - coord.veiling)/2.0
            for i in coord.contLevel.keys():
                new_dy[i] = centroid.contLevel[i]-(centroid.contLevel[i]-coord.contLevel[i])/2.0

            TGB = {"T":new_T, "G":new_G, "B":new_B}
            cL = {key:0.0 for key in coord.contLevel.keys()}
            for i in coord.contLevel.keys():
                cL[i] = new_dy[i]
            retval = gridPoint(TGB, cL, new_r)
            
        return retval

    def contract(self, centroid, coords):
        for i in range(len(coords)):
            newcoord = self.reflect(centroid, coords[i], trial=3)
            coords[i] = newcoord

        return coords

    def simplex(self, guess, plt, **kwargs):
        #simplex_coords = [init_guess]
        #simplex_values = [self.computeS(init_guess)]
        self.compareMode = kwargs["mode"]
        if kwargs["mode"] == 'CONTINUUM':
            self.floaters["T"] = False
            self.floaters["G"] = False
            self.floaters["B"] = False
            self.floaters["dy"] = True
            self.floaters["r"] = False
        elif kwargs["mode"] == 'LINES':
            self.floaters["T"] = True 
            self.floaters["G"] = True
            self.floaters["B"] = True
            self.floaters["dy"] = False
            self.floaters["r"] = True

        if "Fixed_B" in kwargs:
            self.floaters["B"] = False

        coords = []
        Svalues = []
        for key in self.floaters.keys():
            if self.floaters[key] == True:
                new_TGBcoords = {"T":guess.TGB["T"], "G":guess.TGB["G"], "B":guess.TGB["B"]}
                if key in new_TGBcoords:
                    if (new_TGBcoords[key] + self.delta[key]) < self.limits[key][1]:
                        new_TGBcoords[key] += self.delta[key]
                    else:
                        new_TGBcoords[key] -= self.delta[key]
                    contLevels = {}
                    for num in self.x_window.keys():
                        contLevels[num] = guess.contLevel[num]
                    veil = guess.veiling
                    simplexPoint = gridPoint(new_TGBcoords, contLevels, veil)
                    coords.append(simplexPoint)
                    Svalues.append(self.computeS(simplexPoint))
                elif key == 'dy':
                    for num in self.x_window.keys():
                        contLevels = {}
                        for i in self.x_window.keys():
                            contLevels[i] = guess.contLevel[i]
                        if (contLevels[num] + self.delta["dy"]) < self.limits["dy"][1]:
                            contLevels[num] += self.delta["dy"]
                        else:
                            contLevels[num] -= self.delta["dy"]
                        veil = guess.veiling
                        simplexPoint = gridPoint(new_TGBcoords, contLevels, veil)
                        coords.append(simplexPoint)
                        Svalues.append(self.computeS(simplexPoint))
                elif key == 'r':
                    contLevels = {}
                    for i in self.x_window.keys():
                        contLevels[i] = guess.contLevel[i]
                    veil = guess.veiling
                    if (veil + self.delta["r"]) < self.limits["r"][1]:
                        veil += veil/2.0
                    else:
                        veil -= veil/2.0
                    simplexPoint = gridPoint(new_TGBcoords, contLevels, veil)
                    coords.append(simplexPoint)
                    Svalues.append(self.computeS(simplexPoint))

        n_contractions = 0

        print len(coords)
        while (numpy.std(Svalues) > numpy.mean(Svalues)*0.005):
            print numpy.mean(Svalues), numpy.std(Svalues)
            order = numpy.argsort(Svalues)
            centroid = self.findCentroid([coords[i] for i in order[0:-1]])
            print centroid.dump()
            print 'Worst Point: ', Svalues[order[-1]]
            print coords[order[-1]].difference(centroid)

            #junk = self.computeS(centroid)#, plot=plt)
            # Reflect about centroid
            trial_1 = self.reflect(centroid, coords[order[-1]], trial=1)
            trial_1.checkLimits()
            S1 = self.computeS(trial_1)
            
            if (S1 > Svalues[order[-1]]):    # Try longer path along distance
                trial_2 = self.reflect(centroid, coords[order[-1]], trial=2)
                trial_2.checkLimits()
                S2 = self.computeS(trial_2)
                if (S2 > Svalues[order[-1]]):    # Try half the distance
                    trial_3 = self.reflect(centroid, coords[order[-1]], trial=3)
                    trial_3.checkLimits()
                    S3 = self.computeS(trial_3)
                    if (S3 > Svalues[order[-1]]):     # Shrink?
                        #self.delta_factor *= 2.0
                        #if n_contractions <= 2:
                        coords = self.contract(centroid, coords)
                        Svalues = []
                        for coord in coords:
                            coord.checkLimits()
                            Svalues.append(self.computeS(coord))
                            #print 'Contracted!'
                        #    n_contractions += 1
                        #else:
                        #    break
                    else:
                        coords[order[-1]] = trial_3
                        Svalues[order[-1]] = S3
                        #print 'Trial 3'
                else:
                    coords[order[-1]] = trial_2
                    Svalues[order[-1]] = S2
                    #print 'Trial 2'
            else:
                coords[order[-1]] = trial_1
                Svalues[order[-1]] = S1
                #print 'Trial 1'
        
        retval = self.findCentroid(coords)
        print numpy.mean(Svalues), numpy.std(Svalues)

        return retval

    def calc_initial_guess(self, features, weights):
        temps = []
        gravs = []
        Bs = []
        Ws = []
        for key in features.keys():
            temps.append(features[key]["T"])
            gravs.append(features[key]["G"])
            Bs.append(features[key]["B"])
            Ws.append(weights[key])

        retval = {"T":numpy.average(temps, weights=Ws), "G":numpy.average(gravs, weights=Ws), "B":numpy.average(Bs,
        weights=Ws)}

        if (2 in weights.keys()):
            if (weights[2] > 100.0):
                retval["G"] = features[2]["G"]

        return retval

    def fitSpectrum(self, wl, flux, error, plt, **kwargs):
        outfile = kwargs["outfile"]
        # Gets the initial guess coordinates for both features
        guess_coords = {}
        self.x_window = {}
        self.flat = {}
        self.z = {}
        self.interpolated_model = {}
        weights = {}

        for num in self.features.keys():
            feat = self.features[num]
            self.currFeat = num
            if (min(wl) < feat["xstart"]):
                x_window, flat, z = SEDTools.removeContinuum(wl, flux, error, feat["slope_start"], feat["slope_stop"],
                strongLines=feat["strongLines"], lineWidths=feat["lineWidths"], errors=True)

                self.x_window[num] = x_window
                self.flat[num] = flat
                self.z[num] = z
                self.interpolated_model[num] = {"T":0.0, "G":0.0, "B":0.0, "y_new":[]}

                x_sm, y_sm = self.readMOOGModel(4000.0, 400.0, 0.0)
                x_sm = x_sm/10000.0                # convert MOOG wavelengths to microns
                self.features[self.currFeat]["wl"] = x_sm
                
                kwargs["outfile"]=self.dataBaseDir+outfile+'_feat_'+str(self.features[self.currFeat]["num"])+'.dat'
                #kwargs["noBField"]=True
                guess_coords[num] = self.gridSearch(**kwargs)
                weights[num] = numpy.mean(flat/z)
                
        initial_guess = self.calc_initial_guess(guess_coords, weights)
        '''
        initial_guess["T"] = numpy.average([guess_coords[coord]["T"] for coord in guess_coords], weights=tempWeight)
        if (2 in guess_coords.keys() ):
            initial_guess["G"] = min(guess_coords[2]["G"], 500)
        else:
            initial_guess["G"] = numpy.mean([guess_coords[coord]["G"] for coord in guess_coords])
        initial_guess["B"] = numpy.mean([guess_coords[coord]["B"] for coord in guess_coords])
        '''
        # Calculate an initial guess for the veiling at 2.2 microns (feature 4)
        print "Guesses from Grid Search :", guess_coords
        print "Initial Guess :", initial_guess
        contLevels = {key:1.0 for key in guess_coords.keys()}
        veiling = 0.005
        init_guess = gridPoint(initial_guess, contLevels, veiling)
        #retval.append(initial_guess)
        first_pass = self.simplex(init_guess, plt, mode = 'CONTINUUM')
        x_sm = self.features[4]["wl"]
        self.currFeat = 4
        y_new = self.interpolatedModel(initial_guess["T"], initial_guess["G"], initial_guess["B"])

        new_wl = self.x_window[4] + self.features[4]["x_offset"]
        overlap = scipy.where( (new_wl > min(x_sm)) & (new_wl < max(x_sm)) )[0]

        synthetic_spectrum = self.binMOOGSpectrum(y_new, x_sm, new_wl[overlap])*contLevels[4]
        veiling = self.calcVeiling(self.flat[4][overlap], synthetic_spectrum, new_wl[overlap],self.features[4]["comparePoints"])
        best_coords = self.simplex(first_pass, plt, mode = 'LINES')
        #first_pass.TGB["B"] = 0.0
        #best_coords = self.simplex(first_pass, plt, mode = 'LINES', Fixed_B = True)
        self.floaters["dy"] = True
        self.saveFigures(best_coords, outfile=outfile)
        #self.saveFigures(best_coords, outfile=outfile+'_B=0')
        covariance = self.computeCovariance(best_coords)

        return best_coords, covariance

    def saveFigures(self, coords, **kwargs): 
        fig_width_pt = 246.0
        fig_width = 7.0  # inches
        inches_per_pt = 1.0/72.27
        pts_per_inch = 72.27
        golden_mean = (numpy.sqrt(5)-1.0)/2.0
        fig_height = fig_width*golden_mean
        fig_size = [fig_width, fig_height]
        params = {'backend' : 'ps',
          'axes.labelsize' : 12,
          'text.fontsize' : 12,
          'legend.fontsize' : 12,
          'xtick.labelsize' : 10,
          'ytick.labelsize' : 10,
          'text.usetex' : True,
          'figure.figsize' : fig_size}

        pyplot.rcParams.update(params)
        plotData = self.computeS(coords, returnSpectra = True)
        YSO_Name = kwargs["outfile"].replace('_', ' ')
        for num in plotData.keys():
            fig = pyplot.figure(0)
            pyplot.clf()
            plots = []
            plots.append(pyplot.plot(plotData[num]["wl"], plotData[num]["obs"], label='Observed', lw = 0.25, color='r'))
            plots.append(pyplot.plot(plotData[num]["wl"], plotData[num]["veiled"],label='Best Fit',lw = 0.25,color='b'))
            pyplot.xlabel(r'$\lambda$ ($\mu$m)')
            pyplot.ylabel(r'$F_{\lambda}$')
            pyplot.title(YSO_Name+' Feature :'+str(num))
            pyplot.legend( plots, ['Observed','Best Fit'], 'best')
            pyplot.savefig('plots/'+kwargs["outfile"]+'_f'+str(num)+'.eps')

    def prelimSearch(self, wl, flux, error, plt, **kwargs):   # wl in microns
        retval = []
        outfile = kwargs["outfile"]
        for num in self.features.keys():
            feat = self.features[num]
            self.delta_factor = 1.0
            self.currFeat = num
            if ( min(wl) < feat["xstart"] ):
                #chisq = numpy.zeros([len(feat["TandGandB"][0]), len(self.x_offsets), len(self.y_offsets), len(self.veilings)])
                x_window, flat, z = SEDTools.removeContinuum(wl, flux, error, feat["slope_start"], feat["slope_stop"],strongLines=feat["strongLines"], lineWidths=feat["lineWidths"], errors=True)
                
                self.x_window = x_window
                self.flat = flat
                self.z = z
                
                if kwargs["mode"] == 'PREP':
                    coordinates = []
                    T_initial_guess = 4000.0
                    G_initial_guess = 400.0
                    B_initial_guess = 1.0
                    dy_initial_guess = 1.0
                    
                    T_guess = T_initial_guess
                    G_guess = G_initial_guess
                    B_guess = B_initial_guess
                    x_sm, y_sm = self.readMOOGModel(T_guess, G_guess, B_guess)
                    x_sm = x_sm/10000.0                # convert MOOG wavelengths to microns
                    minx = min(x_sm)
                    maxx = max(x_sm)
                    self.features[self.currFeat]["wl"] = x_sm
                    
                    
                    dy_guess = dy_initial_guess
                    self.findWavelengthShift(x_window, flat, x_sm, y_sm)
                    dx_guess = self.features[self.currFeat]["x_offset"]
                    
                    #Calculate the initial guess for the wavelength shift
                    new_wl = x_window+dx_guess
                    overlap = scipy.where( (new_wl > minx) & (new_wl < maxx) )[0]
                    
                    synthetic_spectrum = self.binMOOGSpectrum(y_sm, x_sm, new_wl[overlap])

                    
                    #Calculate the initial guess for the veiling
                    #r_initial_guess = self.calcVeiling(flat[overlap], synthetic_spectrum, new_wl[overlap], feat["comparePoints"])
                    kwargs["outfile"]=self.dataBaseDir+outfile+'_feat_'+str(self.features[self.currFeat]["num"])+'.dat'
                    if not(os.path.exists(kwargs["outfile"])):
                        guess_coords = self.gridSearch(plt=plt,**kwargs)

