import { get, patch, del } from "./client"
import type { JobOpportunity, Certification, Course, Event, Group, Trend, ResultTitleUpdate } from "./types"

function withRunId(base: string, runId?: string) {
  return runId ? `${base}?run_id=${encodeURIComponent(runId)}` : base
}

export function listJobs(profileId: string, runId?: string) {
  return get<JobOpportunity[]>(withRunId(`/profiles/${profileId}/results/jobs`, runId))
}

export function listCertifications(profileId: string, runId?: string) {
  return get<Certification[]>(withRunId(`/profiles/${profileId}/results/certifications`, runId))
}

export function listCourses(profileId: string, runId?: string) {
  return get<Course[]>(withRunId(`/profiles/${profileId}/results/courses`, runId))
}

export function listEvents(profileId: string, runId?: string) {
  return get<Event[]>(withRunId(`/profiles/${profileId}/results/events`, runId))
}

export function listGroups(profileId: string, runId?: string) {
  return get<Group[]>(withRunId(`/profiles/${profileId}/results/groups`, runId))
}

export function listTrends(profileId: string, runId?: string) {
  return get<Trend[]>(withRunId(`/profiles/${profileId}/results/trends`, runId))
}

export function updateResult(profileId: string, category: string, itemId: string, body: ResultTitleUpdate) {
  return patch<unknown>(`/profiles/${profileId}/results/${category}/${itemId}`, body)
}

export function deleteResult(profileId: string, category: string, itemId: string) {
  return del(`/profiles/${profileId}/results/${category}/${itemId}`)
}
