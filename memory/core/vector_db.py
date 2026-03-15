import faiss
import numpy as np

class VectorDB:
    def __init__(self, dim: int = 128):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        
    def add(self, vectors: np.ndarray):
        faiss.normalize_L2(vectors)
        self.index.add(vectors)
        
    def search(self, query: np.ndarray, k: int = 5):
        faiss.normalize_L2(query)
        distances, indices = self.index.search(query, k)
        return distances, indices
