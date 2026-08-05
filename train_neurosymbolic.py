from stable_baselines3 import PPO
from src.neurosymbolic_env import KaggricultureNeurosymbolicEnv

def main():
    print("=" * 60)
    print("🚀 TRAINING KAGGRICULTURE NEUROSYMBOLIC PPO AGENT")
    print("=" * 60)

    # 1. Instantiate the Environment against the Final Boss opponent (main.py)
    env = KaggricultureNeurosymbolicEnv(opponent="main.py")

    # 2. Initialize Lightweight PPO Policy (MLP)
    # 30 steps = 1 full match, so n_steps=120 collects 4 matches per policy update
    model = PPO(
        "MlpPolicy",
        env,
        device="cuda", 
        learning_rate=3e-4,
        n_steps=120,
        batch_size=30,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        verbose=1
    )

    # 3. Train for 3,000 macro-steps (approx. 100 full matches)
    print("\nStarting training for 3,000 macro-steps (100 full matches)...")
    model.learn(total_timesteps=3000, progress_bar=True)

    # 4. Save the trained weights
    model.save("neurosymbolic_cfo_weights")
    print("\n" + "=" * 60)
    print("✅ Training complete! Saved weights to: neurosymbolic_cfo_weights.zip")
    print("=" * 60)

if __name__ == "__main__":
    main()
