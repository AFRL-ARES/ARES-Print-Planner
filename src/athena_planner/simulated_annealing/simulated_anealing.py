import numpy as np
from PyAres import AresPlannerService, PlanRequest, PlanResponse, AresDataType

def perturb_parameter(parameter_val, min_val, max_val, std):
    new_settings = []

    for num, parameter in enumerate(settings[0]):
        while True:
            new_parameter = np.random.normal(parameter, stds[num])
            if parameter_ranges[num][0] <= new_parameter <= parameter_ranges[num][1]:
                new_settings.append(new_parameter)
                break  
            else:
                continue
    return np.array([new_settings])

def find_matching_setting(param_name: str, settings: Dict[str, any]) -> int:
   param_name = param_name.lower()

   if("bed" in param_name):
      return settings["Bed Temp Standard Deviation"]
   
   if("nozzle" in param_name):
      return settings["Nozzle Temp Standard Deviation"]
   
   if("extrusion" in param_name):
      return settings["Extrusion Rate Mod Standard Deviation"]
   
   if("speed" in param_name):
      return settings["Speed Mod Standard Deviation"]
   
   if("retraction" in param_name):
      return settings["Retraction Length Standard Deviation"]
   
   if("acceleration" in param_name):
      return settings["Acceleration Mod Standard Deviation"]
   
   if("start_temperature" in param_name):
      return settings["Simulated Annealing Starting Temperature"]
   
   if("cooling_rate" in param_name)
      return settings["Simulated Annealing Cooling Rate"]

   

def simulated_annealing_planner(request: PlanRequest) -> PlanResponse:
   """
   Graig's Simulated annealing planner:
   - Summary of Planning Logic (for itteration # N>0)
      1. Perterb the current best set of parameters using a normal distrbution with a user specified set of standard devations for each parameter
      2. Print a new iteration and obtain a new objective function score.  
      3. 
      
   """
   # Graig's simulated annealing planner:
   # For each itteration, the planner perterbs the input settings for the 3d print and

   current_names = [] 
   current_values = []
   parameter_names = []
   parameter_values = []
   best_result_index = -1

   # Calculate the temperature for simulated annealing algrithinm   
   if len(request.analysis_results) != 0:
      N_iter = len(request.analysis_results)
      start_temp = find_matching_setting("start_temperature", request.settings)
      cooling_rate = find_matching_setting("cooling_rate", request.settings)
      anneal_temp = np.round(start_temp*np.exp(-cooling_rate*N_iter),3)
      
      # The nomenclature here is a bit odd  because we're adapting from how graig wrote his initial code
      # Here the most recent result is the candidate set of conditions
      
      candidate_objective_val  = request.analysis_results[-1]
      current_objective_val = request.analysis_results[-2]
      

      best_objective_val = max(request.analysis_results)
      best_result_index = request.analysis_results.index(max(request.analysis_results))

      delta = current_objective_val - candidate_objective_val # The change in the objective function from the last run
      anneal_criteria = np.exp(delta/anneal_temp) > np.random.uniform(0, 1)
      # Since a low score is better, a positive delta means that the print improved

   for parameter in request.parameters:
      while True:
         if len(parameter.param_history) == 0: # For the first loop
            parameter_names.append(parameter.name)
            parameter_values.append(parameter.maximum_value)
            break
         else:
            # Get the standard deviation that will be used to perturb each paramter
            deviation = find_matching_setting(parameter.name, request.settings)
            old_value = parameter.param_history[best_result_index] # or -1?
            new_value = np.random.normal(old_value.planned_value,deviation)
            if(parameter.minimum_value <= new_value <= parameter.maximum_value):
              parameter_names.append(parameter.name)
              parameter_values.append(round(new_value))
              break
            else:
               continue

   if delta > 0 or anneal_criteria:
      pass
      if current




   return PlanResponse(parameter_names, parameter_values)



def simulated_annealing(max_iterations, start_temp, eta, stds, resume_filename=None, 
                        initial_settings = None, parameter_ranges=[(160, 240), (25, 100), (20, 180), 
                               (0, 100), (0.8, 1.6)]):
    
    



    if resume_filename:
        df = pd.read_csv(resume_filename)
        last_experiment = df.iloc[-1]
        best_solution = np.array([last_experiment.iloc[0:5].to_numpy()])
        best_value = last_experiment.iloc[5]
        current_solution = np.array([last_experiment.iloc[6:11].to_numpy()])
        current_value = last_experiment.iloc[11]
        temperature = last_experiment.iloc[12]
        temperature *= 1 - eta
        iteration = int(last_experiment.iloc[13]) + 1         
    else:
        if initial_settings is None:
            iteration = 0
            best_solution = np.array([[np.random.uniform(min_val, max_val) for min_val, max_val in parameter_ranges]])
            best_value = objective_function(best_solution, iteration)
            current_solution = best_solution
            current_value = best_value
            temperature = start_temp
            data = list(best_solution[0]) + [best_value] + list(current_solution[0]) + [current_value] +[temperature] + [iteration]
            df = pd.DataFrame([data])
            df.to_csv('sa_data.csv', index=False)
            iteration += 1
        else:    
            iteration = 0
            best_solution = initial_settings
            best_value = objective_function(best_solution, iteration)
            current_solution = best_solution
            current_value = best_value
            temperature = start_temp
            data = list(best_solution[0]) + [best_value] + list(current_solution[0]) + [current_value] +[temperature] + [iteration]
            df = pd.DataFrame([data])
            df.to_csv('sa_data.csv', index=False)
            iteration += 1
        
    while iteration <= max_iterations:
        
        new_solution = perturb(current_solution, parameter_ranges, stds)
        new_value = objective_function(new_solution, iteration)

        delta = current_value - new_value

        if delta > 0 or math.exp(delta / temperature) > np.random.uniform(0, 1):
            current_solution, current_value = new_solution, new_value

            if current_value < best_value:
                best_solution, best_value = current_solution, current_value

        data = list(best_solution[0]) + [best_value] + list(current_solution[0]) + [current_value] +[temperature] + [iteration]
        df.loc[len(df)] = data
        df.to_csv('sa_data.csv', index=False)
        iteration += 1
        temperature *= 1 - eta

    return best_solution, best_value