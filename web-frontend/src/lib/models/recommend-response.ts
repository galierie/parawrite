import { array, type InferOutput, literal, number, object, string } from 'valibot';

const WordResultSchema = object({
    word: string(),
    score: number(),
    reason: string(),
});

const SynonymGroupResultSchema = object({
    id: string(),
    results: array(WordResultSchema),
});

export const RecommendResponseSchema = object({
    status: literal(200),
    message: string(),
    synonym_group_results: array(SynonymGroupResultSchema),
});

export type RecommendResponse = InferOutput<typeof RecommendResponseSchema>;
