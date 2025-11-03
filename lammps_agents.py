import os
from dotenv import load_dotenv
load_dotenv()

import autogen
from autogen.coding import LocalCommandLineCodeExecutor
from autogen.agentchat.contrib.capabilities.teachability import Teachability
import nest_asyncio
import sys, asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
import datetime
from typing import Any
from src.tools.specialized_tools.local_run_manager import LocalRunManager
nest_asyncio.apply()
from src.tools.llm_config import get_llm_config
from src.tools.validation_tools import ValidationManager


class AutoGenSystem:
    def __init__(self, llm_type: str, workdir: str):
        print("Starting Agentic System initialization...")

        self.llm_type = llm_type
        self.llm_config = get_llm_config(llm_type)

        self.workdir = os.path.abspath(workdir)
        if not os.path.exists(self.workdir):
            os.makedirs(self.workdir, exist_ok=True)
            print(f"Created working directory: {self.workdir}")

        self.executor = LocalCommandLineCodeExecutor(
            timeout=1200,
            work_dir=self.workdir,
        )
        print("🔧 Setting up components...")
        self._setup_specialized_tools()    
        self._setup_validation_manager()   

        self._setup_agents()               
        self._setup_function_registry()    
        self._setup_group_chat()           
        self._setup_teachability()         
        print("AutoGenSystem ready!")


    def _setup_validation_manager(self):
        """Set up validation manager."""
        try:
            self.validation_manager = ValidationManager(self.workdir)
            self.validation_manager.potential_manager = self.potential_manager            
            print("ValidationManager initialized")
        except Exception as e:
            print(f"ValidationManager failed: {e}")
            raise

    def _setup_specialized_tools(self):
        """Initialize all specialized tool managers."""
        try:
            from src.tools.specialized_tools import (
                FileManager,
                StructureCreator,
                PotentialManager,
                HPCManager,
                # LocalRunManager,
                PhonopyManager
            )

            print("🔧 Setting up specialized tools...")

            # Initialize file management tools
            self.file_manager = FileManager(self.workdir)
            print("  ✅ FileManager initialized")

            # Initialize structure creator
            self.structure_creator = StructureCreator(self.workdir)
            print("  ✅ StructureCreator initialized")


            self.local_run_manager = LocalRunManager(self.workdir)

            self.potential_manager = PotentialManager(self.workdir, None) 

            # Initialize potential manager attributes for workflow tracking
            if not hasattr(self.potential_manager, 'potential_validated'):
                self.potential_manager.potential_validated = False
            if not hasattr(self.potential_manager, 'last_potential_file'):
                self.potential_manager.last_potential_file = None
            print("  ✅ PotentialManager initialized")

            # Initialize HPC manager
            # self.hpc_manager = HPCManager(self.workdir)
            self.hpc_manager = self.local_run_manager
            print("  ✅ HPCManager initialized")

            # Initialize phonopy manager
            self.phonopy_manager = PhonopyManager(self.workdir)
            print("  ✅ PhonopyManager initialized")

            print("✅ All specialized tools ready!")

        except Exception as e:
            print(f"Specialized tools failed: {e}")
            raise

    def _setup_agents(self):
        """Set up all agents using the factory."""
        try:
            from src.tools.agent_factory import AgentFactory

            print("Setting up agents...")

            # Create agent factory
            agent_factory = AgentFactory(self.llm_config, self.executor, self.workdir)

            # Create all agents
            self.agents = agent_factory.create_all_agents()

            # Extract individual agents for backward compatibility
            self.lammps_admin = self.agents['admin']
            self.structure_agent = self.agents['structure']
            self.potential_agent = self.agents['potential']
            self.lammps_agent = self.agents['lammps']
            self.lammps_elastic_agent = self.agents['lammps_elastic']
            self.reviewer_agent = self.agents['reviewer']
            self.hpc_agent = self.agents['hpc']
            self.analysis_agent = self.agents['analysis']
            self.websurfer = self.agents['websurfer']
            self.phonopy_agent = self.agents['phonopy']

            # Here we link the websurfer to potential manager
            if hasattr(self, 'potential_manager') and self.websurfer:
                if hasattr(self.potential_manager, 'set_websurfer'):
                    self.potential_manager.set_websurfer(self.websurfer)
                else:
                    self.potential_manager.websurfer = self.websurfer

            print("✅ Agents initialized")

        except Exception as e:
            print(f"❌ Agents setup failed: {e}")
            raise

    def get_managers_dict(self):
        """Get dictionary of all managers for function registry."""
        return {
            'file_manager': self.file_manager,
            'structure_creator': self.structure_creator,
            'potential_manager': self.potential_manager,
            'hpc_manager': self.hpc_manager,
            'local_run_manager': self.local_run_manager,
            'phonopy_manager': self.phonopy_manager,
            'validation_manager': self.validation_manager
        }

    def _setup_function_registry(self):
        """Set up function registry and register all functions."""
        try:
            from src.tools.function_registry import FunctionRegistry

            print("Setting up function registry...")

            managers_dict = self.get_managers_dict()

            self.function_registry = FunctionRegistry(self.agents, managers_dict, self.workdir)
            self.function_registry.register_all_functions()

            print("Function registry ready")

        except Exception as e:
            print(f"Function registry failed: {e}")
            raise


    def _setup_group_chat(self, previous_chat_file: str = None):
        """Set up group chat with all specialized agents."""
        try:
            print("Setting up group chat...")
            previous_messages = []
            if previous_chat_file:
                previous_messages = self._load_previous_messages(previous_chat_file)

            self.groupchat = autogen.GroupChat(
                agents=[
                    self.lammps_admin,
                    self.structure_agent,
                    self.potential_agent,
                    self.lammps_agent,
                    self.lammps_elastic_agent,
                    self.reviewer_agent,
                    self.hpc_agent,
                    self.analysis_agent,  
                    self.websurfer,
                    self.phonopy_agent,
                ],
                messages=previous_messages,
                max_round=800,
                select_speaker_auto_llm_config=self.llm_config,
                speaker_selection_method="auto",
                
            )

            from src.system_messages.manager_system_message import MANAGER_SYSTEM_PROMPT
            # manager_llm_config = {
            # "model": "o3",
            # 'api_key': OPENAI_API_KEY,
            # # 'temperature': 0,
            # }
            self.manager = autogen.GroupChatManager(
                groupchat=self.groupchat,
                llm_config=self.llm_config,
                system_message=MANAGER_SYSTEM_PROMPT,
            )

            print(f"Setting up auto-vision...")
            print(f"Analysis agent: {self.analysis_agent.name}")

        except Exception as e:
            print(f"Group chat failed: {e}")
            raise


    def _setup_teachability(self):
        """Set up teachability for the agents."""
        try:
            print("Setting up teachability...")

            self.teachability = Teachability(
                verbosity=0,
                reset_db=False,
                path_to_db_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), f"teachability_db_{self.llm_type}")),
                #ath_to_db_dir=f"./teachability_db_{self.llm_type}",
                recall_threshold=6,
                llm_config=self.llm_config
            )
            for agent in [self.lammps_agent, self.lammps_admin , self.manager]:
                self.teachability.add_to_agent(agent)

            print("Teachability ready")

        except Exception as e:
            print(f"Teachability failed: {e}")
            self.logger.error(f"Teachability setup failed: {e}")
            print("Continuing without teachability...")


    def initiate_chat(self, prompt: str) -> Any:

        try:
            result = self.lammps_admin.initiate_chat(
                self.manager,
                message=prompt,
            )

            self._save_chat_result(prompt, result)
            
            return result
            
        except Exception as e:
            print(f"Chat failed: {str(e)}")
            raise

    def _load_previous_messages(self, chat_file_path: str) -> list:
        """Load and parse previous chat messages from saved file."""
        try:
            if not os.path.exists(chat_file_path):
                print(f"Chat file not found: {chat_file_path}")
                return []
            
            with open(chat_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            messages = []
            
            import re
            
            agent_patterns = [
                r"admin \(to chat_manager\):",
                r"structure_agent:",
                r"potential_agent:", 
                r"lammps_agent:",
                r"lammps_elastic_agent:",
                r"reviewer_agent:",
                r"hpc_agent:",
                r"analysis_agent:",
                r"websurfer:",
                r"phonopy_agent:",
                r"vision_agent:",  
                r"chat_manager:"
            ]
            
            lines = content.split('\n')
            current_speaker = None
            current_message = []
            
            for line in lines:
                speaker_found = False
                for pattern in agent_patterns:
                    if re.match(pattern, line):
                        if current_speaker and current_message:
                            messages.append({
                                "content": '\n'.join(current_message).strip(),
                                "name": current_speaker
                            })
                        
                        current_speaker = pattern.replace(":", "").replace(" (to chat_manager)", "")
                        current_message = []
                        speaker_found = True
                        break
                
                if not speaker_found and current_speaker:
                    current_message.append(line)
            
            if current_speaker and current_message:
                messages.append({
                    "content": '\n'.join(current_message).strip(),
                    "name": current_speaker
                })
            
            print(f"✅ Loaded {len(messages)} previous messages")
            return messages
            
        except Exception as e:
            print(f"❌ Failed to load previous messages: {e}")
            return []

    def _save_chat_result(self, prompt: str, result):
        """Save chat result to text file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        results_dir = "results"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir, exist_ok=True)
        
        result_file = f"results/chat_result_{timestamp}.txt"
        
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write(f"LAMMPS AGENT CONVERSATION RESULT\n")
                f.write(f"Timestamp: {datetime.datetime.now()}\n")
                f.write(f"Prompt: {prompt}\n")
                f.write("="*80 + "\n\n")
                
                # Write the full conversation result
                f.write(str(result))
                
                f.write(f"\n\n" + "="*80 + "\n")
                f.write(f"End of conversation - {datetime.datetime.now()}\n")
                f.write("="*80 + "\n")
            
            print(f"💾 Chat result saved: {result_file}")
            
        except Exception as e:
            print(f"Failed to save chat result: {e}")
  

# if __name__ == "__main__":
#     try:
#         workdir = "lammps_run_test"
#         llm_type = "gpt4o" #"gpt-4.1" #

#         print("Initializing AutoGen LAMMPS System...")

#         # Initialize the system
#         autogen_system = AutoGenSystem(
#             llm_type=llm_type,
#             workdir=workdir,
#         )

#         # Activate this if you want to provide a specific input from previous results
#         # previous_chat = r"C:\Users\kvriz\Desktop\LAMMPS-Agents\results\chat_result_20250703_082056.txt"
#         #r"C:\Users\kvriz\Desktop\LAMMPS-Agents\results\chat_result_20250605_100215.txt"
#         # autogen_system._setup_group_chat(previous_chat)

#         print("Starting LAMMPS calculation...")
#         prompt_1a = """Calculate the lattice constants of gold using LAMMPS.""" # If restarting """Continue from where we left off - what's the next step?""" #
#         prompt_1b = """Calculate the lattice constants for a gold-copper alloy using LAMMPS."""

#         prompt_2a = """Compute the elastic constants of gold."""
#         prompt_2b = """Compute the elastic constants of a gold-copper alloy. Start from where we left off in the previous chat Time to analyse the results and get the elastic constants matrix."""
        
#         prompt_3a = """Calculate the phonon dispersion for gold."""
#         prompt_3b = """Calculate the phonon dispersion for a gold-copper alloy."""

#         prompt_4a = """Continue from where we left off - Perform a melting point simulation for a gold-copper alloy using LAMMPS. The full melting simulation has finished.
#         Now create the ovitio frame and do the analysis."""
#         #"""Perform a melting point simulation for a nickel-copper alloy using LAMMPS."""
#         #"""Perform a melting point simulation for gold using LAMMPS."""
#         #"""Perform a melting point simulation for iron using LAMMPS."""
#         #"""Perform a melting point simulation for gold using LAMMPS and the provided potential file."""
#         prompt_4b = """Calculate the phonon dispersion for a gold-copper alloy.""" #"""Compute the elastic constants of titanium.""" 
#         #"""Calculate the lattice constants and cohesive energy for gold using LAMMPS."""
#         #"""Perform a melting point simulation for titanium using LAMMPS."""
#         #"""Perform a melting point simulation for a gold-copper alloy using LAMMPS."""
#         #"""Run a LAMMPS simulations starting from the already existing potential and lammps input files in the lammps_run_test folder."""
#         #"""Perform a melting point simulation for Silicon using LAMMPS starting from the already existing potential and lammps input files in the lammps_run_test folder."""
#         #"""Continue from where we left AND Perform a melting point simulation for a gold-copper alloy. """
#         # """Check the image melting_visualization.png for melting."""# <img melting_visualization.png> and <img full_melt_visualization.png> and comment on which one is a melted structure."""
#         #"""Analyze the output of the melting point simulation and create the plots.""" #
#         # prompt_3b = """Check the "melted_structure_visualization.png" and decide if the structure is fully melted or not.""" #
#         # prompt_3 = """We have just performed a melting point calculation and the image generated from ovito
#         # is in the workdir. Check the image and see if there are two phases or only one. If it is only one then
#         # rerun the lammps simulation with co
#         # rrected parameters"""
#         # prompt_8= """We are calculating the melting point of gold. Rerun the simulation locally."""
        
#         # The simulation has just finished.
#         # Create the melting analysis plot by looking at the dump.melting . Check the melting analysis plot and decide in the melting point simulation was successfull
        
        
#         import asyncio, os

#         dump_path = os.path.abspath(os.path.join(workdir, "dump.output"))
#         frames_dir = os.path.abspath(os.path.join(workdir, "frames"))


#         import time
#         time.sleep(1)
#         chat_result = autogen_system.initiate_chat(prompt_1a)

#         print("Run completed successfully!")

#     except Exception as e:
#         print(f"System failed: {e}")

#         try:
#             if hasattr(autogen_system, 'analysis_agent'):
#                 autogen_system.analysis_agent.execute_tool("cleanup_monitors", {})
#         except:
#             pass
#         import traceback
#         traceback.print_exc()


if __name__ == "__main__":
    try:
        base_workdir = "lammps_run_test"
        llm_type = "gpt4o"
        prompt = """Calculate the lattice constants of gold using LAMMPS."""
        n_runs = 10

        print(f"Initializing AutoGen LAMMPS System for {n_runs} repeated runs...")

        results_summary = []

        for i in range(1, n_runs + 1):
            print("\n" + "="*80)
            print(f"🔁 Starting Run {i}/{n_runs}")
            print("="*80)

            # Create a unique subdirectory for each run
            run_workdir = os.path.join(base_workdir, f"run_{i:02d}")
            os.makedirs(run_workdir, exist_ok=True)

            try:
                # Initialize a fresh system each time to ensure independence
                autogen_system = AutoGenSystem(
                    llm_type=llm_type,
                    workdir=run_workdir,
                )

                # Give it a small pause between runs (optional)
                import time
                time.sleep(1)

                # Run the lattice constant calculation
                chat_result = autogen_system.initiate_chat(prompt)

                # Record success
                results_summary.append({"run": i, "status": "success", "workdir": run_workdir})
                print(f"✅ Run {i} completed successfully!\n")

            except Exception as e:
                results_summary.append({"run": i, "status": f"failed: {e}", "workdir": run_workdir})
                print(f"❌ Run {i} failed: {e}\n")

        # Save summary file
        summary_file = os.path.join(base_workdir, "evaluation_summary.txt")
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("Lattice Constant Evaluation Summary\n")
            f.write("="*60 + "\n")
            for r in results_summary:
                f.write(f"Run {r['run']:02d}: {r['status']} (dir: {r['workdir']})\n")

        print(f"📄 Summary saved to: {summary_file}")

        # Optional: print final statistics
        success_count = sum(1 for r in results_summary if r["status"] == "success")
        print(f"\n✅ Successful runs: {success_count}/{n_runs}")
        print("Evaluation complete.")

    except Exception as e:
        print(f"System failed during evaluation: {e}")
        import traceback
        traceback.print_exc()
