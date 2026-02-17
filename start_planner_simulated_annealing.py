#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: /start_planner_simulated_annealing.py
# Project: ARES-Print-Planner
# Created Date: Monday, October 27th 2025, 1:50:01 pm
# Author(s): Nick Kleiner, Arthur W. N. Sloan
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

from PyAres import AresPlannerService, AresDataType
from src.athena_planner.simulated_annealing import simulated_annealing_planner

if __name__ == "__main__":
  name = "Simulated Annealing 3D Print Planner"
  description = "A PyAres implementation of Graig Ganitano's Simulated Annealing 3D Printing Planner, see DOI: 10.1007/s40964-023-00480-1"
  version = "1.1.0"
  planner = AresPlannerService(simulated_annealing_planner,
                               name,
                               description,
                               version, port=8002)

  #Mark that the planner supports numbers
  planner.add_supported_type(AresDataType.NUMBER)
  
  #Standard Deviation Settings
  planner.add_setting("Nozzle Temp Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Bed Temp Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Extrusion Rate Mod Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Speed Mod Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Retraction Length Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Acceleration Mod Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Fan Speed Mod Standard Deviation", AresDataType.NUMBER)

  #Other Settings
  planner.add_setting("Simulated Annealing Starting Temperature", AresDataType.NUMBER,optional=False)
  planner.add_setting("Simulated Annealing Cooling Rate", AresDataType.NUMBER,optional=False)
  planner.add_setting("Retain Historical Context", AresDataType.BOOLEAN) #If enabled, will continue using the best data from the previous campaigns to influence it's current decisions
  planner.add_setting("Verbose Output", AresDataType.BOOLEAN) #If enabled, will print out more detailed information during planning
  planner.add_setting("RNG Seed", AresDataType.NUMBER,optional=True) # Sets a seed for the random number generator
  planner.start()