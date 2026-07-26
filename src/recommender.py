import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix
from pathlib import Path 


ROOT = Path(__file__).resolve().parent.parent
MATRIX_DIR = ROOT / "matrix"

class Recommender:
    def __init__(self, novels_df, gt_map):
        self.df = novels_df.reset_index(drop=True)
        self.id_to_idx = {nid: i for i, nid in enumerate(self.df['id'])}
        self.idx_to_id = {i: nid for nid, i in self.id_to_idx.items()}
        n = len(self.df)
        
        trope_path = MATRIX_DIR / "trope_sim.npy"
        desc_path = MATRIX_DIR / "desc_sim.npy"
        collab_path = MATRIX_DIR / "collab_sim.npy"

        if trope_path.exists() and desc_path.exists() and collab_path.exists():
            self.trope_sim = np.load(trope_path)
            self.desc_sim = np.load(desc_path)
            self.collab_sim = np.load(collab_path)
        else:
            trope_matrix = np.vstack(self.df["tag_embedding"]).astype(np.float32)
            desc_matrix  = np.vstack(self.df["desc_embedding"]).astype(np.float32)

            self.trope_sim = self._normalize(cosine_similarity(trope_matrix))
            self.desc_sim  = self._normalize(cosine_similarity(desc_matrix))

            rows, cols = [], []
            for src, tgts in gt_map.items():
                if src in self.id_to_idx:
                    s = self.id_to_idx[src]
                    for t in tgts:
                        if t in self.id_to_idx:
                            rows.append(s)
                            cols.append(self.id_to_idx[t])

            adj = csr_matrix(
                (np.ones(len(rows)), (rows, cols)),
                shape=(n, n),
                dtype=np.float32
            )
            adj = (adj + adj.T)

            self.collab_sim = self._normalize(cosine_similarity(adj)) * 0.5
            
    def _normalize(self, x):
        x = x.astype(np.float32)
        min_v, max_v = x.min(), x.max()
        if max_v - min_v < 1e-8:
            return np.zeros_like(x)
        return (x - min_v) / (max_v - min_v)

    def recommend(self, source_id, top_n=10, mode="balanced"):
        if source_id not in self.id_to_idx:
            return []

        idx = self.id_to_idx[source_id]

        configs = {
            # lambda: higher = more diversity
            "familiar":   {"w": (0.55, 0.20, 0.25), "trope_penalty": 0.4, "lambda": 0.15},
            "balanced":   {"w": (0.38, 0.25, 0.37), "trope_penalty": 0.25, "lambda": 0.30},
            "adventurous":{"w": (0.25, 0.20, 0.55), "trope_penalty": 0.10, "lambda": 0.45},
        }

        cfg = configs[mode]
        w_t, w_c, w_d = cfg["w"]
        lambda_param = cfg["lambda"]  # 0 = pure relevance, 1 = pure diversity

        t = self.trope_sim[idx]
        c = self.collab_sim[idx]
        d = self.desc_sim[idx]

        # Base relevance score
        relevance = w_t * t + w_c * c + w_d * d
        relevance -= cfg["trope_penalty"] * (1 - t)
        relevance[idx] = -1

        candidates = np.where(relevance > 0)[0]
        selected = []

        while len(selected) < top_n and len(candidates) > 0:
            if not selected:
                best = candidates[np.argmax(relevance[candidates])]
            else:
                # Get similarity matrix: rows=candidates, cols=selected
                sim_to_selected = self.desc_sim[np.ix_(candidates, selected)]
                max_sim = sim_to_selected.max(axis=1)

                # λ * (1 - max_sim) + (1 - λ) * relevance
                # Higher λ = more weight on diversity (low similarity)
                mmr_score = (
                    lambda_param * (1 - max_sim)  # diversity component
                    + (1 - lambda_param) * relevance[candidates]  # relevance component
                )

                best = candidates[np.argmax(mmr_score)]

            selected.append(best)
            candidates = candidates[candidates != best]

        return [self._format(idx, i, relevance, t, c, d) for i in selected]

    def _format(self, src, tgt, score, t, c, d):
        row = self.df.iloc[tgt]
        src_tags = set(self.df.iloc[src]["tags"]) if isinstance(self.df.iloc[src]["tags"], list) else set()
        tgt_tags = set(row["tags"]) if isinstance(row["tags"], list) else set()

        return {
            "id": self.idx_to_id[tgt],
            "title": row["title"],
            "genres": row["genres"],
            "score": round(float(score[tgt]), 4),
            "breakdown": {
                "trope": round(float(t[tgt]), 3),
                "desc":  round(float(d[tgt]), 3),
                "collab":round(float(c[tgt]), 3),
            },
            "tags": list(src_tags & tgt_tags),
            "description": row["description"],
            "link": row["link"],
        }


    def evaluate_modes(self, gt_map, sample_size=50):
        print("\n" + "=" * 60)
        print("MODE EVALUATION")
        print("=" * 60)

        modes = ["familiar", "balanced", "adventurous"]
        sample_ids = list(gt_map.keys())[:sample_size]

        results = {
            mode: {
                "serendipity": [],
                "coverage": [],
                "precision": []
            } for mode in modes
        }

        for src_id in sample_ids:
            if src_id not in self.id_to_idx:
                continue

            src_idx = self.id_to_idx[src_id]
            gt_targets = set(gt_map.get(src_id, []))

            for mode in modes:
                recs = self.recommend(
                    source_id=src_id,
                    top_n=10,
                    mode=mode
                )

                if not recs:
                    continue

                rec_ids = [r["id"] for r in recs]
                rec_idx = [self.id_to_idx[rid] for rid in rec_ids]

                # METRIC 1: Precision@K (lower bound)
                overlap = len(set(rec_ids) & gt_targets)
                results[mode]["precision"].append(overlap / len(rec_ids))

                # METRIC 2: Coverage / Diversity@K
                # (description embedding space)
                if len(rec_idx) > 1:
                    pairwise = []
                    for i in range(len(rec_idx)):
                        for j in range(i + 1, len(rec_idx)):
                            pairwise.append(
                                self.desc_sim[rec_idx[i]][rec_idx[j]]
                            )
                    results[mode]["coverage"].append(1 - np.mean(pairwise))

                # METRIC 3: Serendipity@K
                # relevance × (1 − similarity_to_source)
                ser_scores = []
                for r_idx, r in zip(rec_idx, recs):
                    relevance = r["score"]
                    similarity = self.desc_sim[src_idx][r_idx]
                    ser_scores.append(relevance * (1 - similarity))

                results[mode]["serendipity"].append(np.mean(ser_scores))

        print(f"{'Mode':<12} | {'Precision':<10} | {'Serendipity':<12} | {'Diversity':<10}")
        print("-" * 55)

        for mode in modes:
            print(
                f"{mode.capitalize():<12} | "
                f"{np.mean(results[mode]['precision']) * 100:>7.1f}%   | "
                f"{np.mean(results[mode]['serendipity']):>10.3f}   | "
                f"{np.mean(results[mode]['coverage']):>8.3f}"
            )  
