#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: /src/athena_planner/simulated_annealing/simulated_anealing.py
# Project: ARES-Print-Planner
# Created Date: Monday, October 27th 2025, 1:54:16 pm
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
from PyAres import AresPlannerService, PlanRequest, PlanResponse, AresDataType
from typing import Any

def find_matching_setting(param_name: str, settings: dict[str, Any]) -> int:
   #TODO Is there a way for ARES OS to supply some or all of this info so we don't need to hard code it?
   maping_dict = {'bed':"Bed Temp Standard Deviation",
                  'nozzle':"Nozzle Temp Standard Deviation",
                  'extrusion':'Extrusion Rate Mod Standard Deviation',
                  'speed':"Speed Mod Standard Deviation",
                  'retraction':'Retraction Length Standard Deviation',
                  'acceleration':'Retraction Length Standard Deviation',
                  'start_temperature':'Simulated Annealing Starting Temperature',
                  'cooling_rate':'Simulated Annealing Cooling Rate'}
   param_name = param_name.lower()
   if param_name in maping_dict:
      return settings[maping_dict[param_name]]

def get_parameter_data(request: PlanRequest,idx: int) -> tuple[list,list,list[tuple],list]:
   parameter_names = []
   parameter_values = []
   parameter_bounds = []
   parameter_deviations = []
   for parameter in request.parameters:
      parameter_names.append(parameter.name)
      parameter_bounds.append((parameter.minimum_value,parameter.maximum_value)) # order is (min, max)
      parameter_deviations.append(find_matching_setting(parameter.name, request.settings))
      if len(parameter.param_history) == 0: # For the first loop ?
         # TODO Do we need logic here? If planning is called after the first experiment the length of the
         # parameter history should always be at least 1?
         parameter_values.append(parameter.maximum_value)
      else:
         parameter_values.append(parameter.param_history[idx].planned_value) # Would we want to do planned or achieved value here?
   return parameter_names, parameter_values, parameter_bounds, parameter_deviations

def perturb_parameters(names: list, condition: list, bounds:list[tuple], deviations:list) -> list: 
   # Randomly perturb the values of a condtion given lists of the 
   # parameter names, the starting paramter values, allowed bounds (min, max), 
   # and the distribution standard deviations 
   new_condition = []
   for i, _ in enumerate(names):
      old_val = condition[i]
      dev = deviations[i]
      min_val = bounds[i][0]
      max_val = bounds[i][1]
      while True:
         new_val = np.random.normal(old_val,dev)
         if (min_val <= new_val <= max_val):
            new_condition.append(new_val)
            break
         else:
            continue
   return new_condition

def simulated_annealing_planner(request: PlanRequest) -> PlanResponse:
   """
   PyAres-ified Graig's Simulated annealing planner:
      
   """
   # Graig's simulated annealing planner:
   # For each itteration, the planner perterbs the input settings for the 3d print and
   N_iter = len(request.analysis_results)
   # Calculate the temperature for simulated annealing algrithinm   
   if len(request.analysis_results) != 0:
      
      start_temp = find_matching_setting("start_temperature", request.settings)
      cooling_rate = find_matching_setting("cooling_rate", request.settings)
      anneal_temp = np.round(start_temp*np.exp(-cooling_rate*N_iter),3)
      root_condition_index = -1 # TODO Put something real here once we figure out how best to implement it
   else: # Do we want logic supporting calling the planner before the first experiment?
      pass

   if N_iter == 1:
      pass
   else:
      # Compares the analyzer values to see if the new condition is better than the old root condtion)
      test_conditon_value = request.analysis_results[-1]
      root_condition_value = request.analysis_results[root_condition_index]
      delta = root_condition_value - test_conditon_value
      delta_criteria = delta > 0

      # Sample from a pseudo-boltzman distribution to see if we update the root condition even if the score is lower
      # This can potentially kick the planner out of a local minimum.
      annealing_criteria = np.exp(delta/anneal_temp) > np.random.uniform(0, 1)

      if delta_criteria or annealing_criteria:
         root_condition_index = N_iter-1 # TODO how do we save this out to ARES OS for it to be avialible the next time the planner is called

      parameter_names, root_condition_values, bounds, deviations = get_parameter_data(request,root_condition_index)

      new_test_condition = perturb_parameters(parameter_names, root_condition_values, bounds, deviations)

   return PlanResponse(parameter_names, new_test_condition)