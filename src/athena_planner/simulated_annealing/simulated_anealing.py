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
from time import time
#%% persistent plannervariables, these are retained between calls to the planner service
root_condition_index = -1
root_condition_dict = {}
last_condition_dict = {}
last_result_value = -1.0
root_condition_result_value = -1.0
total_iterations_completed = 0
rand_gen = -1

'''
An implementation of Graig Ganitano's Simulated Annealing Planner for 3D Printing.
DOI: 10.1007/s40964-023-00480-1

Planner theory of operation:
   The goal of the planner to is minimize the objective score of the process.

   The basic method of operation to acheive this goal is to randomly perturb 
   each parameter by sampling from a normal distribution centered on the current 
   value with a user specified standard deviation. 

   The planner operates from a "root condition" which serves as the current value from which the 
   "test condition" is derived via the random perturbation. After each experimental iteration
   if the objective score for the test conditon is lower (better) than the previous best objective score, 
   the test condition becomes the new root condition. This will tend to cause the planner to find conditions 
   that minimize the objective score in the vicinity of its root condition.

   In the event that the objective score is higher (worse), the planner checks the following inquality:

   exp((best score - test score)/T) > uniform(0, 1)

   Where T is the "temperature" of the simulation. If the inquality evaluates to true, the root condition 
   is updated to the test condition regardles of the score, while if it is false the root condition is 
   retained. This approach helps kick the planner out of local minima in the process response surface. 

   The temperature of the simulation determines how frequently this kick occurs, with higher temperatures producing 
   results closer to a random walk, and lower temperatures behaving more like a hill climbing/desecent approach. Within
   the planner, this temperature is controlled by an initial temperature setting and a cooling rate, which causes the simulation 
   temperature to decay as: T(N_itter) = T_0*exp(-<decay rate>*N_iter), and thus decreases the randomness of the planner over time.

   Note that this is a pure simulated annealing planner, and there is no logic to force the planner to backtrack to 
   known good conditions after the root conditions is updated by the annealing criteria.

Planner settings:
   This planner has the following settigns that must be defined when starting a PyAres planner service. 
   There is string matching to associate the correct setting with the correct parameter, so names must be exact.
      1. Bed Temp Standard Deviation
      2. Nozzle Temp Standard Deviation
      3. Extrusion Rate Mod Standard Deviation
      4. Speed Mod Standard Deviation
      5. Retraction Length Standard Deviation
      6. Acceleration Standard Deviation
      7. Fan Speed Mod Standard Deviation
      8. Simulated Annealing Starting Temperature,
      9. Simulated Annealing Cooling Rate
      10. Retain Historical Context
      11. RNG Seed

'''
#%% Main planner function called by planner service
def simulated_annealing_planner(request: PlanRequest) -> PlanResponse:
   """
   PyAres-ified version of Graig's Simulated annealing planner:
   """
   # Graig's simulated annealing planner:
   # For each itteration, the planner perterbs the input settings for the 3d print and
   # These values allow the planner to maintain context beyond the scope of a single campaign.
   # Context is reset if the planner service is restarted.

   global root_condition_dict
   global last_result_value
   global root_condition_result_value
   global rand_gen
   global total_iterations_completed

   verbose = bool(find_matching_setting("verbose output", request.settings))
   N_iter = len(request.analysis_results)
   retain_historical_context = bool(find_matching_setting("retain_historical_context", request.settings))
   rng_seed = find_matching_setting("rng_seed", request.settings)

   if verbose:
      print(f"--- Iteration #: {N_iter} ---")
      if retain_historical_context:
         print("Retaining Historical Context is ENABLED")
      else:
         print("Retaining Historical Context is DISABLED")
      if root_condition_dict:
         print("The current root condition is:")
         for key, value in root_condition_dict.items():
            print(f"\tParam: {key}, Value: {value}")
         print(f'\tWith Objective Score: {root_condition_result_value}')

   parameter_names : List[str] = []
   new_test_condition : List[float] = []
   
   # Establish or retrieve the random number generator
   if rand_gen == -1:
      if rng_seed is not None and rng_seed >0:
         seq = np.random.SeedSequence(int(rng_seed))

         rng = np.random.default_rng(int(rng_seed))
      else:
         rng_seed = int(time())
         seq = np.random.SeedSequence(rng_seed)
         
      rng = np.random.default_rng(seq)
      if verbose:
         print("No existing Random Number Generator detected, creating new one with seed:", rng_seed)
      rand_gen=rng
   else:
      rng = rand_gen

   if N_iter == 0:
      # If the user choses to retain historical context, we grab the old values, if applicable
      if retain_historical_context and root_condition_dict:
         #TODO: Fix
         # We retained historical context successfully, use those values...
         parameter_names, root_condition_values, bounds, deviations, success = get_historical_param_data(request)
         if success: # if there is a mismatch between the reqeust and the historical data, we fallback to using the initial values to avoid crashing.
            new_test_condition = perturb_parameters(parameter_names, root_condition_values, bounds, deviations, rng)
         else:
            if verbose:
               print("Failed to retrieve historical context, using initial values.")
            for param in request.parameters:
               parameter_names.append(param.name)
               
               if isinstance(param.initial_value, float):
                  new_test_condition.append(param.initial_value)
                  root_condition_dict.update({param.name: param.initial_value})

               else:
                  print("Problem trying to access intial value! Value was not of type float.")
                  new_test_condition.append(0.0)
      else:
         if verbose:
            print("First iteration, using initial values.")
         for param in request.parameters:
            parameter_names.append(param.name)
            
            if isinstance(param.initial_value, float):
               new_test_condition.append(param.initial_value)
               root_condition_dict.update({param.name: param.initial_value})

            else:
               print("Problem trying to access intial value! Value was not of type float.")
               new_test_condition.append(0.0)

   elif N_iter == 1: # On the second iteration, may or may not have meaninful historical data to compare to depending on if historical context exists.
      if retain_historical_context: # If there is hisorical context, we use the normal check & update root locgic
         try:
            check_and_update_root(request, retain_historical_context, verbose, rng)
         except Exception as e:
            print(f"Error updating root conditon on second itteration - {e}")
      else: # If there is no historical context, we just use the first itteration as the root condition without comparison, and then perturb from there on the next itteration
         for param in request.parameters:
            root_condition_dict.update({param.name: param.param_history[0].planned_value})
            last_condition_dict.update({param.name: param.param_history[0].planned_value})
            root_condition_result_value = request.analysis_results[0]
            last_result_value = request.analysis_results[0]
            if verbose:
               print("Only one itteration completed, using it as the root conditon.")
               print("The new root condition is:")
               for key, value in root_condition_dict.items():
                  print(f"\tParam: {key}, Value: {value}")
               print(f'\tWith Objective Score: {root_condition_result_value}')

      if verbose:
         print("Perturbing from root condition to get new test condition.")

      parameter_names, root_condition_values, bounds, deviations = get_parameter_data(request)
      new_test_condition = perturb_parameters(parameter_names, root_condition_values, bounds, deviations, rng)
   
   else:
      try:
         check_and_update_root(request, retain_historical_context, verbose, rng)
      except Exception as e:
         print(f"Error updating root conditon - {e}")
      
      if verbose:
         print("The new root condition is:")
         for key, value in root_condition_dict.items():
            print(f"\tParam: {key}, Value: {value}")
         print(f'\tWith Objective Score: {root_condition_result_value}')
         print("Perturbing from root condition to get new test condition.")

      parameter_names, root_condition_values, bounds, deviations = get_parameter_data(request)
      new_test_condition = perturb_parameters(parameter_names, root_condition_values, bounds, deviations,rng)

   if verbose:
      print("Proposed new test condition:")
      for n,v in zip(parameter_names, new_test_condition):
         print(f"\tParam: {n}, Value: {v}")
      print(f"-------------------------")
      total_iterations_completed += 1
      
   return PlanResponse(parameter_names=parameter_names, parameter_values=new_test_condition)

   

