import pyvista as pv
import gzip # For handling .gz

# How to run this script: .\environments\my-python313-venv-win\Scripts\python.exe misc_code\pyvista_geometry_loading.py

# If it's a compressed file, read the decompressed content first
# Using raw strings or forward slashes to avoid escape character issues
try:
    with gzip.open(r'E:\Misc\FOAMFlask\run_folder\fluid\aerofoilNACA0012Steady\constant\geometry\NACA0012.obj.gz', 'rb') as f:
        print("Reading compressed file...")
        # Write to a temporary file because PyVista often prefers file paths or specific file-like objects for some readers
        # But for .obj, pv.read might expect a file path. Let's try writing to a temp .obj file.
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.obj', delete=False) as tmp:
            tmp.write(f.read())
            tmp_path = tmp.name
            
    print(f"Decompressed to temporary file: {tmp_path}")
    
    mesh = pv.read(tmp_path)
    print("Successfully read mesh file.")
    
    mesh.plot()
    
    # Cleanup
    try:
        os.remove(tmp_path)
        print("Temporary file cleaned up.")
    except:
        pass
        
except Exception as e:
    print(f"Error reading or plotting mesh: {e}")
