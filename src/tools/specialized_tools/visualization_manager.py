class VisualizationManager:
    """Handles visualization tasks using OVITO."""
    
    def __init__(self, workdir: str):
        self.workdir = workdir
    
    def render_lammps_dump(self, dump_file: str = "dump.output", 
                          output_image: str = "frame0.png",
                          frame_number: str = "last",
                          image_size: tuple = (1600, 1200)) -> str:
        """Render LAMMPS dump file using OVITO."""
        import os
        import sys
        
        try:
            # Import OVITO modules with error handling
            import warnings
            warnings.filterwarnings('ignore', message='.*OVITO.*PyPI')
            
            import ovito
            from ovito.io import import_file
            from ovito.modifiers import ComputePropertyModifier
            from ovito.vis import Viewport
            
            # Build file paths
            dump_path = os.path.join(self.workdir, dump_file)
            output_path = os.path.join(self.workdir, output_image)
            
            result = f"OVITO VISUALIZATION:\n"
            result += f"  OVITO version: {ovito.version}\n"
            result += f"  Python version: {sys.version.split()[0]}\n"
            result += f"  Dump file: {dump_path}\n"
            result += f"  Output image: {output_path}\n"
            
            # Check if dump file exists
            if not os.path.exists(dump_path):
                return result + f"ERROR: Dump file not found: {dump_path}"
            
            # Import the dump file
            pipe = import_file(dump_path, multiple_frames=True)

            # Get the total number of frames and handle "last" frame request
            total_frames = pipe.num_frames
            result += f"  Total frames available: {total_frames}\n"
            
            if frame_number == "last":
                frame_number = total_frames - 1
                result += f"Rendering LAST frame (frame {frame_number})\n"
            elif isinstance(frame_number, int):
                if frame_number >= total_frames:
                    return result + f"ERROR: Frame {frame_number} not available (max: {total_frames-1})"
                result += f"  Rendering frame {frame_number}\n"
            else:
                return result + f"ERROR: Invalid frame_number. Use integer or 'last'"
            
            # Get frame data
            frame_data = pipe.compute(frame_number)
            props = frame_data.particles.keys()
            
            result += f"  Frame {frame_number} properties: {list(props)}\n"
            
            # Handle radius property
            if 'Radius' in props:
                result += "  ✅ Radius column present – nothing to do\n"
            elif 'radius' in props:
                result += " Found 'radius' → mapping to 'Radius'\n"
                pipe.modifiers.append(ComputePropertyModifier(
                    output_property='Radius',
                    expressions='radius'))
            else:
                result += "No radius column → assigning default radius 1.0 Å\n"
                pipe.modifiers.append(ComputePropertyModifier(
                    output_property='Radius',
                    expressions='1.0'))
            
            # Add to scene and render
            pipe.add_to_scene()
            
            # Create viewport
            # vp = Viewport(type=Viewport.Type.Ortho) # get image of the top view
            vp = Viewport(type=Viewport.Type.Front) # get image of the front view
            vp.camera_dir = (0.0, -1.0, 0.0)  
            vp.zoom_all()
            
            # Render image
            vp.render_image(
                filename=output_path,
                size=image_size,
                frame=frame_number,
                background=(1, 1, 1)  # White background
            )
            
            # Verify output
            if os.path.exists(output_path):
                size_bytes = os.path.getsize(output_path)
                result += f"SUCCESS: Rendered {output_image} ({size_bytes} bytes)\n"
                result += f"Image size: {image_size[0]}x{image_size[1]} pixels"
            else:
                result += f"ERROR: Output image was not created"
            
            return result
            
        except ImportError as e:
            return f"OVITO import error: {str(e)}\n" \
                   f"Install OVITO with: pip install ovito"
        except Exception as e:
            return f"Visualization error: {str(e)}"
    
    def render_multiple_frames(self, dump_file: str = "dump.output",
                              frame_count: int = 5,
                              output_prefix: str = "frame") -> str:
        """Render multiple frames from dump file."""
        results = []
        
        for frame in range(frame_count):
            output_name = f"{output_prefix}_{frame:03d}.png"
            result = self.render_lammps_dump(dump_file, output_name, frame)
            results.append(f"Frame {frame}: {result.split('SUCCESS:')[-1] if 'SUCCESS:' in result else 'Failed'}")
        
        return "MULTIPLE FRAME RENDERING:\n" + "\n".join(results)
    
    def create_animation(self, dump_file: str = "dump.output", 
                        output_gif: str = "animation.gif") -> str:
        """Create animation from dump file frames."""
        import os
        
        try:
            # First, render multiple frames
            frame_result = self.render_multiple_frames(dump_file, frame_count=10)
            
            # Try to create GIF using imageio (if available)
            try:
                import imageio
                
                # Collect frame files
                frame_files = []
                for i in range(10):
                    frame_file = os.path.join(self.workdir, f"frame_{i:03d}.png")
                    if os.path.exists(frame_file):
                        frame_files.append(frame_file)
                
                if frame_files:
                    # Read images and create GIF
                    images = [imageio.imread(f) for f in frame_files]
                    gif_path = os.path.join(self.workdir, output_gif)
                    imageio.mimsave(gif_path, images, duration=0.5)
                    
                    return f"🎬 Animation created: {output_gif}\n" \
                           f"📁 Frames used: {len(frame_files)}\n" \
                           f"{frame_result}"
                else:
                    return f"No frame files found for animation\n{frame_result}"
                    
            except ImportError:
                return f"Animation requires imageio: pip install imageio\n" \
                       f"Individual frames rendered:\n{frame_result}"
                       
        except Exception as e:
            return f" error: {str(e)}"
    
    def analyze_dump_file(self, dump_file: str = "dump.output") -> str:
        """Analyze dump file structure and content."""
        import os
        
        dump_path = os.path.join(self.workdir, dump_file)
        
        if not os.path.exists(dump_path):
            return f"Dump file not found: {dump_path}"
        
        try:
            # Try to import OVITO and analyze
            import ovito
            from ovito.io import import_file
            
            pipe = import_file(dump_path, multiple_frames=True)
            
            # Get basic info
            total_frames = pipe.num_frames
            frame0 = pipe.compute(0)
            
            props = list(frame0.particles.keys())
            atom_count = frame0.particles.count
            
            # Get simulation box info
            box = frame0.cell
            
            result = f"📊 DUMP FILE ANALYSIS:\n"
            result += f"  File: {dump_file}\n"
            result += f"  Total frames: {total_frames}\n"
            result += f"  Atoms per frame: {atom_count}\n"
            result += f"  Particle properties: {props}\n"
            result += f"  Simulation box: {box.matrix[0,0]:.2f} x {box.matrix[1,1]:.2f} x {box.matrix[2,2]:.2f}\n"
            
            # File size
            file_size = os.path.getsize(dump_path)
            result += f"  File size: {file_size} bytes ({file_size/1024:.1f} KB)\n"
            
            return result
            
        except ImportError:
            # Fallback: basic file analysis without OVITO
            file_size = os.path.getsize(dump_path)
            
            with open(dump_path, 'r') as f:
                lines = f.readlines()
            
            return f"BASIC DUMP FILE ANALYSIS:\n" \
                   f"  File: {dump_file}\n" \
                   f"  File size: {file_size} bytes\n" \
                   f"  Total lines: {len(lines)}\n" \
                   f"  Install OVITO for detailed analysis"
                   
        except Exception as e:
            return f"Analysis error: {str(e)}"
        