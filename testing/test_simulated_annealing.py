import numpy as np
from PyAres import PlanRequest, PlanningParameter, AresDataType, ParameterHistoryItem
from PyAres.test_tools import PlannerTestClient
from testing.synthetic_process_space import SyntheticProcessResponse
if __name__ == "__main__":
    N_iterations = 10
    seed = 1337
    # Define Test Data:
    settings_dict = {"Bed Temp Standard Deviation":10.0,
                     "Nozzle Temp Standard Deviation":10.0,
                     'Extrusion Rate Mod Standard Deviation':0.1,
                     "Speed Mod Standard Deviation":0.2,
                     'Retraction Length Standard Deviation':0.5,
                     'Acceleration Mod Standard Deviation':0.1,
                     'Fan Speed Mod Standard Deviation':0.25,
                     'Simulated Annealing Starting Temperature':20,
                     'Simulated Annealing Cooling Rate':0.01,
                     'Retain Historical Context':True,
                     'Verbose Output':True,
                     'RNG Seed':seed}
    
    param_names = ["bed", 
                   "nozzle temp", 
                   "speed", 
                   'extrusion',
                   'retraction',
                   'acceleration',
                   'fan speed mod']

    rng = np.random.default_rng(seed=seed)
    data = np.vstack((rng.normal(60,5), 
                        rng.normal(220,5), 
                        rng.normal(1,0.2), 
                        rng.normal(0.8,0.1), 
                        rng.normal(0.5,0.5), 
                        rng.normal(1,0.2), 
                        rng.normal(0.5,0.1)))
    bounds = [(0,100),
              (120,300),
              (0,2),
              (0.6,2),
              (0,5),
              (0,2),
              (0,1)]
    
    process_response = SyntheticProcessResponse(dict(zip(param_names, bounds)),
                                                num_gaussians=7, 
                                                noise_scale=0.15, 
                                                noise_frequency=3.0, 
                                                seed=seed)
    results = []
    # Start Test Client
    test_client = PlannerTestClient(port=8002, host='localhost')

    # 1. Service Health Checks
    test_client.check_status()
    test_client.get_info()
    response_dict = dict()
    # 2. Run Planning Loop using the synthetic process response space
    results = []
    for i in range(N_iterations):
        planning_parameters = []
        if i == 0:
            results = []
        else:
            print(response_dict)
            results.append(process_response.evaluate(response_dict))
        for j in range(len(param_names)):
            param_history = []
            if i == 0:
                param_history.append(ParameterHistoryItem(planned_value=[], achieved_value=[]))
            else:
                val = response_dict[param_names[j]]
                param_history.append(ParameterHistoryItem(planned_value=float(val), achieved_value=float(val)))
            planning_parameters.append(PlanningParameter(name=param_names[j],
                                                        minimum_value=bounds[j][0],
                                                        maximum_value=bounds[j][1],
                                                        param_history=param_history,
                                                        data_type=AresDataType.NUMBER,
                                                        is_planned=True,
                                                        is_result=False,
                                                        planner_name="Simulated Annealing Planner",
                                                        initial_value=data[j,0]))
        request = PlanRequest(planning_parameters, settings_dict,results)
        response = test_client.run_planning(request)
        print(response.parameter_names)
        values = [v.number_value for v in response.parameter_values]
        response_dict = dict(zip(response.parameter_names, values))


