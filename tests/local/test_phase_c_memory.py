import pytest
np = pytest.importorskip("numpy")
from memory.core.vector_db import VectorDB

def test_vector_db():
    db = VectorDB(dim=64)
    vectors = np.random.rand(10, 64).astype("float32")
    db.add(vectors)
    distances, indices = db.search(vectors[0:1], k=1)
    assert len(indices) == 1
    assert indices[0][0] == 0  # Should find itself
