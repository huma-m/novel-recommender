from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from src.data_loader import load_data, get_gt_map
from src.recommender import Recommender

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
gt_map = get_gt_map(novels['id'])
recommender = Recommender(novels, gt_map)

class RecommendationRequest(BaseModel):
    id: int
    title: str
    mode: str = "balanced"
    top_n: int = 5
    min_similarity: float = 0.2
    
@app.get("/books")
def get_random_books(n: int = 10):
    if novels.empty:
        return []

    sample = novels.sample(n=min(n, len(novels)))

    return sample[[
        "id",
        "title",
        "description",
        "link"
    ]].to_dict(orient="records")
    
@app.get("/search")
def searchBooks(q: str):
    q = q.strip()
    if not q:
        return []
    mask = novels['title'].str.lower().str.contains(q.lower())
    matches = novels[mask].head(10)
    results = matches[['id', 'title',]].reset_index().to_dict(orient='records')
    return results

@app.post("/recommendations")
def get_recommendations(request: RecommendationRequest):
    try:
        recs = recommender.recommend(source_id=request.id,
                                    top_n=request.top_n, 
                                    mode=request.mode)
        return {"input_title": request.title, "recommendations": recs}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def read_root():
    return FileResponse("app/templates/index.html")
