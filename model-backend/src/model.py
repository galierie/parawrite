from pydantic import BaseModel
from transformers import PreTrainedModel, PreTrainedTokenizerFast
import torch
from torch.nn.functional import softmax

class SynonymGroupRequest(BaseModel):
    id: str
    words: list[str]

class WordResult(BaseModel):
    word: str
    score: float
    reason: str

class SynonymGroupResult(BaseModel):
    id: str
    results: list[WordResult]


def bert_infer(model: PreTrainedModel, tokenizer: PreTrainedTokenizerFast, text: str):
    tokenized = tokenizer(text, return_tensors="pt")
    logits = model(**tokenized).logits
    mask_token_index = torch.where(tokenized["input_ids"] == tokenizer.mask_token_id)[1]
    mask_token_logits = logits[0, mask_token_index, :]
    best = mask_token_logits[0].argmax(dim=-1).item()


    token_text = tokenizer.decode([best]).strip()
    return token_text

    


def recommend_by_batch(model: PreTrainedModel, tokenizer: PreTrainedTokenizerFast, synonym_groups: list[SynonymGroupRequest], text: str) -> list[SynonymGroupResult]:
    input_tokens = tokenizer(text, return_tensors="pt", return_offsets_mapping=True)

    # Get [MASK] indexes in text
    mask_text_indexes = (input_tokens.input_ids == tokenizer.mask_token_id).nonzero(as_tuple=False)
    # Validate input
    if len(synonym_groups) != mask_text_indexes.shape[0]:
        raise IndexError(f'Number of [MASK]s and number of synonym groups are not equal.')
    
    # Score against the model's entire vocabulary
    with torch.no_grad():
        model_output = model(**input_tokens)
        # TODO: Add reasoning

    def get_synonym_group_probabilities(item: tuple[int, SynonymGroupRequest]):
        idx, request = item

        # Convert the logits to probabilities for a specific [MASK]
        logits = model_output.logits[0, mask_text_indexes[idx, 1]]
        scores = softmax(logits, dim=-1)

        results: list[WordResult] = []

        for word in request.words:
            # word_token_arr: list[str] = tokenizer.tokenize(text=word) # type: ignore
            # if len(word_token_arr) != 1:
            #     print(f'Skipping scoring for word "{word}". Generated tokens: {word_token_arr}')
            #     results.append(WordResult(word=word, score=0, reason=''))
            #     continue

            # word_token = word_token_arr[0]
            # if word_token == tokenizer.unk_token:
            #     print(f'Skipping scoring for word "{word}". The word is somehow unknown to the model\'s vocabulary.')
            #     results.append(WordResult(word=word, score=0, reason=''))
            #     continue

            # Get the token ID from the model's entire vocabulary
            word_token_id = tokenizer.convert_tokens_to_ids(word)
            if isinstance(word_token_id, list):
                print(f'Skipping scoring for word "{word}". Generated more than one token ID.')
                results.append(WordResult(word=word, score=0, reason=''))
                continue

            # TODO use surrounding text as context
            reason = bert_infer(model, tokenizer, f"The word {word} should be more fitting for the sentence as it has the best [MASK]")

            results.append(WordResult(word=word, score=scores[word_token_id].item(), reason=f"{word} is the best pick as it has the best {reason}"))
        
        return SynonymGroupResult(id=request.id, results=results)

    return list(map(get_synonym_group_probabilities, enumerate(synonym_groups)))
