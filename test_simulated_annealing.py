import numpy as np
from PyAres import PlanRequest, PlanningParameter, AresDataType, ParameterHistoryItem
from PyAres.test_tools import PlannerTestClient

if __name__ == "__main__":
    test_client = PlannerTestClient(port=8002, host='localhost')

    # 1. Health Checks
    test_client.check_status()
    test_client.get_info()

    # Define Test Data:
    settings_dict = {"Bed Temp Standard Deviation":10.0,
                     "Nozzle Temp Standard Deviation":10.0,
                     'Extrusion Rate Mod Standard Deviation':0.1,
                     "Speed Mod Standard Deviation":0.2,
                     'Retraction Length Standard Deviation':0.5,
                     'Acceleration Standard Deviation':0.2,
                     'Fan Speed Mod Standard Deviation':0.1,
                     'Simulated Annealing Starting Temperature':20,
                     'Simulated Annealing Cooling Rate':0.01,
                     'Retain Historical Context':True,
                     'Verbose Output':True,
                     'RNG Seed':12345}
    
    param_names = ["bed", 
                   "nozzle temp", 
                   "speed", 
                   'extrusion',
                   'retraction',
                   'acceleration',
                   'fan speed mod']

    rng = np.random.default_rng(seed=12345)
    data = np.vstack((rng.normal(60,5), 
                        rng.normal(220,5), 
                        rng.normal(1,0.2), 
                        rng.normal(0.8,0.1), 
                        rng.normal(0.5,0.5), 
                        rng.normal(0.2,0.2), 
                        rng.normal(0.5,0.1)))
    bounds = [(0,100),
              (120,300),
              (0,2),
              (0.6,2),
              (0,5),
              (0,2),
              (0,1)]
    results = []
    for j in range(10):
        planning_parameters = []
        results.append(rng.uniform(5,500))
        for i in range(len(param_names)):
            param_history = []
            if j == 0:
                param_history.append(ParameterHistoryItem(planned_value=[], achieved_value=[]))
            else:
                val = response_dict[param_names[i]]
                param_history.append(ParameterHistoryItem(planned_value=float(val), achieved_value=float(val)+rng.normal(0,0.1)))
            planning_parameters.append(PlanningParameter(name=param_names[i],
                                                        minimum_value=bounds[i][0],
                                                        maximum_value=bounds[i][1],
                                                        param_history=param_history,
                                                        data_type=AresDataType.NUMBER,
                                                        is_planned=True,
                                                        is_result=False,
                                                        planner_name="Simulated Annealing Planner",
                                                        initial_value=data[i,0]))
        if j == 0:
            request = PlanRequest(planning_parameters, settings_dict,[])
        else:
            request = PlanRequest(planning_parameters, settings_dict,results)
        response = test_client.run_planning(request)
        values = [v.number_value for v in response.parameter_values]
        response_dict = dict(zip(response.parameter_names, values))
        print(response_dict)
