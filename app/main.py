from fastapi import FastAPI, HTTPException
import uvicorn
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from src.data_loader import load_data
from src.recommender_base_tag import recommend_novels, compute_similarities

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

novels = load_data()
# tag_similarity = compute_tag_similarity(novels)
# desc_similarity = compute_desc_similarity(novels)
similarity = compute_similarities(novels, tag_weight=0.5, desc_weight=0.5)

class RecommendationRequest(BaseModel):
    title: str
    top_n: int = 5
    min_similarity: float = 0.2
    
# @app.get("/books")
# def getAllBooks():
#     books = []
#     for idx, row in novels.iterrows():
#         book = {
#             "title": row['title'],
#         }
#         books.append(book)
#     return books

@app.get("/search")
def searchBooks(q: str):
    q = q.strip()
    if not q:
        return []
    mask = novels['title'].str.lower().str.contains(q.lower())
    matches = novels[mask].head(10)
    results = matches[['title']].reset_index().to_dict(orient='records')
    # results = search_novels(q, limit=10)
    return results

@app.post("/recommendations")
def get_recommendations(request: RecommendationRequest):
    try:
        recs = recommend_novels(request.title, novels, similarity, request.top_n, request.min_similarity)
        return {"input_title": request.title, "recommendations": recs}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def read_root():
    return FileResponse("app/templates/index.html")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)