import numpy as np
import noise
import matplotlib.pyplot as plt
from scipy.optimize import differential_evolution

class SyntheticProcessResponse:
    def __init__(self, 
                 param_bounds: dict,
                 num_gaussians: int = 5, 
                 noise_scale: float = 0.1, 
                 noise_frequency: float = 2.0, 
                 response_bounds: tuple = (0, 1),
                 seed: int | None = None):
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
        self.param_names = sorted(list(param_bounds.keys()))
        self.dims = len(self.param_names)
        self.response_bounds = response_bounds
        self.noise_scale = noise_scale
        self.noise_freq = noise_frequency

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

    def evaluate(self, params):
        """
        Queries the synthetic space at a specific coordinate.
        """
        try:
            point = np.array([params[k] for k in self.param_names])
        except KeyError as e:
            raise KeyError(f"Missing parameter in input: {e}")

        # 1. Calculate Gaussian Component
        gaussian_sum = 0.0
        for g in self.gaussians:
            diff = (point - g['center']) ** 2
            width = 2 * (g['bandwidth'] ** 2)
            exponent = -np.sum(diff / width)
            
            gaussian_sum += g['amplitude'] * np.exp(exponent)

        # 2. Calculate Perlin Noise Component
        norm_point = []
        for i, p_name in enumerate(self.param_names):
            low, high = self.param_bounds[p_name]
            # Normalize to 0-1 range, then scale by frequency
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
            # Fallback for >3 dimensions
            noise_val = noise.pnoise3(norm_point[0], norm_point[1], sum(norm_point[2:]))

        total_response = gaussian_sum + (noise_val * self.noise_scale)
        
        return total_response