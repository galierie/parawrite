from pydantic import BaseModel
from transformers import PreTrainedModel, PreTrainedTokenizerFast
import torch
from torch.nn.functional import softmax

class WordResult(BaseModel):
    word: str
    score: float
    reason: str

def recommend_by_batch(model: PreTrainedModel, tokenizer: PreTrainedTokenizerFast, synonym_groups: list[list[str]], text: str) -> list[list[WordResult]]:
    input_tokens = tokenizer(text, return_tensors="pt")

    # Get [MASK] indexes in text
    mask_text_indexes = (input_tokens.input_ids == tokenizer.mask_token_id).nonzero(as_tuple=False)
    # Validate input
    if len(synonym_groups) != mask_text_indexes.shape[0]:
        raise IndexError(f'Number of [MASK]s and number of synonym groups are not equal.')
    
    # Score against the model's entire vocabulary
    with torch.no_grad():
        model_output = model(**input_tokens)
        # TODO: Add reasoning

    def get_synonym_group_probabilities(item: tuple[int, list[str]]):
        idx, group = item

        # Convert the logits to probabilities for a specific [MASK]
        logits = model_output.logits[0, mask_text_indexes[idx, 1]]
        scores = softmax(logits, dim=-1)

        results: list[WordResult] = []

        for word in group:
            word_token_arr: list[str] = tokenizer.tokenize(text=word) # type: ignore
            if len(word_token_arr) != 1:
                print(f'Skipping scoring for word "{word}". Generated tokens: {word_token_arr}')
                continue

            word_token = word_token_arr[0]
            if word_token == tokenizer.unk_token:
                print(f'Skipping scoring for word "{word}". The word is somehow unknown to the model\'s vocabulary.')
                continue

            # Get the token ID from the model's entire vocabulary
            word_token_id = tokenizer.convert_tokens_to_ids(word_token)
            if isinstance(word_token_id, list):
                print(f'Skipping scoring for word "{word}". Generated more than one token ID.')
                continue

            results.append(WordResult(word=word, score=scores[word_token_id].item(), reason=''))
        
        return results

    return list(map(get_synonym_group_probabilities, enumerate(synonym_groups)))
