import numpy as np
from PyAres import PlanRequest, PlanningParameter, AresDataType, ParameterHistoryItem
from PyAres.test_tools import PlannerTestClient
import matplotlib.pyplot as plt
import itertools
import noise


class SyntheticProcessResponse:
    def __init__(self, 
                 param_bounds: dict,
                 output_bounds= (0.0, 1.0), 
                 num_gaussians: int = 5, 
                 noise_scale: float = 0.1, 
                 noise_frequency: float = 2.0, 
                 response_bounds: tuple = (0, 1),
                 seed: int | None = None,
                 calibration_samples=10000):
        """
        Initializes the synthetic process response space using modern NumPy RNG.

        Args:
            param_bounds (dict): Dictionary where keys are parameter names and values are 
                                 tuples of (lower_bound, upper_bound).
            num_gaussians (int): Number of "peaks" or "valleys" to generate in the space.
            noise_scale (float): Magnitude of the Perlin noise added to the signal.
            noise_frequency (float): Frequency of the Perlin noise.
            response_bounds (tuple): Tuple of (min_response, max_response) to scale the output.
            seed (int | None, optional): Random seed for the dedicated generator.
        """
        # --- Modern NumPy Random Generator ---
        # We create a specific generator instance for this class. 
        # This isolates the randomness of this environment from the rest of your code.
        self.rng = np.random.default_rng(seed)

        self.param_bounds = param_bounds
        self.output_bounds = output_bounds
        self.param_names = sorted(list(param_bounds.keys()))
        self.dims = len(self.param_names)
        self.response_bounds = response_bounds
        self.noise_scale = noise_scale
        self.noise_freq = noise_frequency
        self.raw_min = 0.0
        self.raw_max = 1.0

        # --- Generate Random Gaussians ---
        self.gaussians = []
        
        for _ in range(num_gaussians):
            # Random center within the defined bounds
            center = np.array([
                self.rng.uniform(self.param_bounds[p][0], self.param_bounds[p][1]) 
                for p in self.param_names
            ])
            
            # Random bandwidth (width of the bell curve).
            bandwidths = np.array([
                (self.param_bounds[p][1] - self.param_bounds[p][0]) * self.rng.uniform(0.1, 0.5)
                for p in self.param_names
            ])
            
            # Random amplitude
            amplitude = self.rng.uniform(-1.0, 2.0)
            
            self.gaussians.append({
                'center': center,
                'bandwidth': bandwidths,
                'amplitude': amplitude
            })

        # Random offset for Perlin noise
        self.noise_offset = self.rng.uniform(0, 100, self.dims)

        # calibrate the output scale
        self._calibrate_bounds(calibration_samples)

    
    def _raw_evaluate(self, point):
        """Internal method to compute the unscaled response for a numpy array point."""
        # Gaussian Component
        gaussian_sum = 0.0
        for g in self.gaussians:
            diff = (point - g['center']) ** 2
            width = 2 * (g['bandwidth'] ** 2)
            exponent = -np.sum(diff / width)
            gaussian_sum += g['amplitude'] * np.exp(exponent)

        # Perlin Noise Component
        norm_point = []
        for i, p_name in enumerate(self.param_names):
            low, high = self.param_bounds[p_name]
            norm_val = ((point[i] - low) / (high - low)) * self.noise_freq
            norm_point.append(norm_val + self.noise_offset[i])

        noise_val = 0.0
        if self.dims == 1:
            noise_val = noise.pnoise1(norm_point[0])
        elif self.dims == 2:
            noise_val = noise.pnoise2(norm_point[0], norm_point[1])
        elif self.dims == 3:
            noise_val = noise.pnoise3(norm_point[0], norm_point[1], norm_point[2])
        else:
            noise_val = noise.pnoise3(norm_point[0], norm_point[1], sum(norm_point[2:]))

        return gaussian_sum + (noise_val * self.noise_scale)
    
    def _calibrate_bounds(self, num_samples):
        """Samples the parameter space to estimate the global min and max."""
        # Generate random samples across the N-dimensional space
        samples = np.zeros((num_samples, self.dims))
        for i, p_name in enumerate(self.param_names):
            low, high = self.param_bounds[p_name]
            samples[:, i] = self.rng.uniform(low, high, num_samples)

        # Evaluate all samples to find empirical min/max
        raw_responses = np.array([self._raw_evaluate(pt) for pt in samples])
        
        self.raw_min = np.min(raw_responses)
        self.raw_max = np.max(raw_responses)
        
        # Prevent division by zero in case of a completely flat landscape
        if np.isclose(self.raw_min, self.raw_max):
            self.raw_max = self.raw_min + 1e-9


    def evaluate(self, params):
        """Queries the synthetic space and returns a scaled response."""
        try:
            point = np.array([params[k] for k in self.param_names])
        except KeyError as e:
            raise KeyError(f"Missing parameter in input: {e}")

        # 1. Get raw response
        raw_val = self._raw_evaluate(point)

        # 2. Scale to target bounds
        t_min, t_max = self.output_bounds
        scaled_val = t_min + ((raw_val - self.raw_min) * (t_max - t_min)) / (self.raw_max - self.raw_min)

        # 3. Clip the output
        # Because calibration is empirical, a real query might slightly exceed the 
        # sampled raw_min or raw_max. Clipping ensures strict adherence to output_bounds.
        return float(np.clip(scaled_val, t_min, t_max))

