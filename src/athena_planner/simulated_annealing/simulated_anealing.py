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
from PyAres import PlanRequest, PlanResponse
from typing import Any, List

root_condition_index = -1
root_condition_dict = {}
last_condition_dict = {}
last_result_value = -1.0
root_condition_result_value = -1.0
total_iterations_completed = 0

def find_matching_setting(param_name: str, settings: dict[str, Any]) -> int:
   #TODO Is there a way for ARES OS to supply some or all of this info so we don't need to hard code it?
   maping_dict = {'bed':"Bed Temp Standard Deviation",
                  'nozzle temp':"Nozzle Temp Standard Deviation",
                  'extrusion':'Extrusion Rate Mod Standard Deviation',
                  'speed':"Speed Mod Standard Deviation",
                  'retraction':'Retraction Length Standard Deviation',
                  'acceleration':'Acceleration Standard Deviation',
                  'fan speed mod':'Fan Speed Mod Standard Deviation',
                  'start_temperature':'Simulated Annealing Starting Temperature',
                  'cooling_rate':'Simulated Annealing Cooling Rate',
                  'retain_historical_context':'Retain Historical Context'}
   param_name = param_name.lower()
   if param_name in maping_dict:
      return settings[maping_dict[param_name]]
   
   else:
      return -1

def get_parameter_data(request: PlanRequest) -> tuple[list,list,list[tuple],list]:
   parameter_names = []
   parameter_values = []
   parameter_bounds = []
   parameter_deviations = []
   for parameter in request.parameters:
      parameter_names.append(parameter.name)
      parameter_bounds.append((parameter.minimum_value,parameter.maximum_value)) # order is (min, max)
      parameter_deviations.append(find_matching_setting(parameter.name, request.settings))
      if len(parameter.param_history) == 0:
         # TODO Do we need logic here? If planning is called after the first experiment the length of the
         # parameter history should always be at least 1?
         parameter_values.append(parameter.maximum_value)
      else:
         parameter_values.append(root_condition_dict[parameter.name])

   return parameter_names, parameter_values, parameter_bounds, parameter_deviations

def get_historical_param_data(request: PlanRequest) ->  tuple[list,list,list[tuple],list]:
   parameter_names = []
   parameter_values = []
   parameter_bounds = []
   parameter_deviations = []
   for parameter in request.parameters:
      parameter_names.append(parameter.name)
      parameter_bounds.append((parameter.minimum_value,parameter.maximum_value))
      parameter_deviations.append(find_matching_setting(parameter.name, request.settings))
      if root_condition_dict.get(parameter.name):
         parameter_values.append(root_condition_dict[parameter.name])
      else:
         print(f"Error! Tried finding historical data, but none existing for parameter {parameter.name}. Planner cannot plan!")
   
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
         new_val = np.random.normal(old_val.planned_value,dev)
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
   # These values allow the planner to maintain context beyond the scope of a single campaign
   global root_condition_dict
   global last_result_value
   global root_condition_result_value

   N_iter = len(request.analysis_results)
   parameter_names : List[str] = []
   new_test_condition : List[float] = []
   
   # Calculate the temperature for simulated annealing algorithm

   retain_historical_context = find_matching_setting("retain_historical_context", request.settings)

   if N_iter == 0:
      # If the user chose to retain historical context, we grab the old values, if applicable
      if retain_historical_context and root_condition_dict:
         #TODO: Fix
         #check_and_update_root(request, retain_historical_context)
         # We retained historical context successfully, use those values...
         parameter_names, root_condition_values, bounds, deviations = get_historical_param_data(request)
         new_test_condition = perturb_parameters(parameter_names, root_condition_values, bounds, deviations)

      else:
         for param in request.parameters:
            parameter_names.append(param.name)
            
            if isinstance(param.initial_value, float):
               new_test_condition.append(param.initial_value)
               root_condition_dict.update({param.name: param.initial_value})

            else:
               print("Problem trying to access intial value! Value was not of type float.")
               new_test_condition.append(0.0)

      return PlanResponse(parameter_names=parameter_names, parameter_values=new_test_condition)

   elif N_iter == 1:
      if retain_historical_context:
         check_and_update_root(request, retain_historical_context)

         for param in request.parameters:
            root_condition_dict.update({param.name: param.param_history[0]})
            last_condition_dict.update({param.name: param.param_history[0]})

      
      parameter_names, root_condition_values, bounds, deviations = get_parameter_data(request)
      new_test_condition = perturb_parameters(parameter_names, root_condition_values, bounds, deviations)
      return PlanResponse(parameter_names, new_test_condition)
   
   else:
      check_and_update_root(request, retain_historical_context)
      parameter_names, root_condition_values, bounds, deviations = get_parameter_data(request)
      new_test_condition = perturb_parameters(parameter_names, root_condition_values, bounds, deviations)

      return PlanResponse(parameter_names, new_test_condition)
   

def check_and_update_root(request: PlanRequest, retain_historical_context):
   """Updates the root value if applicable, as well as the last received result value"""
   global root_condition_result_value
   global last_result_value
   global total_iterations_completed

   start_temp = find_matching_setting("start_temperature", request.settings)
   cooling_rate = find_matching_setting("cooling_rate", request.settings)
   anneal_temp = np.round(start_temp*np.exp(-cooling_rate*total_iterations_completed),3)

   # Compares the analyzer values to see if the new condition is better than the old root condtion
   test_conditon_value = request.analysis_results[-1]
   last_result_value = request.analysis_results[-1]
   delta = root_condition_result_value - test_conditon_value
   delta_criteria = delta > 0

   # Sample from a pseudo-boltzman distribution to see if we update the root condition even if the score is lower
   # This can potentially kick the planner out of a local minimum.
   annealing_criteria = np.exp(delta/anneal_temp) > np.random.uniform(0, 1)

   if delta_criteria or annealing_criteria:
      root_condition_result_value = request.analysis_results[-1]
      #root_condition_index = N_iter-1
      
      if retain_historical_context:
         root_condition_result_value = request.analysis_results[-1]
         for param in request.parameters:
            root_condition_dict.update({param.name: param.param_history[-1]})
            last_condition_dict.update({param.name: param.param_history[-1]})

   # This means we need to check for an update between campaigns
   # else: 
   #    test_conditon_value = last_result_value
