export type ApiErrorCode = "UNAUTHORIZED" | "FORBIDDEN" | "NOT_FOUND" | "CONFLICT" | "INVALID";

export interface ApiErrorPayload {
  code: ApiErrorCode;
  message: string;
}
