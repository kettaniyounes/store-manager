import os
import shutil

def delete_pycache_folders(base_dir):
    for root, dirs, files in os.walk(base_dir):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                pycache_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(pycache_path)
                    print(f"Deleted: {pycache_path}")
                except Exception as e:
                    print(f"Failed to delete {pycache_path}: {e}")

if __name__ == "__main__":
    project_dir = os.path.dirname(os.path.abspath(__file__))
    delete_pycache_folders(project_dir)