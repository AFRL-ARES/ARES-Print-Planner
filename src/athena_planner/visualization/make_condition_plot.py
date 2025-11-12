#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: /src/athena_planner/visualization/make_condition_plot.py
# Project: ARES-Print-Planner
# Created Date: Wednesday, November 12th 2025, 10:45:39 am
# Author(s): Arthur W. N. Sloan
# -----
# MIT License
# 
# Copyright (c) 2025 AFRL-ARES
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# 
###

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from PyAres import PlanRequest
import cv2
import itertools

matplotlib.use('Agg')
marker_cycle = itertools.cycle(('o','+','.','*','^','s','x','D')) 
def make_condition_plots(request:PlanRequest):
    paparameter_names = []
    parameter_values = []
    normalized_values = []


    for parameter in request.parameters:
        paparameter_names.append(parameter.name)
        bounds = (parameter.minimum_value,parameter.maximum_value)
        param_vals = []
        for iteration in parameter.param_history:
            param_vals.append(iteration.planned_value)
        param_vals = np.array(param_vals)
        norm_vals = (param_vals - bounds[0]) / (bounds[1]-bounds[0])
        parameter_values.append(param_vals)
        normalized_values.append(norm_vals)

    parameter_values = np.array(parameter_values)
    normalized_values = np.array(normalized_values)
    n_params = len(request.parameters)
    n_iter = parameter_values.shape[1] # check this, indivicual itterations should be the columns?

    #We're going to make a plot for each itteration

    images = []
    for i in range(n_iter):
        fig,ax = plt.subplots()
        ax.set_xlim(-1,n_iter+1)
        ax.set_ylim(-0.5,1)
        ax.set_xticks(np.arange(0,n_iter))
        ax.set_yticks([0,0.5,1])
        ax.set_yticklabels([r'$x_{min}$','',r'$x_{max}$'])
        ax.set_xlabel('Iteration',fontsize=12,fontweight='bold')
        ax.set_ylabel('Parameter Value',fontsize=12,fontweight='bold')
        for j, p in enumerate(paparameter_names):
            ax.plot(np.arange(0,i),normalized_values[j,:i+1],label=p,marker=next(marker_cycle))
        
        fig.set_dpi(300)
        fig.tight_layout()
        fig.canvas.draw()
        img = np.array(fig.canvas.buffer_rgba())
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        images.append(img)
    
    # For a bit of a different style 
    highlight_images = []

    for i in range(n_iter):
        fig,ax = plt.subplots()
        ax.set_xlim(-1,n_iter+1)
        ax.set_ylim(-0.5,1)
        ax.set_xticks(np.arange(0,n_iter))
        ax.set_yticks([0,0.5,1])
        ax.set_yticklabels([r'$x_{min}$','',r'$x_{max}$'])
        ax.set_xlabel('Iteration',fontsize=12,fontweight='bold')
        ax.set_ylabel('Parameter Value',fontsize=12,fontweight='bold')
        for j, p in enumerate(paparameter_names):
            marker = next(marker_cycle)
            l = ax.plot(np.arange(0,n_iter),normalized_values[j,:],label=p,marker=marker,alpha=0.5)
            color = l[0].get_color()
            ax.plot(i, normalized_values[j,i], color=color, marker=marker)
        
        fig.set_dpi(300)
        fig.tight_layout()
        fig.canvas.draw()
        img = np.array(fig.canvas.buffer_rgba())
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        highlight_images.append(img)

    return images, highlight_images




