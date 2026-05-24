import { literal, object, string, type InferOutput } from 'valibot';

export const ErrorResponseSchema = object({
  status: literal(400),
  message: string(),
});

export type ErrorResponse = InferOutput<typeof ErrorResponseSchema>;
