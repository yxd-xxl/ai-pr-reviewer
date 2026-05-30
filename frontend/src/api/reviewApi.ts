import { apiGet, apiPost } from "./client";
import type { ReviewResult } from "../types";

export function fetchReview(prUrl: string): Promise<ReviewResult> {
  return apiPost<ReviewResult>("/api/v1/review", { pr_url: prUrl });
}

export function submitFeedback(
  fingerprint: string,
  state: string,
  reason: string
): Promise<{ status: string }> {
  return apiPost("/api/v1/feedback", { fingerprint, state, reason });
}

export function getReviewHistory(
  repo: string,
  limit: number = 20
): Promise<unknown[]> {
  return apiGet(`/api/v1/reviews?repo=${encodeURIComponent(repo)}&limit=${limit}`);
}
