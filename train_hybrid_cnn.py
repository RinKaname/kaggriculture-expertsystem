"""Hybrid CNN + MLP Neurosymbolic RL Training Pipeline with CUDA Acceleration."""
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


def train_hybrid(opponent="starter", total_timesteps=1500, save_name="hybrid_cnn_weights"):
    print("=" * 65)
    print("[*] HYBRID CNN + MLP NEUROSYMBOLIC TRAINING")
    print("=" * 65)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[+] Device: {device.upper()}")
    if device == "cuda":
        print(f"[+] GPU: {torch.cuda.get_device_name(0)}")

    env = KaggricultureNeurosymbolicEnv(opponent=opponent)

    policy_kwargs = dict(
        features_extractor_class=HybridCNNFeaturesExtractor,
        features_extractor_kwargs=dict(cnn_output_dim=64, mlp_output_dim=64),
        net_arch=dict(pi=[64], vf=[64])
    )

    model = PPO(
        "MultiInputPolicy",
        env,
        policy_kwargs=policy_kwargs,
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

    print(f"\n[+] Training vs '{opponent}' for {total_timesteps} steps...")
    model.learn(total_timesteps=total_timesteps, progress_bar=True)

    model.save(save_name)
    print(f"\n[+] Training complete! Saved weights to: {save_name}.zip")
    return model


if __name__ == "__main__":
    train_hybrid(opponent="starter", total_timesteps=1500, save_name="hybrid_cnn_weights")
