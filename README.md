# Novel Recommendation System

An end-to-end  hybrid recommendation system that discovers new novels based on trope similarity, writing style, and reader behavior patterns.

The project was built to explore how semantic understanding of trope tags and novel descriptions can be combined with community recommendation data to generate high-quality recommendations while balancing relevance and discovery.

---

## Project Overview

The system consists of an offline machine learning pipeline and an online recommendation service.

### Offline Pipeline

- Collected and cleaned novel metadata from public sources
- Generated transformer embeddings for novels tag and description
- Stored embeddings in SQLite for efficient retrieval
- Constructed a collaborative recommendation graph from existing recommendation links

### Recommendation Engine

The recommender combines three complementary signals:

- **Trope similarity** using SentenceTransformer embeddings generated from novel tags
- **Semantic similarity** using SentenceTransformer embeddings generated from novel descriptions
- **Collaborative similarity** derived from community recommendation relationships

These signals are fused into a hybrid recommendation score that can be tuned to balance relevance and exploration.

### Recommendation Strategies

- Familiar – prioritizes highly similar novels for maximum relevance.
- Balanced – provides the best trade-off between relevance and discovery.
- Adventurous – increases recommendation diversity to encourage exploration of less obvious novels.
  
Offline evaluation showed that the Balanced strategy achieved the highest recommendation precision while maintaining strong diversity and serendipity compared to the other modes.

---

## Evaluation

The recommender was evaluated using both relevance and discovery-oriented metrics.

Evaluation includes:

- Precision: Measures how new recommendations still match the source novel's tropes.
- Serendipity: Measures how well the recommender discovers unexpected but still relevant novels instead of recommending only obvious choices.
- Intra-list Diversity: Measures how different the recommended novels are from one another.

Multiple weighting strategies were explored to analyze the trade-offs between recommendation accuracy and recommendation discovery.

---

## Technologies

- Python
- FastAPI
- SentenceTransformers
- scikit-learn
- SQLAlchemy
- SQLite
- Pandas
- NumPy
- SciPy

---

## Project Highlights

- Built an end-to-end recommendation pipeline from data collection to deployment.
- Designed a hybrid recommendation system combining semantic embeddings with collaborative filtering.
- Implemented offline embedding generation for efficient online inference.
- Developed custom evaluation metrics to assess recommendation quality beyond traditional ranking accuracy.
- Structured the project using a modular architecture separating data processing, database operations, recommendation logic, evaluation, and API layers.

---
