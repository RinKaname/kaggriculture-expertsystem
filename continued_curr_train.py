"""Resume and Continue Training for Kaggriculture Hybrid CNN + MLP RL Agent."""
import os
import torch
import torch.nn as nn
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from src.neurosymbolic_env import KaggricultureNeurosymbolicEnv
from train_hybrid_cnn import HybridCNNFeaturesExtractor


def continue_training(
    weights_path="neurosymbolic_cfo_weights.zip",
    opponent="main.py",
    extra_timesteps=3000,
    learning_rate=1e-4,
    save_name="neurosymbolic_cfo_weights"
):
    print("=" * 65)
    print("[*] CONTINUED TRAINING PIPELINE (RESUME FROM CHECKPOINT)")
    print("=" * 65)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[+] Hardware Accelerator: {device.upper()}")
    if device == "cuda":
        print(f"[+] GPU Device: {torch.cuda.get_device_name(0)}")

    if not os.path.exists(weights_path):
        # Check without .zip extension
        if os.path.exists(weights_path + ".zip"):
            weights_path = weights_path + ".zip"
        else:
            raise FileNotFoundError(
                f"Cannot find checkpoint: {weights_path}. Please run train_curriculum.py first!"
            )

    print(f"\n[+] Loading existing model weights from: {weights_path}")
    env = KaggricultureNeurosymbolicEnv(opponent=opponent)

    # Load existing PPO policy and attach new environment & device
    model = PPO.load(weights_path, env=env, device=device)
    model.learning_rate = learning_rate

    print(f"[+] Resuming training vs '{opponent}' for an additional {extra_timesteps:,} steps...")
    print(f"[+] Learning Rate: {learning_rate}")
    
    # reset_num_timesteps=False preserves the step counter & progress
    model.learn(total_timesteps=extra_timesteps, progress_bar=True, reset_num_timesteps=False)

    model.save(save_name)
    print("\n" + "=" * 65)
    print(f"[+] Continued training complete! Saved updated model to: {save_name}.zip")
    print("=" * 65)
    return model


if __name__ == "__main__":
    # Continue training against main.py for 3,000 steps (100 full matches)
    continue_training(
        weights_path="neurosymbolic_cfo_weights.zip",
        opponent="main.py",
        extra_timesteps=3000,
        learning_rate=1e-4,
        save_name="neurosymbolic_cfo_weights"
    )
