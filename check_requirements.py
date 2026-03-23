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
            # First, extract package name (remove version specifiers)
            package_name = req.split('>=')[0].split('<')[0].split('==')[0]
            package_name = package_name.replace('-', '_')  # Replace hyphens with underscores for import
            
            __import__(package_name)
            installed.append(req)
            print(f"✓ {req}")
        except ImportError:
            missing.append(req)
            print(f"✗ {req}")
    
    print("\n" + "-" * 50)
    print(f"Installed: {len(installed)}")
    print(f"Missing: {len(missing)}")
    
    if missing:
        print("\nMissing requirements:")
        for req in missing:
            print(f"  - {req}")
    else:
        print("\nAll requirements are installed!")

if __name__ == "__main__":
    check_requirements()