def check_and_update_root(request: PlanRequest, retain_historical_context:bool, verbose=False, rng=np.random.default_rng()) -> None:
   """Updates the root value if applicable, as well as the last received result value"""
   global root_condition_result_value
   global last_result_value
   global total_iterations_completed
   global root_condition_dict
   global last_condition_dict
   # 

   start_temp = find_matching_setting("start_temperature", request.settings)
   cooling_rate = find_matching_setting("cooling_rate", request.settings)
   anneal_temp = np.round(start_temp*np.exp(-cooling_rate*total_iterations_completed),3)
   if verbose:
      print(f"Temperature for simulated annealing: {anneal_temp}")

   # Compares the analyzer values to see if the new condition is better than the old root condtion
   test_conditon_value = request.analysis_results[-1]
   last_result_value = request.analysis_results[-1]
   delta = root_condition_result_value - test_conditon_value
   if verbose:
      print(f"Root Condition Score: {root_condition_result_value}")
      print(f"Test Condition Score: {test_conditon_value}")

   # This is a minimization planner, so a better results is a lower score
   delta_criteria = delta > 0

   # Sample from a pseudo-boltzman distribution to see if we update the root condition even if the score is lower
   # This can potentially kick the planner out of a local minimum.
   annealing_criteria = np.exp(delta/anneal_temp) > rng.uniform(0, 1)
   if verbose:
      print(f"Delta Criteria Met: {delta_criteria}")
      print(f"Annealing Criteria Met: {annealing_criteria}")

   if delta_criteria or annealing_criteria:
      if verbose:
         print("Updating root condition to the test condition.")
      root_condition_result_value = request.analysis_results[-1]

      for param in request.parameters:
         root_condition_dict.update({param.name: param.param_history[-1].planned_value})
         last_condition_dict.update({param.name: param.param_history[-1].planned_value})
   elif root_condition_result_value == -1: 
      if verbose:
         print("No Score for existing root condition. Updating root condition to the test condition.")
      root_condition_result_value = request.analysis_results[-1]

      for param in request.parameters:
         root_condition_dict.update({param.name: param.param_history[-1].planned_value})
         last_condition_dict.update({param.name: param.param_history[-1].planned_value})
   else:
      if verbose:
         print("Retaining existing root condition.")
      # Root condition remains the same, just update the last condition
      for param in request.parameters:
         last_condition_dict.update({param.name: param.param_history[-1]})

