"""Automated Kaggle Submission Builder and Validator.
Packages main.py, policy_weights.pt, decompressed_trace.json, and src/ into submission.tar.gz.
Validates the bundle in an isolated sandbox before submitting.
"""
import os
import shutil
import tarfile
import tempfile
from kaggle_environments import make

def build_and_validate_bundle(output_tar="submission.tar.gz"):
    print("=" * 70)
    print("[*] BUILDING AND VALIDATING KAGGLE SUBMISSION BUNDLE")
    print("=" * 70)

    # 1. Create Tar.gz Archive using Python tarfile (cross-platform, zero path bugs)
    files_to_add = [
        "main.py",
        "policy_weights.pt",
        "decompressed_trace.json",
    ]
    directories_to_add = [
        "src",
    ]

    with tarfile.open(output_tar, "w:gz") as tar:
        for f in files_to_add:
            if os.path.exists(f):
                tar.add(f, arcname=f)
                print(f"  + Added file: {f}")
            else:
                print(f"  ! Warning: missing {f}")
        for d in directories_to_add:
            if os.path.exists(d):
                tar.add(d, arcname=d)
                print(f"  + Added directory: {d}")

    tar_size_kb = os.path.getsize(output_tar) / 1024.0
    print(f"\n[+] Created {output_tar} ({tar_size_kb:,.1f} KB)")

    # 2. Extract and Validate in Isolated Sandbox
    print("\n[*] Validating submission bundle in clean temporary sandbox...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        with tarfile.open(output_tar, "r:gz") as tar:
            tar.extractall(path=tmp_dir)

        main_path = os.path.join(tmp_dir, "main.py")
        env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
        env.run([main_path, "starter"])

        final = env.steps[-1]
        p0_reward = final[0].reward or 0
        p1_reward = final[1].reward or 0
        print(f"  * Sandbox Match Result vs Starter: P0=${p0_reward:,.0f} | P1=${p1_reward:,.0f} | Margin=${p0_reward - p1_reward:+,.0f}")
        print(f"  * P0 Status: {final[0].status} | P1 Status: {final[1].status}")
        
        if final[0].status == "DONE":
            print("\n" + "=" * 70)
            print("[+] BUNDLE VALIDATION PASSED! Ready for Kaggle Submission.")
            print("=" * 70)
            return True
        else:
            print("\n[-] Sandbox validation failed!")
            return False


if __name__ == "__main__":
    build_and_validate_bundle()
