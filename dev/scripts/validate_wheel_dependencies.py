#!/usr/bin/env python3
"""
Validate that wheel contains all required dependencies.
This prevents publishing packages with missing dependencies.
"""
import sys
import zipfile
from pathlib import Path
import re


def extract_dependencies_from_wheel(wheel_path):
    """Extract dependencies from wheel metadata."""
    dependencies = []
    
    with zipfile.ZipFile(wheel_path, 'r') as wheel:
        # Find METADATA file
        metadata_files = [f for f in wheel.namelist() if f.endswith('/METADATA')]
        if not metadata_files:
            raise ValueError(f"No METADATA file found in wheel: {wheel_path}")
        
        metadata_content = wheel.read(metadata_files[0]).decode('utf-8')
        
        # Extract Requires-Dist lines
        for line in metadata_content.split('\n'):
            if line.startswith('Requires-Dist:'):
                # Extract dependency (ignore extras conditions)
                dep = line.replace('Requires-Dist: ', '').split(';')[0].strip()
                if dep:  # Skip empty lines
                    dependencies.append(dep)
    
    return dependencies


def extract_dependencies_from_pyproject(pyproject_path):
    """Extract required dependencies from pyproject.toml."""
    dependencies = []
    
    with open(pyproject_path, 'r') as f:
        content = f.read()
    
    # Find dependencies section
    in_dependencies = False
    for line in content.split('\n'):
        line = line.strip()
        
        if line == 'dependencies = [':
            in_dependencies = True
            continue
        elif in_dependencies and line == ']':
            break
        elif in_dependencies and line.startswith('"'):
            # Extract dependency name, handle both trailing comma and closing bracket
            dep = line.strip('"').rstrip(',').rstrip('"').strip()
            if dep:  # Skip empty lines
                dependencies.append(dep)
    
    return dependencies


def normalize_dependency_name(dep_spec):
    """Extract package name from dependency specification."""
    # Remove version constraints and extras
    name = re.split(r'[<>=!\[]', dep_spec)[0].strip()
    return name.lower().replace('_', '-')


def main():
    """Validate wheel dependencies."""
    if len(sys.argv) != 2:
        print("Usage: python validate_wheel_dependencies.py <wheel_file>")
        sys.exit(1)
    
    wheel_path = Path(sys.argv[1])
    if not wheel_path.exists():
        print(f"Error: Wheel file not found: {wheel_path}")
        sys.exit(1)
    
    # Find pyproject.toml
    pyproject_path = wheel_path.parent.parent / 'pyproject.toml'
    if not pyproject_path.exists():
        print(f"Error: pyproject.toml not found: {pyproject_path}")
        sys.exit(1)
    
    print(f"🔍 Validating dependencies in {wheel_path.name}")
    print(f"📋 Using pyproject.toml: {pyproject_path}")
    
    try:
        # Extract dependencies
        wheel_deps = extract_dependencies_from_wheel(wheel_path)
        pyproject_deps = extract_dependencies_from_pyproject(pyproject_path)
        
        print(f"\n📦 pyproject.toml dependencies ({len(pyproject_deps)}):")
        for dep in sorted(pyproject_deps):
            print(f"  • {dep}")
        
        print(f"\n🎯 Wheel metadata dependencies ({len(wheel_deps)}):")
        for dep in sorted(wheel_deps):
            print(f"  • {dep}")
        
        # Normalize and compare
        pyproject_names = {normalize_dependency_name(dep) for dep in pyproject_deps}
        wheel_names = {normalize_dependency_name(dep) for dep in wheel_deps}
        
        # Check for missing dependencies
        missing_in_wheel = pyproject_names - wheel_names
        extra_in_wheel = wheel_names - pyproject_names
        
        print(f"\n🔍 Validation Results:")
        if missing_in_wheel:
            print(f"❌ Missing in wheel: {', '.join(sorted(missing_in_wheel))}")
            return False
        
        if extra_in_wheel:
            print(f"⚠️  Extra in wheel: {', '.join(sorted(extra_in_wheel))}")
        
        if pyproject_names == wheel_names:
            print("✅ All required dependencies present in wheel!")
            return True
        else:
            print("✅ Core dependencies match (extras are optional)")
            return True
            
    except Exception as e:
        print(f"❌ Error validating dependencies: {e}")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)