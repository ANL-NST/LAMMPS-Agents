# All the LAMMPS agents
from autogen.agents.experimental import WebSurferAgent
from autogen import UserProxyAgent, ConversableAgent
from config.settings import OPENAI_API_KEY, anthropic_api_key
from autogen.agentchat.contrib.multimodal_conversable_agent import MultimodalConversableAgent

class AgentFactory:
    """Factory class for creating AutoGen agents with proper configuration.
    This class is not registering functions, but rather creating agent instances."""

    def __init__(self, llm_config, executor, workdir):
        """
        Initialize the agent factory.
        
        Args:
            llm_config: LLM configuration dictionary
            executor: Code executor instance
            workdir: Working directory path
        """
        self.llm_config = llm_config
        self.executor = executor
        self.workdir = workdir
    
    def create_all_agents(self):
        """
        Create all agents and return them as a dictionary.
        
        Returns:
            dict: Dictionary of agent name -> agent instance
        """
        agents = {}
        
        # Create agents
        agents['websurfer'] = self.create_websurfer_agent()
        agents['admin'] = self.create_admin_agent(agents['websurfer'])
        agents['structure'] = self.create_structure_agent()
        agents['potential'] = self.create_potential_agent()
        agents['lammps'] = self.create_lammps_agent()
        agents['lammps_elastic'] = self.create_lammps_elastic_agent()  
        agents['reviewer'] = self.create_reviewer_agent()
        agents['hpc'] = self.create_hpc_agent()
        agents['analysis'] = self.create_analysis_agent()
        agents['phonopy'] = self.create_phonopy_agent() 
        # agents['vision'] = self.create_vision_agent()       
        
        return agents
    
    def create_websurfer_agent(self):
        """Create WebSurfer agent with specific LLM config."""
        from src.system_messages.websurfer_system_message import WEBSURFER_SYSTEM_PROMPT
        
        # WebSurfer needs different LLM config (o3 not supported)
        websurfer_llm_config = {
            "model": "gpt-4.1",
            'api_key': OPENAI_API_KEY,
            'temperature': 0,
        }
        
        return WebSurferAgent(
            name="WebSurfer",
            llm_config=websurfer_llm_config,
            web_tool="browser_use",
            system_message=WEBSURFER_SYSTEM_PROMPT,
        )
    
    def create_admin_agent(self, websurfer_agent):
        """Create admin agent and register WebSurfer tools."""
        admin = UserProxyAgent(
            name="admin",
            is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
            human_input_mode="ALWAYS",
            system_message="Admin agent. You coordinate the workflow and provide feedback. Return 'TERMINATE' when done.",
            llm_config=self.llm_config,
            code_execution_config={"executor": self.executor},
        )
        
        # Register WebSurfer tools with admin
        for tool in websurfer_agent.tools:
            tool.register_for_execution(admin)
        
        return admin
    
    def create_structure_agent(self):
        """Create structure creation agent."""
        from src.system_messages.structure_creator_system_message import StructureCreator_SYSTEM_PROMPT
        
        return ConversableAgent(
            name="StructureCreator",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False,
            system_message=StructureCreator_SYSTEM_PROMPT
        )
    
    def create_potential_agent(self):
        """Create potential management agent."""
        from src.system_messages.potential_manager_system_message import POTENTIAL_MANAGER_SYSTEM_PROMPT
        
        return ConversableAgent(
            name="PotentialManager",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False,
            system_message=POTENTIAL_MANAGER_SYSTEM_PROMPT
        )
    
    def create_lammps_agent(self):
        """Create LAMMPS input creator agent."""
        from src.system_messages.lammps_input_creator_message import LAMMPS_INPUT_CREATOR_SYSTEM_PROMPT
        lammps_llm_config = {
            "model": "o3",
            'api_key': OPENAI_API_KEY,
            # 'temperature': 0,
        }
        return ConversableAgent(
            name="LAMMPSInputCreator",
            llm_config=self.llm_config,
            human_input_mode="ALWAYS",
            code_execution_config=False,
            system_message=LAMMPS_INPUT_CREATOR_SYSTEM_PROMPT
        )
    
    def create_lammps_elastic_agent(self):
        """Create LAMMPS simulations for the calculation of elastic constants."""
        from src.system_messages.lammps_elastic_message import LAMMPS_ELASTIC_SYSTEM_PROMPT        
        return ConversableAgent(
            name="LAMMPSElasticContants",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False,
            system_message=LAMMPS_ELASTIC_SYSTEM_PROMPT
        )

    def create_reviewer_agent(self):
        """Create LAMMPS input reviewer agent."""
        from src.system_messages.lammps_input_reviewer_message import LAMMPS_INPUT_REVIEWER_SYSTEM_PROMPT
        
        return ConversableAgent(
            name="LAMMPSReviewer",
            llm_config=self.llm_config,
            human_input_mode="ALWAYS",
            code_execution_config=False,
            system_message=LAMMPS_INPUT_REVIEWER_SYSTEM_PROMPT
        )
    
    def create_hpc_agent(self):
        """Create HPC execution agent."""
        from src.system_messages.hpc_manager_system_message import HPC_MANAGER_SYSTEM_PROMPT
        
        return ConversableAgent(
            name="HPCExecutor",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False,
            system_message=HPC_MANAGER_SYSTEM_PROMPT
        )
    
    def create_analysis_agent(self):
        """Create results analysis agent."""
        from src.system_messages.results_analyser_system_message import RESULTS_ANALYZER_SYSTEM_PROMPT
        
        return ConversableAgent(
            name="ResultsAnalyzer",
            llm_config=self.llm_config,
            human_input_mode="ALWAYS",
            code_execution_config=False,
            system_message=RESULTS_ANALYZER_SYSTEM_PROMPT
        )
    
    def create_phonopy_agent(self):
        """Create phonopy calculation agent."""
        from src.system_messages.phonopy_system_message import PHONOPY_SYSTEM_PROMPT
        
        return ConversableAgent(
            name="PhonopyCalculator",
            llm_config=self.llm_config,
            human_input_mode="ALWAYS",
            code_execution_config=False,
            system_message=PHONOPY_SYSTEM_PROMPT
        )
  

    def get_agent_list(self, agents_dict):
        """
        Get list of agents for group chat in correct order.
        
        Args:
            agents_dict: Dictionary of agents from create_all_agents()
            
        Returns:
            list: Ordered list of agents for group chat
        """
        return [
            agents_dict['admin'],
            agents_dict['structure'],
            agents_dict['potential'],
            agents_dict['lammps'],
            agents_dict['lammps_elastic'],
            agents_dict['reviewer'],
            agents_dict['hpc'],
            agents_dict['analysis'],
            agents_dict['websurfer'],
            agents_dict['phonopy'],
            # agents_dict['vision']
        ]
    
    @staticmethod
    def create_factory(llm_config, executor, workdir):
        """
        Static factory method to create AgentFactory instance.
        
        Args:
            llm_config: LLM configuration dictionary
            executor: Code executor instance  
            workdir: Working directory path
            
        Returns:
            AgentFactory: Configured factory instance
        """
        return AgentFactory(llm_config, executor, workdir)