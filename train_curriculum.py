"""3-Stage Curriculum Learning for Kaggriculture Neurosymbolic RL Agent."""
from torch import cpu
import torch
from tqdm import tqdm
from stable_baselines3 import PPO
from src.neurosymbolic_env import KaggricultureNeurosymbolicEnv

def train_curriculum():
    print("=" * 65)
    print("🎓 3-STAGE CURRICULUM LEARNING PIPELINE")
    print("=" * 65)

    device = "cuda" if torch.cuda.is_available() else "auto"
    print(f"⚡ Hardware Accelerator: {device.upper()}")
    if device == "cuda":
        print(f"🎮 GPU Device: {torch.cuda.get_device_name(0)}")

    # -------------------------------------------------------------
    # STAGE 1: Grade School vs Starter Baseline (1,500 timesteps)
    # -------------------------------------------------------------
    print("\n[+] STAGE 1/3: Training vs 'starter' baseline (1,500 steps / 50 matches)...")
    env_stage1 = KaggricultureNeurosymbolicEnv(opponent="starter")
    model = PPO(
        "MlpPolicy",
        env_stage1,
        device=device,
        learning_rate=5e-4,
        n_steps=120,
        batch_size=30,
        n_epochs=10,
        gamma=0.99,
        clip_range=0.2,
        ent_coef=0.02,
        verbose=1
    )
    model.learn(total_timesteps=1500, progress_bar=True)
    model.save("curriculum_stage1")
    print("✅ Stage 1 complete! Saved to curriculum_stage1.zip")

    # -------------------------------------------------------------
    # STAGE 2: High School vs Archive/baseline.py (1,500 timesteps)
    # -------------------------------------------------------------
    print("\n[+] STAGE 2/3: Transferring to vs 'Archive/baseline.py' (1,500 steps)...")
    env_stage2 = KaggricultureNeurosymbolicEnv(opponent="Archive/baseline.py")
    model.set_env(env_stage2)
    model.learning_rate = 3e-4
    model.learn(total_timesteps=1500, progress_bar=True, reset_num_timesteps=False)
    model.save("curriculum_stage2")
    print("✅ Stage 2 complete! Saved to curriculum_stage2.zip")

    # -------------------------------------------------------------
    # STAGE 3: Grandmaster Arena vs main.py (1,500 timesteps)
    # -------------------------------------------------------------
    print("\n[+] STAGE 3/3: Fine-Tuning vs Final Boss 'main.py' (1,500 steps)...")
    env_stage3 = KaggricultureNeurosymbolicEnv(opponent="main.py")
    model.set_env(env_stage3)
    model.learning_rate = 1e-4
    model.learn(total_timesteps=1500, progress_bar=True, reset_num_timesteps=False)
    model.save("neurosymbolic_cfo_weights")
    print("\n" + "=" * 65)
    print("🏆 ALL 3 CURRICULUM STAGES COMPLETE!")
    print("Saved final model to: neurosymbolic_cfo_weights.zip")
    print("=" * 65)

if __name__ == "__main__":
    train_curriculum()
