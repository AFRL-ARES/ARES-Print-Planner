from PyAres import AresPlannerService, AresDataType
from athena_planner.sim_anneal import simulated_annealing_planner

if __name__ == "__main__":
  name = "Simulated Annealing 3D Print Planner"
  description = "A PyAres implementation of Graig Ganitano's Simulated Annealing 3D Printing Planner"
  planner = AresPlannerService(simulated_annealing_planner, name,  description, "1.0.0", port=8002)

  #Mark that the planner supports numbers
  planner.add_supported_type(AresDataType.NUMBER)
  
  #Add Settings, allow user to set standard deviation on all parameters
  planner.add_setting("Nozzle Temp Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Bed Temp Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Extrusion Rate Mod Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Speed Mod Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Retraction Length Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Acceleration Mod Standard Deviation", AresDataType.NUMBER)
  planner.add_setting("Simulated Annealing Starting Temperature", AresDataType.NUMBER)
  planner.add_setting("Simulated Annealing Cooling Rate", AresDataType.NUMBER)

  planner.start()