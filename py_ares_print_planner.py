from PyAres import AresPlannerService, PlanRequest, PlanResponse, AresDataType
from typing import Dict
import numpy as np

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
   

def Plan(request: PlanRequest) -> PlanResponse:
   parameter_names = []
   parameter_values = []
   best_parameter_set_index = -1

   if len(request.analysis_results) != 0:
      best_parameter_set_index = request.analysis_results.index(max(request.analysis_results))

   for parameter in request.parameters:

      while True:
         if len(parameter.param_history) == 0:
            parameter_names.append(parameter.name)
            parameter_values.append(parameter.maximum_value)
            break
          
         else:
            deviation = find_matching_setting(parameter.name, request.settings)
            #By default, this value is -1 so we'll either get the settings that achieved the best value so far, or we'll get the last entry
            #Apparently Greg doesn't use the best value, but the last one?
            last_value = parameter.param_history[-1]
            print(f"Last Value: {last_value}, Deviation: {deviation}")  
            new_parameter = np.random.normal(last_value.planned_value, deviation)

            if(parameter.minimum_value <= new_parameter <= parameter.maximum_value):
              parameter_names.append(parameter.name)
              parameter_values.append(round(new_parameter))
              break
            
            else:
               continue
            

   return PlanResponse(parameter_names, parameter_values)


if __name__ == "__main__":
  name = "Print Planner"
  description = "A PyAres implementation of Graig Ganitano's 3D Printing Planner"
  planner = AresPlannerService(Plan, name,  description, "1.0.0", port=8002)

  #Mark that the planner supports numbers
  planner.add_supported_type(AresDataType.NUMBER)
  
  #Add Settings, allow user to set standard deviation on all parameters
  planner.add_setting("Nozzle Temp Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Bed Temp Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Extrusion Rate Mod Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Speed Mod Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Retraction Length Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Acceleration Mod Standard Deviation", AresDataType.NUMBER)

  planner.start()