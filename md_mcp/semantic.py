import os
import json
from sentence_transformers import SentenceTransformer, util

class SemanticIndex:
    def __init__(self, model_name="all-MiniLM-L6-v2", cache_dir=None):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.model = SentenceTransformer(model_name)
        self.embeddings = {}
        self.loaded = False

    def build_index(self, chunks):
        for chunk in chunks:
            self.embeddings[chunk.header_path] = self.model.encode(chunk.content)
        self.save_index()

    def save_index(self):
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
            index_file = os.path.join(self.cache_dir, ".md-mcp-embeddings.json")
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(self.embeddings, f)

    def load_index(self, cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            self.embeddings = json.load(f)

    def search(self, query, top_k=5):
        query_embedding = self.model.encode(query)
        scores = util.pytorch_cos_sim(query_embedding, self.embeddings)
        indices = scores.topk(top_k).indices
        return [list(self.embeddings.keys())[idx] for idx in indices]

    def is_available(self):
        try:
            self.model.encode("Hello, world!")
            return True
        except Exception:
            return False

# Example usage:
# index = SemanticIndex()
# index.build_index(chunk_list)
# results = index.search("your query text")