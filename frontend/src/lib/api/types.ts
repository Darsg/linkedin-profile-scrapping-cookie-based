// Friendly names for the types generated from the backend OpenAPI schema.
// Regenerate with `npm run gen:api` after changing backend schemas.
import type { components } from "./schema";

type Schemas = components["schemas"];

export type ScrapeJob = Schemas["ScrapeJobOut"];
export type JobStatus = Schemas["JobStatus"];
export type ProfileSummary = Schemas["ProfileSummary"];
export type ProfileDetail = Schemas["ProfileDetail"];
export type Contact = Schemas["ContactOut"];
export type Experience = Schemas["ExperienceOut"];
export type Education = Schemas["EducationOut"];
export type Activity = Schemas["ActivityOut"];

export type Page<T> = { items: T[]; total: number; limit: number; offset: number };

export const ACTIVE_STATUSES: readonly JobStatus[] = ["queued", "running"];
export const isActive = (job: Pick<ScrapeJob, "status">) => ACTIVE_STATUSES.includes(job.status);
