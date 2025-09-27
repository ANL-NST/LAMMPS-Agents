### Installation

1. Clone the repository:
```bash
git clone https://github.com/ANL-NST/LAMMPS-Agents.git
cd LAMMPS-Agents
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Components

### Core Files
- `lammps_agents.py`: Main implementation of the pipeline using LAMMPS agents
- `src/system_messages`: Contains the system messages used to guide each of the agents
- `src/tools`: Contains the main tools and file systems
- `results`: Contains exemplar runs with the agentic workflow for the tested systems.

### Teachability Databases
- `teachability_db_gpt4o/`: Contains the ChromaDB with the saved input-output pairs after the human teachings using as a base model GPT-4o


## How to run the code
If you want to test the code, you should have a access to LAMMPS software and install the requirements. You can add a new prompt inside the `lammps_agents.py` script and run it via:
```
python lammps_agents.py

```

## Instructions to add a new agent
1. Update the `src/tools/agent_factory.py`
2. Update the `lammps_agents.py` with the new agents
3. Go to `src/tools/function_registry.py` to register any new functions to your agents.
4. Add a system message for the agent in `src/system_messages` to explain the actions that can take and the available functions it has 


## Instructions to run LAMMPS 
The LAMMPS software is a prerequisite to run the simulations. A local LAMMPS version can be used or a version that is availanble to an HPC system. The functions that are responsible for running the simulations are located into: 
1. Update the `src/tools/specialized_tools/hpc_manager.py`