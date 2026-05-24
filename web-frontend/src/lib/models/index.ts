import { ErrorResponseSchema, type ErrorResponse } from './error-response';
import { RecommendResponseSchema, type RecommendResponse } from './recommend-response';
import { variant } from 'valibot';

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