#%% 
def find_matching_setting(param_name: str, settings: dict[str, Any]):
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
                  'retain_historical_context':'Retain Historical Context',
                  'rng_seed':'RNG Seed',
                  'verbose output':'Verbose Output'}
   if param_name.lower() in maping_dict:
      value = settings[maping_dict[param_name.lower()]]
   else:
      try:
         value = settings[param_name]
      except:
         value = -1 
   return value

def get_parameter_data(request: PlanRequest) -> tuple[list,list,list[tuple],list]:
   # Grabs the parameter names, current values, bounds, and deviations to use for the perturbation
   # Since the perturbation is based on the root conditon 
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

def get_historical_param_data(request: PlanRequest) ->  tuple[list,list,list[tuple],list,bool]:
   global root_condition_dict
   parameter_names = []
   parameter_values = []
   parameter_bounds = []
   parameter_deviations = []
   missing_data = False
   for parameter in request.parameters:
      parameter_names.append(parameter.name)
      parameter_bounds.append((parameter.minimum_value,parameter.maximum_value))
      parameter_deviations.append(find_matching_setting(parameter.name, request.settings))
      if root_condition_dict.get(parameter.name):
         parameter_values.append(root_condition_dict[parameter.name])
      else:
         missing_data = True
      
      if missing_data:
         print('Warning, the requested parameters and historical data do not fully align.')
         print(f'\tRequest parameters: {', '.join(parameter_names)}')
         print(f'\tHistorical parameters: {', '.join(root_condition_dict.keys())}')
         print('Proceeding with new values for missing parameters, but this may lead to suboptimal results.')

   return parameter_names, parameter_values, parameter_bounds, parameter_deviations, not missing_data
      

def perturb_parameters(names: list, condition: list, bounds:list[tuple], deviations:list, rng:np.random.Generator) -> list: 
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
         new_val = rng.normal(old_val,dev)
         if (min_val <= new_val <= max_val):
            new_condition.append(new_val)
            break
         else:
            continue
   return new_condition