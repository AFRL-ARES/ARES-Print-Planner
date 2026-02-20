# Simulated Annealing Print Planner
## Introduction
This PyARES planner is designed for use with [Educational ARES](https://github.com/AFRL-ARES/Educational-ARES). The planning approch is based on the technique outline in in **A hybrid metaheuristic and computer vision approach to closed-loop calibration of fused deposition modeling 3D printers** by Ganitano et al. (DOI: [10.1007/s40964-023-00480-1](https://doi.org/10.1007/s40964-023-00480-1)) with modifications to make it suitable for use with the Educational ARES project. 

This project runs as a service using the [PyAres library](https://pypi.org/project/PyAres/), allowing it to integrate with Educational ARES.

## Planner theory of operation:
The goal of the planner is to minimize the objective score of the process. To generate new test points, conditions are randomly perturbed by sampling from a normal distribution centered on the current value with a user specified standard deviation. 

The planner operates from a "root condition" which serves as the current value from which the 
"test condition" is perturbed. After each experimental iteration
if the objective score for the test conditon is lower (better) than the previous best objective score, 
the test condition becomes the new root condition. This will tend to cause the planner to find conditions 
that minimize the objective score in the vicinity of its root condition.

In the event that the objective score is higher (worse), the planner checks the following inquality:

exp((best score - test score)/T) > uniform(0, 1)

Where T is the "temperature" of the simulation. If the inquality evaluates to true, the root condition is updated to the test condition regardless of the score. This approach helps kick the planner out of local minima in the process response surface. 

The temperature of the simulation determines how frequently this kick occurs, with higher temperatures producing 
results closer to a random walk, and lower temperatures behaving more like a hill climbing/desecent approach. Within
the planner, this temperature is controlled by an initial temperature setting and a cooling rate, which causes the simulation 
temperature to decay as: T(N_itter) = T_0*exp(-<decay rate>*N_iter), and thus decreases the randomness of the planner over time.

Note that this is a pure simulated annealing planner, and there is no logic to force the planner to backtrack to 
known good conditions after the root conditions are updated by the annealing criteria.

## Project Structure
* `start_planner_simulated_annealing.py`: The main entry point. Starts the PyAres service.
* `src/athena_planner/`: Main package source.
    * `simulated_annealing/simulated_annealing.py`: Contains the logic for the planner

## Installation & Environment Setup

This project requires **Python >=3.10**. A dedicated environment is highly recommended to keep module dependences for different PyAres services from causing version conflicts.

### Option A: Using Anaconda / Miniconda / Miniforge (Recommended)

1.  **Create the environment:**
    ```bash
    conda create -n ares_analyzer
    ```
2.  **Activate the environment:**
    ```bash
    conda activate ares_analyzer
    ```
3.  **Install system dependencies (Optional but recommended for OpenCV/Blender):**
    * On Linux, you may need libraries like `libx11-dev` or `libgl1`.
    * *Example (Ubuntu):* `sudo apt-get install libxi6 libgconf-2-4`
4.  **Install the package:**
    Navigate to the project root directory and run:
    ```bash
    pip install .
    ```
    *Note: This will automatically install dependencies listed in `pyproject.toml`, including `PyAres`, `numpy`, etc.*

### Option B: Using Python venv

1.  **Ensure you have Python >=3.10 installed:**
    Check your version:
    ```bash
    python --version
    ```
2.  **Create the virtual environment:**
    ```bash
    python -m venv ares_venv
    ```
3.  **Activate the environment:**
    * **Windows:**
        ```powershell
        .\ares_venv\Scripts\activate
        ```
    * **Linux/macOS:**
        ```bash
        source ares_venv/bin/activate
        ```
4.  **Install the package:**
    ```bash
    pip install .
    ```

## Planner Configuration
The planner has a number of user configurable settings, some of which are global in scope, and some of which correspond to specific experimential parameters
### Global Settings
1. **Simulated Annealing Starting Temperature**: Initial "temperature" of the simulated annealing, controls how random the planner is for early experiments **(Recommended value: 20)**
2. **Simulated Annealing Cooling Rate**: Decay rate of the temperature, controls how quickly the planner transitions from the more exploratory high temperature operation to the more minimization focused low temperature operation. **(Recommended value: 0.01)**
3. **Retain Historical Context**: Retains historical data between ARES OS campaings, allows the results to be stitched together between the 3-4 experiment campaings controled by the Educational ARES smartprint configuration. The context is stored in planner global variabes that are maintained until the planner service is relaunched.
4. **RNG Seed**: A user define RNG Seed for repeatable planning. If none is specified, the current unix timestamp is used as the seed.
5. **Verbose Output**: Prints information about the planning process to the associated terminal window. Useful for debugging or just keeping track of the process. 
### Parameter Specific Settings
Due to limitations of communication between ARES OS and PyAres service an explicity relationship between certain parameters and certain settings is defined in the planner itself. Thus it is critical to use the parameter names below when configuring an ARES OS campaigns. These limitations will hopefully be relaxed in a future release. Note that some parameters are numeric while other are multiplicative modifiers for values in the original .gcode file, so when translating results to a profile for a new material, it is important take make note of the default values used.


1. Parameter: **nozzle temp** -> Setting: **Nozzle Temp Standard Deviation**: The standard deviation of perturbations to the printer hot end temperature. (Recommended value: 10)
2. Parameter: **bed** -> Setting: **Bed Temp Standard Deviation**: The standard deviation of perturbations to the print bed temperature. (Recommended value: 10)
3. Parameter: **retraction** -> Setting: **Retraction Length Standard Deviation**: Standard deviation of perturbations to the retraction length print speed. (Recommended value: 0.5)
4. Parameter: **extrusion** -> Setting: **Extrusion Rate Mod Standard Deviation**: Standard deviation of perturbations to the modifier for the extrusion rate. (Recommended value: 0.2)
5. Parameter: **speed** -> Setting: **Speed Mod Standard Deviation**: Standard deviation of perturbations to the modifier for the print speed. (Recommended value: 0.1)
6. Parameter: **acceleration** -> Setting: **Acceleration Mod Standard Deviation**: Standard deviation of perturbations to the modifier for acceleration. (Recommended value: 0.1)
6. Parameter: **fan speed mod** -> Setting: **Fan Speed Mod Standard Deviation**: Standard deviation of perturbations to the modifier for the speed of the print cooling fan. (Recommended value: 0.25)

## Usage

To start the planner service, ensure you have activated the approriate python environment:

```bash
python start_planner_simulated annealing_analyzer.py
```
The service will start on port 8002 (localhost) by default. It waits for PyAres requests.

## Testing/Demo
The script `testing/test_simulated_annealing.py` will perform a basic communication check with the planner as well as demonstrate the planner functionality. For proper functionality, this script should be called from a separate terminal instance from the one running the planner.

The testing script will generate a plot of the normalized variaton in the parameters and the objective score vs the # of iterations for planning on a randomized process response surface comprised of N-dimensional Gaussian distributions. If a test is run with only two parameters, the testing script will also generate 2-d and 3-d plots of the response surface with experimental points marked. The test script then will then run trials over a large number of unique process reponse surfaces and plot median convergence performance w.r.t. the required number of iterations.

