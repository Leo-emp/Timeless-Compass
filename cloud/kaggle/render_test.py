# Kaggle notebook cell (Plan 3, M3 step 1): render one library still on Kaggle's FREE GPU.
# Settings: Accelerator = GPU T4 x2, Internet = On. Paste this whole cell and run it.
# Output: /kaggle/working/render.png (download from the notebook's Output tab).
import os, subprocess
REPO = "https://github.com/Leo-emp/Timeless-Compass.git"      # public repo, no secrets
BRANCH = "cinematic-agent"
SCENE, SAMPLES = "salamis_set_test.py", "128"
subprocess.run(["git", "clone", "--depth", "1", "-b", BRANCH, REPO, "/kaggle/working/tc"], check=True)
os.chdir("/kaggle/working/tc")
blender = subprocess.run(["bash", "cloud/setup_blender_linux.sh", "/kaggle/working/tools"],
                         capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
env = dict(os.environ, TC_GPU="1")                               # Cycles on the GPU (OptiX/CUDA)
subprocess.run([blender, "-b", "--python", f"blender/scenes/{SCENE}", "--", "/kaggle/working/render.png", SAMPLES], env=env, check=True)
print("done -> /kaggle/working/render.png")
