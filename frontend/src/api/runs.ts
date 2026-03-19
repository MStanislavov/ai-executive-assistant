import { get, post, del } from "./client"
import type { Run, RunCreate } from "./types"

export function listRuns(profileId: string) {
  return get<Run[]>(`/profiles/${profileId}/runs`)
}

export function getRun(profileId: string, runId: string) {
  return get<Run>(`/profiles/${profileId}/runs/${runId}`)
}

export function createRun(profileId: string, data: RunCreate) {
  return post<Run>(`/profiles/${profileId}/runs`, data)
}

export function cancelRun(profileId: string, runId: string) {
  return post<{ detail: string }>(`/profiles/${profileId}/runs/${runId}/cancel`)
}

export function deleteRun(profileId: string, runId: string) {
  return del(`/profiles/${profileId}/runs/${runId}`)
}

export function listAllRuns(limit = 10) {
  return get<Run[]>(`/runs?limit=${limit}`)
}
