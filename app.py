"""Root entry point for Stock Market News Research Agent."""
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from app import main

if __name__ == "__main__":
    main()

