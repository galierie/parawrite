from fastapi import FastAPI
from transformers import pipeline

app = FastAPI()


mask_filler = pipeline("fill-mask", model="./ModernBERT-base-finetuned-rappler")


@app.get("/v1/query")
async def query(text: str):
    preds = mask_filler(text)

    return preds[0]