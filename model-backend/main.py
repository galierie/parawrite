from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, WebSocketException
from pydantic import BaseModel
from transformers import AutoModelForMaskedLM, AutoTokenizer

from src.model import SynonymGroupRequest, SynonymGroupResult, WordResult, recommend_by_batch

MODEL_PATH = '../model/ModernBERT-base-finetuned-rappler'

@asynccontextmanager
async def lifespan(app: FastAPI):
    model = AutoModelForMaskedLM.from_pretrained(MODEL_PATH) # type: ignore
    model.eval()
    app.state.model = model
    app.state.tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH) # type: ignore
    yield

app = FastAPI(lifespan=lifespan)

class GenericResponse(BaseModel):
    status: int
    message: str

# ----- API Endpoints -----

@app.get("/")
def main():
    return {"message": "Hello World"}

# /recommend is called by a client to 
# (1) score each word for every synonym group seen by the client based on the text context
# (2) provide some reasoning as to why this is
# This uses live communication (i.e., websockets) to ensure lower latency.

class RecommendRequest(BaseModel):
    synonym_groups: list[SynonymGroupRequest]
    text: str

class RecommendResponse(GenericResponse):
    synonym_group_results: list[SynonymGroupResult]

@app.websocket('/recommend')
async def recommend(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            # Receive payload
            payload_json = await websocket.receive_text()

            try:
                # Validate payload
                payload = RecommendRequest.model_validate_json(payload_json)

                # Process payload
                synonym_group_results: list[SynonymGroupResult] = recommend_by_batch(websocket.app.state.model, websocket.app.state.tokenizer, payload.synonym_groups, payload.text)

                await websocket.send_json(
                    RecommendResponse(status=200, message='OK', synonym_group_results=synonym_group_results).model_dump()
                )
            
            except Exception as err:
                print(f'Generic Exception: {str(err)}')

                # All errors manually raised are due to weird input
                await websocket.send_json(
                    GenericResponse(status=400, message='Possible malformed request.').model_dump()
                )

                continue
    
    except WebSocketDisconnect as err:
        print(f'WebSocket Disconnected: {str(err)}')

    except WebSocketException as err:
        print(f'WebSocket Exception: {str(err)}')

    except Exception as err:
        print(f'Generic Exception: {str(err)}')