def plot_params(n_iter, planning_parameters, results ):
    # 1. 2d plot of the variations in the parameters
    marker_cycle = itertools.cycle(('o','+','.','*','^','s','x','D'))

    fig, (ax_t,ax_b) = plt.subplots(2,1,sharex=True) # 2 plots showing the variation in the paameters (top) and the change in the objective function

    ax_t.set_xlim(-1, n_iter+1)
    ax_t.set_ylim(-0.05,1.05)
    ax_t.set_yticks([0,0.5,1])
    ax_t.set_yticklabels([r'$x_{min}$','',r'$x_{max}$'])
    ax_t.set_xlabel('Iteration',fontsize=12,fontweight='bold')
    ax_t.set_ylabel('Parameter Value',fontsize=12,fontweight='bold')

    for p in planning_parameters:
            name = p.name
            p_bounds = (p.minimum_value,p.maximum_value)
            values = []
            for iteration in p.param_history[1:]: # Drop the first entry as a it is empty
                values.append(iteration.planned_value)
            norm_values = (np.asarray(values) - p_bounds[0]) / (p_bounds[1]-p_bounds[0])
            ax_t.plot(np.arange(0,n_iter-1),norm_values,label=name,marker=next(marker_cycle))
            ax_t.legend(loc='center right')
    best_results = np.array([np.min(results[:i+1]) for i in range(len(results))])
    
    ax_b.set_ylim([np.min(results),np.max(results)])
    ax_b.set_yticks([np.min(results),np.max(results)])
    ax_b.set_ylabel('Objective Score (lower is better)',fontsize=12,fontweight='bold')
    ax_b.plot(np.arange(0,n_iter-1),results,label='Current Score',marker='o')
    ax_b.plot(np.arange(0,n_iter-1),best_results,label='Best Score',marker='D')
    ax_b.legend(loc='center right')
    fig.tight_layout()
    plt.show()

