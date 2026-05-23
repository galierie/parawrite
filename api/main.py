from fastapi import FastAPI
from transformers import pipeline
from lib.types import Query

app = FastAPI()


mask_filler = pipeline("fill-mask", model="./ModernBERT-base-finetuned-rappler")





@app.get("/v1/query")
async def query(query: Query):
    preds = mask_filler(query.text)
    return preds[0]