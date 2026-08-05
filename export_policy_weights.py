"""Export compact PyTorch and NumPy weights from trained PPO checkpoint for zero-dependency inference."""
import zipfile
import torch
import numpy as np

def export_weights(zip_path="psro_oracle_weights.zip", out_pt="policy_weights.pt", out_npz="policy_weights.npz"):
    with zipfile.ZipFile(zip_path, 'r') as z:
        with z.open('policy.pth') as f:
            state_dict = torch.load(f, map_location='cpu')

    # Extract only actor/policy layers needed for inference
    policy_dict = {}
    numpy_dict = {}
    for k, v in state_dict.items():
        if k.startswith("features_extractor.") or k.startswith("mlp_extractor.policy_net.") or k.startswith("action_net."):
            policy_dict[k] = v
            numpy_dict[k] = v.cpu().numpy()

    # Save PyTorch format
    torch.save(policy_dict, out_pt)
    # Save NumPy format
    np.savez_compressed(out_npz, **numpy_dict)
    print(f"[+] Exported PyTorch weights to: {out_pt}")
    print(f"[+] Exported NumPy weights to: {out_npz}")

if __name__ == "__main__":
    export_weights()