def plot_surface_2d_3d(response_surface, planning_parameters, results,res=100):
    p_dict = {}
    bounds = []
    param_names = []
    for p in planning_parameters:
        name = p.name
        param_names.append(name)
        bounds.append((p.minimum_value,p.maximum_value))
        values = []
        for iteration in p.param_history[1:]: # Drop the first entry as a it is empty
            values.append(iteration.planned_value)
        p_dict[name]=np.array(values)

    #Generate Grid for Plotting
    x = np.linspace(bounds[0][0], bounds[0][1], res)
    y = np.linspace(bounds[1][0], bounds[1][1], res)
    X, Y = np.meshgrid(x, y)
    Z = np.zeros_like(X)

    for i in range(X.shape[0]):
        for j in range(X.shape[1]):
            Z[i, j] = response_surface.evaluate({param_names[0]: X[i, j], param_names[1]: Y[i, j]})
    fig, ax = plt.subplots()
    contour = ax.contourf(X, Y, Z, levels=30, cmap='viridis', alpha=0.8)
    fig.colorbar(contour, ax=ax, label='Objective Value')
    
    # Plot path on 2D
    ax.scatter(p_dict[param_names[0]], p_dict[param_names[1]], c='white', edgecolor='black', s=30, alpha=0.6, label='Samples')

    ax.scatter(p_dict[param_names[0]][np.argmin(results)], p_dict[param_names[1]][np.argmin(results)], c='red', marker='*', s=200, label='Best Found', zorder=10)
    # Connect the dots to show sequence
    
    ax.set_title("2D Landscape")
    ax.set_xlabel(f"Param: {param_names[0]}")
    ax.set_ylabel(f"Param: {param_names[1]}")
    ax.legend()
    plt.show()

    # --- Plot 2: 3D Surface ---
    fig = plt.figure()

    ax = fig.add_subplot(projection='3d')    
    # Plot Surface
    surf = ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.7, edgecolor='none', rstride=2, cstride=2)
    
    # Plot Path on 3D (lifted slightly so points don't clip into the surface)
    ax.scatter(p_dict[param_names[0]], p_dict[param_names[1]], results + 0.05, c='red', s=20, depthshade=False, label='Planner Path')

    # Mark the best point
    ax.scatter(p_dict[param_names[0]][np.argmin(results)], p_dict[param_names[1]][np.argmin(results)], np.min(results) + 0.1, c='magenta', marker='*', s=300, label='Best Solution')

    ax.set_title("3D Surface View")
    ax.set_xlabel("Param X")
    ax.set_ylabel("Param Y")
    ax.set_zlabel("Objective")
    ax.view_init(elev=45, azim=-45) # Set a nice viewing angle
    fig.tight_layout()
    plt.show()

def run_test(test_client, 
                settings_dict, 
                params_dict, 
                response_surface,
                N_iterations,
                N_params):
    
    param_names = params_dict['names']
    init_vals = params_dict['initial_values']
    bounds = params_dict['bounds']

    response_dict = dict()
    # Run Planning Loop using the synthetic process response space
    results = []
    param_histories = [[] for i in range(N_params)]

    for i in range(N_iterations):
        planning_parameters = []

        if i == 0:
            results = []
        else:
            print(response_dict)
            results.append(response_surface.evaluate(response_dict)) # Negative because the planner is a minimization planner

        for j in range(len(param_names[:N_params])):
            if i == 0: # The ARES OS loop always starts with Plan, so the first entry will will have no result and no paramter history.
                param_histories[j].append(ParameterHistoryItem(planned_value=[], achieved_value=[]))
            else:
                val = response_dict[param_names[j]]
                param_histories[j].append(ParameterHistoryItem(planned_value=float(val), achieved_value=float(val))) 
            
            planning_parameters.append(PlanningParameter(name=param_names[j],
                                                        minimum_value=bounds[j][0],
                                                        maximum_value=bounds[j][1],
                                                        param_history=param_histories[j],
                                                        data_type=AresDataType.NUMBER,
                                                        is_planned=True,
                                                        is_result=False,
                                                        planner_name="Simulated Annealing Planner",
                                                        initial_value=init_vals[j,0]))

        request = PlanRequest(planning_parameters, settings_dict,results)
        response = test_client.run_planning(request)
        values = [v.number_value for v in response.parameter_values]
        response_dict = dict(zip(response.parameter_names, values))

    return planning_parameters, np.array(results)

