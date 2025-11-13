#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: /src/athena_planner/visualization/make_results_plot.py
# Project: ARES-Print-Planner
# Created Date: Wednesday, November 12th 2025, 4:08:55 pm
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

def make_results_plots(request:PlanRequest):
    results = request.analysis_results

    best_results = np.array([np.min(results[:i+1]) for i in range(len(results))])

    n_iter = len(results) # will this work for the first call?
    images = []

    if n_iter >=1:
        for i in range(n_iter):
            fig,ax = plt.subplots(figsize=(6.4,3.6))
            ax.set_xlim(-1,n_iter+1)
            ax.set_ylim(-0.5,1)
            ax.set_xticks(np.arange(0,n_iter))
            ax.set_yticks([np.max(results)*1.05,np.min(results)*.95])
            ax.set_yticklabels([r'$x_{min}$','',r'$x_{max}$'])
            ax.set_xlabel('Iteration',fontsize=12,fontweight='bold')
            ax.set_ylabel('Objective Score',fontsize=12,fontweight='bold')

            ax.plot(np.arange(0,i),results[:i+1],label='Current Score',marker='o')
            ax.plot(np.arange(0,i),best_results[:i+1],label='Best Score',marker='D')

            fig.set_dpi(300)
            fig.tight_layout()
            fig.canvas.draw()
            img = np.array(fig.canvas.buffer_rgba())
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            images.append(img)

    return images 