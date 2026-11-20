# Kaggle GPU TEST (Plan 3, M3 step 1): render one library still on Kaggle's FREE GPU and time it.
# Runs as a Kaggle "script" kernel (cloud/kaggle/out/tc-render-test/, pushed with `kaggle kernels push`),
# or paste it into a notebook cell. Needs: Accelerator = GPU, Internet = On.
# Output (the kernel's Output tab / `kaggle kernels output`): render.png + blender.log.
import os, subprocess, time
REPO = "https://github.com/Leo-emp/Timeless-Compass.git"      # public repo, no secrets
BRANCH = "cinematic-agent"
SCENE, SAMPLES = "salamis_set_test.py", "128"
CODE, TOOLS, OUT = "/kaggle/tmp/tc", "/kaggle/tmp/tools", "/kaggle/working"   # /kaggle/tmp is not saved as output

subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv"])
subprocess.run(["git", "clone", "--depth", "1", "-b", BRANCH, REPO, CODE], check=True)
os.chdir(CODE)
t0 = time.time()
blender = subprocess.run(["bash", "cloud/setup_blender_linux.sh", TOOLS],
                         capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
print(f"INSTALL SECONDS: {time.time() - t0:.0f}")

env = dict(os.environ, TC_GPU="1")                     # Cycles on the GPU (OptiX/CUDA), see blender/lib/common.py
t0 = time.time()                                       # measured render time = first real number for M3
r = subprocess.run([blender, "-b", "--python", f"blender/scenes/{SCENE}", "--", f"{OUT}/render.png", SAMPLES],
                   env=env, capture_output=True, text=True)
with open(f"{OUT}/blender.log", "w") as f:            # full Blender log in the output
    f.write(r.stdout + r.stderr)
keep = [ln for ln in r.stdout.splitlines() if any(w in ln.upper() for w in ("GPU", "OPTIX", "CUDA", "SAVED", "ERROR"))]
print("\n".join(keep[-30:]))
print(f"RENDER SECONDS: {time.time() - t0:.0f}  (exit {r.returncode}, {SAMPLES} samples, 1280x544)")
assert os.path.exists(f"{OUT}/render.png"), "no render: see blender.log in the output"
print(f"done -> {OUT}/render.png")
