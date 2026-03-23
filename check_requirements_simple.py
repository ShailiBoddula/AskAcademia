import subprocess
import sys

def check_requirements():
    # Read requirements from requirements.txt
    with open('requirements.txt', 'r') as f:
        requirements = [line.strip() for line in f if line.strip()]
    
    print("Checking requirements:")
    print("-" * 50)
    
    installed = []
    missing = []
    
    for req in requirements:
        try:
            # Try to import the package
            package_name = req.split('>=')[0].split('<')[0].split('==')[0]
            package_name = package_name.replace('-', '_')
            
            __import__(package_name)
            installed.append(req)
            print("OK: " + req)
        except ImportError:
            missing.append(req)
            print("MISSING: " + req)
    
    print("\n" + "-" * 50)
    print("Installed: " + str(len(installed)))
    print("Missing: " + str(len(missing)))
    
    if missing:
        print("\nMissing requirements:")
        for req in missing:
            print("  - " + req)
    else:
        print("\nAll requirements are installed!")

if __name__ == "__main__":
    check_requirements()