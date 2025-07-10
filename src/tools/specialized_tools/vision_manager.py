import openai
import base64
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..', '..')
sys.path.insert(0, src_dir)

try:
    from config.settings import OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        raise ImportError("Could not find OPENAI_API_KEY in config.settings or environment variables")


class VisionManager:
    """Manager class for analyzing LAMMPS simulation images."""
    
    def __init__(self, workdir: str):
        """
        Initialize the VisionManager.
        
        Args:
            workdir: Working directory where image files are located
        """
        self.workdir = workdir
        self.api_key = OPENAI_API_KEY
    
    def _resolve_image_path(self, image_path: str) -> str:
        """
        Resolve image path to absolute path.
        
        Args:
            image_path: Relative or absolute path to image
            
        Returns:
            Absolute path to image
            
        Raises:
            FileNotFoundError: If image file cannot be found
        """

        if os.path.isabs(image_path):
            if os.path.exists(image_path):
                return image_path
            else:
                raise FileNotFoundError(f"Image file not found: {image_path}")
        
        workdir_path = os.path.join(self.workdir, image_path)
        if os.path.exists(workdir_path):
            return workdir_path
        
        possible_paths = [
            image_path,  
            os.path.join(os.getcwd(), image_path), 
            os.path.join(os.path.dirname(__file__), image_path),  
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        all_tried = [workdir_path] + possible_paths
        raise FileNotFoundError(f"Image file not found. Tried paths: {all_tried}")
    
    def _encode_image(self, image_path: str) -> str:
        """
        Encode image to base64 string.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image string
        """
        full_path = self._resolve_image_path(image_path)
        
        with open(full_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def analyze_melting_point_simulation(self, image_path: str) -> str:
        """
        Analyze LAMMPS melting point simulation image.
        
        Args:
            image_path: Path to the simulation image (relative to workdir or absolute)
            
        Returns:
            String description of the analysis
        """
        try:
            openai.api_key = self.api_key
            
            # Encode the image
            base64_image = self._encode_image(image_path)
            
            response = openai.chat.completions.create(
                model="o3",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """
You are a Vision Agent specialized in analyzing molecular dynamics simulation visualizations created by OVITO.

For a melting point simulation, please decide if the structure is fully melted or not.
For a fully melted structure, look for:
- Random distribution: The atomic positions appear to be randomly distributed throughout the entire image. There is no discernible long-range order or pattern in the arrangement of atoms.
- Absence of lattice structures: There are no visible lattice structures or periodic patterns that would indicate a crystalline arrangement. The atoms are positioned in a disordered manner across the entire image.
- Non-aligned packing: The atoms are closely packed but not aligned in any regular manner. This is characteristic of a liquid-like structure where atoms can move freely.
- Disordered, fluid-like appearance: The overall arrangement looks disordered and fluid-like, consistent with a fully melted state. There is a uniform randomness to the atomic positions across the entire image.
- No ordered regions: There are no visible regions of ordered clusters or rows of atoms that would suggest partial crystallinity. The disorder is consistent throughout the image.
- ALWAYS ignore colour coding

If the structure is not fully melted, recommend parameter adjustments:
- Increase temperature range
- Extend simulation time (increase timesteps)
- Adjust heating rate (slower heating)
- Check potential parameters

Review your assessment carefully before concluding and providing an answer.
                                """
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                # max_tokens=200,
            )
            
            return response.choices[0].message.content
            
        except FileNotFoundError as e:
            return f"{str(e)}"
        except Exception as e:
            return f"Vision analysis failed: {str(e)}"
    
    def analyze_solid_liquid_interface(self, image_path: str) -> str:
        """
        Analyze solid-liquid interface in simulation image.
        
        Args:
            image_path: Path to the simulation image (relative to workdir or absolute)
            
        Returns:
            String description of the interface analysis
        """
        try:
            openai.api_key = self.api_key
            
            # Encode the image
            base64_image = self._encode_image(image_path)
            
            response = openai.chat.completions.create(
                model= "gpt-4o", # "o3", # #gpt-4o
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """
You are a Vision Agent specialized in analyzing molecular dynamics simulation visualizations created by OVITO.

Check if there are two phases shown in the image, such as a solid-liquid interface. 
We need to have a structure that is approximatelly around 50:50 solid-liquid. So almost half of the structure should look disordered and liquid-like,
while the other half should look crystalline and solid-like.
If it is not approximately 50:50 then we need to resubmit the LAMMPS simulation and freeze or unfreeze atoms.
                                """
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                # max_tokens=200,
            )        
            return response.choices[0].message.content
            
        except FileNotFoundError as e:
            return f"{str(e)}"
        except Exception as e:
            return f"Vision analysis failed: {str(e)}"
        

    def analyze_melting_point_plots(self, image_path: str) -> str:
        """
        Analyze the melting point simulation plots.
        
        Args:
            image_path: Path to the simulation image (relative to workdir or absolute)
            
        Returns:
            String description of the analysis
        """
        try:
            openai.api_key = self.api_key
            
            # Encode the image
            base64_image = self._encode_image(image_path)
            
            response = openai.chat.completions.create(
                model="o3",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """
You are a Vision Agent specialized in analyzing molecular dynamics plots for melting point calculation.

Analyze the potential energy vs temperature and heat capacity vs temperature plots (usually named melting_analysis.png):

1. **Heat Capacity Analysis**: Verify there is a clear peak in the heat capacity curve, indicating a phase transition
2. **Energy Correlation**: Check if the heat capacity peak temperature corresponds to an inflection point or steeper slope change in the potential energy curve (not necessarily a sharp discontinuous jump, as melting transitions can be gradual)
3. **Peak Quality**: Ensure the heat capacity peak is well-defined and not at the boundary of the temperature range
4. **Coverage Assessment**: If no clear peak exists, or if the peak occurs near the temperature boundaries, recommend extending the simulation temperature range

Note: For crystalline melting, expect a gradual S-shaped increase in potential energy rather than an abrupt discontinuous jump.

                                """
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                # max_tokens=200,
            )
            
            return response.choices[0].message.content
            
        except FileNotFoundError as e:
            return f"{str(e)}"
        except Exception as e:
            return f"Vision analysis failed: {str(e)}"
    
    def list_images_in_workdir(self) -> str:
        """
        List all image files in the working directory.
        
        Returns:
            String listing of image files found
        """
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
        
        try:
            files = os.listdir(self.workdir)
            image_files = [f for f in files if any(f.lower().endswith(ext) for ext in image_extensions)]
            
            if image_files:
                result = f"📷 Found {len(image_files)} image files in {self.workdir}:\n"
                for img in image_files:
                    file_path = os.path.join(self.workdir, img)
                    file_size = os.path.getsize(file_path)
                    result += f"  📄 {img} ({file_size} bytes)\n"
                return result
            else:
                return f"No image files found in {self.workdir}"
                
        except Exception as e:
            return f"Error listing images: {str(e)}"


# For backward compatibility, provide the standalone functions
def analyze_melting_point_simulation_image(image_path: str, api_key: str = None, workdir: str = None) -> str:
    """Standalone function for backward compatibility."""
    if workdir is None:
        workdir = os.getcwd()
    
    manager = VisionManager(workdir)
    if api_key:
        manager.api_key = api_key
    
    return manager.analyze_melting_point_simulation(image_path)


def analyze_solid_liquid_interface(image_path: str, api_key: str = None, workdir: str = None) -> str:
    """Standalone function for backward compatibility."""
    if workdir is None:
        workdir = os.getcwd()
    
    manager = VisionManager(workdir)
    if api_key:
        manager.api_key = api_key
    
    return manager.analyze_solid_liquid_interface(image_path)


def analyze_melting_point_plots(image_path: str, api_key: str = None, workdir: str = None) -> str:
    """Standalone function for backward compatibility."""
    if workdir is None:
        workdir = os.getcwd()
    
    manager = VisionManager(workdir)
    if api_key:
        manager.api_key = api_key
    
    return manager.analyze_melting_point_plots(image_path)


if __name__ == "__main__":

    workdir = r"C:\Users\kvriz\Desktop\LAMMPS-Agents\ovito_frames_benchmark"
    manager = VisionManager(workdir)
    
    # print(manager.list_images_in_workdir())
    # result = manager.analyze_solid_liquid_interface("test_frame_1.png")
    result = manager.analyze_melting_point_simulation("test_frame_10.png") # melt_visualization.png  #melting_visualization.png 
    print(f"Analysis result: {result}")