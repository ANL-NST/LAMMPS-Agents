# lammps_agents.py
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import autogen
from autogen.coding import LocalCommandLineCodeExecutor
from autogen.agentchat.contrib.capabilities.teachability import Teachability
import nest_asyncio
import sys, asyncio
if sys.platform.startswith("win"):
    # back to default loop (supports subprocess for Playwright)
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
import datetime
from typing import Any

nest_asyncio.apply()
from src.tools.llm_config import get_llm_config
from src.tools.validation_tools import ValidationManager
import tiktoken
# def is_termination_msg(message):
#     return (
#         isinstance(message, dict)
#         and any(word in message.get("content", "").lower() for word in ["terminate", "complete", "done", "finished"])
#     )

class AutoGenSystem:
    def __init__(self, llm_type: str, workdir: str):
        print("Starting Agentic System initialization...")

        self.llm_type = llm_type
        self.llm_config = get_llm_config(llm_type)

        # Ensure working directory exists and is absolute
        self.workdir = os.path.abspath(workdir)
        if not os.path.exists(self.workdir):
            os.makedirs(self.workdir, exist_ok=True)
            print(f"Created working directory: {self.workdir}")

        # Read polybot file
        # with open(polybot_file_path, 'r', encoding="utf-8") as polybot_file:
        #     self.polybot_file = ''.join(polybot_file.readlines())

        # Initialize executor
        self.executor = LocalCommandLineCodeExecutor(
            timeout=1200,
            work_dir=self.workdir,
        )
        # Setup components in CORRECT order
        print("🔧 Setting up components...")
        self._setup_specialized_tools()    # Then specialized tools
        self._setup_validation_manager()   # Validation manager first

        self._setup_agents()               # Then agents (needs specialized tools)
        self._setup_function_registry()    # Functions (needs agents and managers)
        self._setup_group_chat()           # Group chat (needs agents)
        self._setup_teachability()         # Teachability last
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
                PhonopyManager
            )

            print("🔧 Setting up specialized tools...")

            # Initialize file management tools
            self.file_manager = FileManager(self.workdir)
            print("  ✅ FileManager initialized")

            # Initialize structure creator
            self.structure_creator = StructureCreator(self.workdir)
            print("  ✅ StructureCreator initialized")

            # Initialize potential manager (needs websurfer)
            # Note: websurfer will be created in agents setup
            self.potential_manager = PotentialManager(self.workdir, None)  # Will link websurfer later

            # Initialize potential manager attributes for workflow tracking
            if not hasattr(self.potential_manager, 'potential_validated'):
                self.potential_manager.potential_validated = False
            if not hasattr(self.potential_manager, 'last_potential_file'):
                self.potential_manager.last_potential_file = None
            print("  ✅ PotentialManager initialized")

            # Initialize HPC manager
            self.hpc_manager = HPCManager(self.workdir)
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

            print("🤖 Setting up agents...")

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
            # self.vision_agent = self.agents['vision']

            # Now link websurfer to potential manager
            if hasattr(self, 'potential_manager') and self.websurfer:
                # If your PotentialManager has a method to set websurfer
                if hasattr(self.potential_manager, 'set_websurfer'):
                    self.potential_manager.set_websurfer(self.websurfer)
                else:
                    # Or just set it directly
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
            'phonopy_manager': self.phonopy_manager,
            'validation_manager': self.validation_manager
        }

    def _setup_function_registry(self):
        """Set up function registry and register all functions."""
        try:
            from src.tools.function_registry import FunctionRegistry

            print("Setting up function registry...")

            # Get managers dictionary
            managers_dict = self.get_managers_dict()

            # Create function registry and register all functions
            self.function_registry = FunctionRegistry(self.agents, managers_dict, self.workdir)
            self.function_registry.register_all_functions()

            print("Function registry ready")

        except Exception as e:
            print(f"Function registry failed: {e}")
            raise


    def _setup_group_chat(self, previous_chat_file: str = None):
        """Set up group chat with all specialized agents."""
        try:
            print("💬 Setting up group chat...")
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
                    # self.vision_agent,  
                ],
                messages=previous_messages,
                max_round=180,
                select_speaker_auto_llm_config=self.llm_config,
                speaker_selection_method="auto",
                
            )

            from src.system_messages.manager_system_message import MANAGER_SYSTEM_PROMPT

            self.manager = autogen.GroupChatManager(
                groupchat=self.groupchat,
                llm_config=self.llm_config,
                system_message=MANAGER_SYSTEM_PROMPT,
                # is_termination_msg=is_termination_msg
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
            base_dir = os.path.abspath("./") 
            self.teachability = Teachability(
                verbosity=0,
                reset_db=False,
                path_to_db_dir = os.path.join(base_dir, f"./teachability_db_{self.llm_type}"),
                # path_to_db_dir=f"./teachability_db_{self.llm_type}",
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

    def count_tokens(messages, model="gpt-4o"):
        encoding = tiktoken.encoding_for_model(model)
        text = "\n".join(m.get("content", "") for m in messages)
        return len(encoding.encode(text))
    
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
            
            # Split by agent names - adjust these patterns based on your actual file format
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
            
            # Simple parsing - you may need to adjust based on your actual file format
            lines = content.split('\n')
            current_speaker = None
            current_message = []
            
            for line in lines:
                # Check if line starts with an agent name
                speaker_found = False
                for pattern in agent_patterns:
                    if re.match(pattern, line):
                        # Save previous message if exists
                        if current_speaker and current_message:
                            messages.append({
                                "content": '\n'.join(current_message).strip(),
                                "name": current_speaker
                            })
                        
                        # Start new message
                        current_speaker = pattern.replace(":", "").replace(" (to chat_manager)", "")
                        current_message = []
                        speaker_found = True
                        break
                
                if not speaker_found and current_speaker:
                    current_message.append(line)
            
            # Add the last message
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

    

if __name__ == "__main__":
    try:
        workdir = "lammps_run_test_Cu_reax"
        polybot_file_path = 'operation_instructions.py'
        llm_type = "gpt4o" #"gpt-4.1" #

        autogen_system = AutoGenSystem(
            llm_type = llm_type,
            workdir=workdir
        )

        # print("🔥 Initializing AutoGen LAMMPS System...")
        # base_dir = os.path.abspath("./") 
        # prompt_1a = """Calculate the lattice constants and cohesive energy of gold using LAMMPS and use Au_u3.eam potential.""" # If restarting """Continue from where we left off - what's the next step?""" #

        # for i in range(0,5):
        #     workdir = os.path.join(base_dir, f"lammps_run_test_{i}_lattice_Au")
        #     print(f"LAMMPS run {i+1}")
        # # Initialize the system
        #     autogen_system = AutoGenSystem(
        #         llm_type=llm_type,
        #         workdir=workdir
        #         # polybot_file_path=polybot_file_path

        #     )
        #     chat_result = autogen_system.initiate_chat(prompt_1a)

        #     print(f"Run {i+1} completed successfully!")


        print("Starting LAMMPS calculation...")
        prompt_1a = """Calculate the lattice constants and cohesive energy of Copper using use reactive potential LAMMPS. 
                    """ # If restarting """Continue from where we left off - what's the next step?""" #
        prompt_1b = """Calculate the lattice constants and cohesive energy for a Nickel-copper alloy using LAMMPS. Use existing potential file"""
        prompt_1c = """Write the lammps input script to Calculate the cohesive energy for a Nickel-copper alloy."""

        prompt_2a = """Compute the elastic constants of Silicon using LAMMPS."""
        prompt_2b = """Compute the elastic constants of a Nickel-copper alloy."""
        
        prompt_3a = """Calculate the phonon dispersion for Silicon"""
        prompt_3b =""" Calculate the phonon dispersion for Nickel-copper Alloy."""
        prompt_3c = """Search for Band path and symmetry points for phonon dispersion of Nickel-Copepr alloy"""

        prompt_4a = """Perform a melting point simulation for Silicon  using LAMMPS.""" #this is restarting Continue from where we left off - what's the next step? #"""
        prompt_4b = """Check the image melting_visualization.png for melting."""# <img melting_visualization.png> and <img full_melt_visualization.png> and comment on which one is a melted structure."""
        #"""Analyze the output of the melting point simulation and create the plots.""" #"""Perform a melting point simulation for a gold-copper alloy."""
        # prompt_3b = """Check the "melted_structure_visualization.png" and decide if the structure is fully melted or not.""" #
        # prompt_3 = """We have just performed a melting point calculation and the image generated from ovito
        # is in the workdir. Check the image and see if there are two phases or only one. If it is only one then
        # rerun the lammps simulation with co
        # rrected parameters"""

        chat_result = autogen_system.initiate_chat(prompt_1a)
        # print(f"Conversation token count: {autogen_system.count_tokens(chat_result)}")
        
        print("Run completed successfully!")

    except Exception as e:
        print(f"System failed: {e}")
        import traceback
        traceback.print_exc()