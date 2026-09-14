"""
Quick test script to verify ASH-FL Phase 1 setup.
Run this before executing the full simulation.
"""

import sys

def test_imports():
    """Test if all required packages are installed."""
    print("Testing imports...")
    errors = []
    
    try:
        import torch
        print(f"✓ PyTorch {torch.__version__}")
    except ImportError as e:
        errors.append(f"✗ PyTorch: {e}")
    
    try:
        import flwr
        print(f"✓ Flower {flwr.__version__}")
    except ImportError as e:
        errors.append(f"✗ Flower: {e}")
    
    try:
        import yaml
        print(f"✓ PyYAML")
    except ImportError as e:
        errors.append(f"✗ PyYAML: {e}")
    
    try:
        import sklearn
        print(f"✓ scikit-learn {sklearn.__version__}")
    except ImportError as e:
        errors.append(f"✗ scikit-learn: {e}")
    
    try:
        import ucimlrepo
        print(f"✓ ucimlrepo")
    except ImportError as e:
        errors.append(f"✗ ucimlrepo: {e}")
    
    try:
        import numpy
        print(f"✓ NumPy {numpy.__version__}")
    except ImportError as e:
        errors.append(f"✗ NumPy: {e}")
    
    try:
        import pandas
        print(f"✓ Pandas {pandas.__version__}")
    except ImportError as e:
        errors.append(f"✗ Pandas: {e}")
    
    return errors


def test_modules():
    """Test if project modules can be imported."""
    print("\nTesting project modules...")
    errors = []
    
    try:
        from clients.data_loader import HeartDiseaseDataLoader
        print("✓ clients.data_loader")
    except ImportError as e:
        errors.append(f"✗ clients.data_loader: {e}")
    
    try:
        from clients.client import HeartDiseaseNet, HeartDiseaseClient
        print("✓ clients.client")
    except ImportError as e:
        errors.append(f"✗ clients.client: {e}")
    
    try:
        from aggregation.strategy import FedAvgStrategy
        print("✓ aggregation.strategy")
    except ImportError as e:
        errors.append(f"✗ aggregation.strategy: {e}")
    
    return errors


def test_config():
    """Test if config file can be loaded."""
    print("\nTesting configuration...")
    try:
        import yaml
        with open("configs/sim_config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        print(f"✓ Configuration loaded successfully")
        print(f"  - Rounds: {config['num_rounds']}")
        print(f"  - Clients: {config['num_clients_total']}")
        print(f"  - Strategy: {config['strategy']}")
        return []
    except Exception as e:
        return [f"✗ Config loading: {e}"]


def test_model():
    """Test if model can be instantiated."""
    print("\nTesting model instantiation...")
    try:
        from clients.client import HeartDiseaseNet
        model = HeartDiseaseNet(input_dim=13, hidden_dim=32, output_dim=1)
        num_params = sum(p.numel() for p in model.parameters())
        print(f"✓ Model instantiated successfully")
        print(f"  - Parameters: {num_params}")
        return []
    except Exception as e:
        return [f"✗ Model instantiation: {e}"]


def main():
    """Run all tests."""
    print("=" * 60)
    print("ASH-FL Phase 1: Setup Verification")
    print("=" * 60)
    print()
    
    all_errors = []
    
    # Test imports
    all_errors.extend(test_imports())
    
    # Test modules
    all_errors.extend(test_modules())
    
    # Test config
    all_errors.extend(test_config())
    
    # Test model
    all_errors.extend(test_model())
    
    # Summary
    print("\n" + "=" * 60)
    if all_errors:
        print("❌ Setup verification FAILED")
        print("\nErrors found:")
        for error in all_errors:
            print(f"  {error}")
        print("\nPlease install missing packages:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    else:
        print("✅ Setup verification PASSED")
        print("\nYou're ready to run the simulation:")
        print("  python main.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
