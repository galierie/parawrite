import { variant } from 'valibot';

import { type ErrorResponse, ErrorResponseSchema } from './error-response';
import { type RecommendResponse, RecommendResponseSchema } from './recommend-response';

const ResponseSchema = variant('status', [ErrorResponseSchema, RecommendResponseSchema]);
type Response = ErrorResponse | RecommendResponse;

export {
    ErrorResponseSchema,
    RecommendResponseSchema,
    ResponseSchema,
    type ErrorResponse,
    type RecommendResponse,
    type Response,
};
