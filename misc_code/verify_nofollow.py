
import os
import platform

def verify():
    print(f"Running on: {platform.system()}")
    
    # Test the logic used in the fix
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    print(f"Flags value: {flags}")
    
    # Try to open a file with these flags
    try:
        # Create a dummy file
        with open("test_file.txt", "w") as f:
            f.write("test")
            
        fd = os.open("test_file.txt", flags)
        print("Successfully opened file with flags.")
        os.close(fd)
        os.remove("test_file.txt")
    except Exception as e:
        print(f"FAILED to open file: {e}")

if __name__ == "__main__":
    verify()
