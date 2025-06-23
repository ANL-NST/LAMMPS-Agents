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


### Teachability Databases
- `teachability_db_gpt4o/`: Contains the ChromaDB with the saved input-output pairs after the human teachings using as a base model GPT-4o


## Examples
```
python lammps_agents.py

```

## Instructions to add a new agent
1. Update the `src/tools/agent_factory.py`
2. Update the `lammps_agents.py` with the new agents
3. Go to `src/tools/function_registry.py` to register any new functions to your agents.
4. Add a system message for the agent to explain the actions that can take and the available functions it has 


## Instructions to run on HPC
1. Update the `src/tools/specialized_tools/hpc_manager.py`