if __name__ == "__main__":
    # Settings
    N_iterations = 200 # Number of "experiments" in a trial
    test_seed = 7654321098
    plan_seed = 1234567890 
    N_params = 2 # Number of parameters to optimize
    N_tests = 100 # Number of trials to run to gather average performance data



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
                     'Retain Historical Context':False,
                     'Verbose Output':True,
                     'RNG Seed':plan_seed}
    

    param_names = ["bed", 
                   "nozzle temp", 
                   "speed", 
                   'extrusion',
                   'retraction',
                   'acceleration',
                   'fan speed mod']

    rng = np.random.default_rng(seed=test_seed)

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
    
    process_response = SyntheticProcessResponse(dict(zip(param_names[:N_params], bounds)),
                                                output_bounds=(1.0,10000),
                                                num_gaussians=int(rng.integers(3,9)), 
                                                noise_scale=rng.uniform(0.05,0.2), 
                                                noise_frequency=rng.uniform(1.0,10.0), 
                                                seed=int(rng.integers(1e6,1e12)))
    
    params_dict ={'names':param_names,
                  'initial_values':data,
                  'bounds':bounds}
    
    # Start Test Client
    test_client = PlannerTestClient(port=8002, host='localhost')

    # 1. Service Health Checks
    test_client.check_status()
    test_client.get_info()
    # 2. Run a test 
    planning_parameters, results = run_test(test_client,
                                            settings_dict,
                                            params_dict,process_response,
                                            N_iterations,
                                            N_params)

    #%% Test Visualization
    # Visualize the obhjective function progress
    plot_params(N_iterations,planning_parameters,results)

    # If using 2d make plots of the actual parameter space 
    # --- Plot 1: 2D Contour Map ---
    if N_params == 2:
        #Generate Grid for Plotting
        plot_surface_2d_3d(process_response,planning_parameters,results)
    
    # Run 100 different tests and average the results to get an idea of the average performance 
    collected_results = []
    settings_dict.update({'Retain Historical Context':False})

    for i in range(N_tests):
        process_response = SyntheticProcessResponse(dict(zip(param_names[:N_params], bounds)),
                                                    output_bounds=(1.0,10000),
                                                    num_gaussians=int(rng.integers(3,9)), 
                                                    noise_scale=rng.uniform(0.05,0.2), 
                                                    noise_frequency=rng.uniform(1.0,10.0), 
                                                    seed=test_seed)
        _, results = run_test(test_client,
                                settings_dict,
                                params_dict,
                                process_response,
                                N_iterations,
                                N_params)
        best_results = np.array([np.min(results[:i+1]) for i in range(len(results))])
        collected_results.append(best_results)

    quants = np.quantile(np.array(collected_results), [0.05,0.25,0.5,0.75,0.95],axis=0)

    mins = np.min(np.array(collected_results),axis=0)
    maxes = np.max(np.array(collected_results),axis=0)

    fig, ax = plt.subplots()
    ax.set_title(f'{N_params} Param. Optimization, {N_tests} Unique Trials, {N_iterations} Experiments Each.')
    ax.fill_between(np.arange(N_iterations-1),mins,maxes,alpha=0.2,label='Min/Max')
    ax.plot(np.arange(N_iterations-1),quants[2,:],ls='-',color='tab:blue',label='Median')

    ax.plot(np.arange(N_iterations-1),quants[1,:],ls='--',color='tab:blue',label='25th/75 Percentile')
    ax.plot(np.arange(N_iterations-1),quants[3,:],ls='--',color='tab:blue')

    ax.plot(np.arange(N_iterations-1),quants[0,:],ls=':',color='tab:blue',label='5th/95th Percentile')
    ax.plot(np.arange(N_iterations-1),quants[4,:],ls=':',color='tab:blue')

    ax.set_xlabel('Iteration #',fontsize=12,fontweight='bold')
    ax.set_ylabel('Objective Score',fontsize=12,fontweight='bold')
    ax.legend()
    fig.tight_layout()
    plt.show()


    