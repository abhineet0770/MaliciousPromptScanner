import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer

def download_models():
    print("Downloading models...")
    # Multilingual model (v2 feature)
    SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    # Default original model (fallback)
    SentenceTransformer('all-MiniLM-L6-v2')
    print("Models downloaded successfully!")

if __name__ == "__main__":
    download_models()
