"""3-Stage Curriculum Learning for Kaggriculture Hybrid CNN + MLP RL Agent."""
import torch
import torch.nn as nn
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from src.neurosymbolic_env import KaggricultureNeurosymbolicEnv


class HybridCNNFeaturesExtractor(BaseFeaturesExtractor):
    """
    Two-branch Feature Extractor:
    1. Spatial CNN: Conv2D layers for the (5, 10, 10) farm layout.
    2. Economic MLP: Dense layers for the (18,) market and cash features.
    """
    def __init__(self, observation_space: gym.spaces.Dict, cnn_output_dim: int = 64, mlp_output_dim: int = 64):
        super().__init__(observation_space, features_dim=cnn_output_dim + mlp_output_dim)

        # Spatial CNN Branch (Channels: Unlocked, Weed, Crop, Animals, Workers)
        self.cnn = nn.Sequential(
            nn.Conv2d(in_channels=5, out_channels=16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(32 * 10 * 10, cnn_output_dim),
            nn.ReLU()
        )

        # Economic MLP Branch (Prices, Cash, Day/Hour, Shed Inventory)
        self.mlp = nn.Sequential(
            nn.Linear(18, 64),
            nn.ReLU(),
            nn.Linear(64, mlp_output_dim),
            nn.ReLU()
        )

    def forward(self, observations):
        spatial_emb = self.cnn(observations["spatial"])
        economy_emb = self.mlp(observations["economy"])
        return torch.cat([spatial_emb, economy_emb], dim=1)


def train_curriculum():
    print("=" * 65)
    print("[*] 3-STAGE HYBRID CNN + MLP CURRICULUM PIPELINE")
    print("=" * 65)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[+] Hardware Accelerator: {device.upper()}")
    if device == "cuda":
        print(f"[+] GPU Device: {torch.cuda.get_device_name(0)}")

    policy_kwargs = dict(
        features_extractor_class=HybridCNNFeaturesExtractor,
        features_extractor_kwargs=dict(cnn_output_dim=64, mlp_output_dim=64),
        net_arch=dict(pi=[64], vf=[64])
    )

    # -------------------------------------------------------------
    # STAGE 1: Grade School vs Starter Baseline (1,500 timesteps)
    # -------------------------------------------------------------
    print("\n[+] STAGE 1/3: Training vs 'starter' baseline (1,500 steps / 50 matches)...")
    env_stage1 = KaggricultureNeurosymbolicEnv(opponent="starter")
    model = PPO(
        "MultiInputPolicy",
        env_stage1,
        policy_kwargs=policy_kwargs,
        device=device,
        learning_rate=5e-4,
        n_steps=240,
        batch_size=60,
        n_epochs=10,
        gamma=0.99,
        clip_range=0.2,
        ent_coef=0.02,
        verbose=1
    )
    model.learn(total_timesteps=1500, progress_bar=True)
    model.save("curriculum_stage1")
    print("[+] Stage 1 complete! Saved to curriculum_stage1.zip")

    # -------------------------------------------------------------
    # STAGE 2: High School vs Archive/baseline.py (1,500 timesteps)
    # -------------------------------------------------------------
    print("\n[+] STAGE 2/3: Transferring to vs 'Archive/baseline.py' (1,500 steps)...")
    env_stage2 = KaggricultureNeurosymbolicEnv(opponent="Archive/baseline.py")
    model.set_env(env_stage2)
    model.learning_rate = 3e-4
    model.learn(total_timesteps=5000, progress_bar=True, reset_num_timesteps=False)
    model.save("curriculum_stage2")
    print("[+] Stage 2 complete! Saved to curriculum_stage2.zip")

    # -------------------------------------------------------------
    # STAGE 3: Grandmaster Arena vs main.py (1,500 timesteps)
    # -------------------------------------------------------------
    print("\n[+] STAGE 3/3: Fine-Tuning vs Final Boss 'main.py' (1,500 steps)...")
    env_stage3 = KaggricultureNeurosymbolicEnv(opponent="main.py")
    model.set_env(env_stage3)
    model.learning_rate = 1e-4
    model.learn(total_timesteps=10000, progress_bar=True, reset_num_timesteps=False)
    model.save("neurosymbolic_cfo_weights")
    print("\n" + "=" * 65)
    print("[+] ALL 3 CURRICULUM STAGES COMPLETE!")
    print("Saved final model to: neurosymbolic_cfo_weights.zip")
    print("=" * 65)


if __name__ == "__main__":
    train_curriculum()
