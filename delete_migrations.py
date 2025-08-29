import os

# The name of the virtual environment directory to exclude
VENV_FOLDER = "venv"

# Get the absolute path of the directory where the script is running
project_root = os.path.dirname(os.path.abspath(__file__))

print(f"Searching for migration files in: {project_root}")
print(f"Excluding any directory named: {VENV_FOLDER}")

for root, dirs, files in os.walk(project_root):
    # Check if the venv folder is in the current path and skip it
    if os.path.join(project_root, VENV_FOLDER) in root:
        continue

    # Process only if the directory is named 'migrations'
    if os.path.basename(root) == "migrations":
        for file in files:
            # Keep the __init__.py file to maintain the directory as a Python package
            if file != "__init__.py" and file.endswith((".py", ".pyc")):
                file_path = os.path.join(root, file)
                print(f"Deleting migration file: {file_path}")
                os.remove(file_path)

print("\nMigration file deletion complete.")