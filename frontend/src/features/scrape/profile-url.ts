import { z } from "zod";

// Mirrors backend/app/utils/linkedin_url.py so obvious mistakes are caught before a request.
// The backend remains the source of truth.
const PROFILE_URL = /^(https?:\/\/)?([a-z]{2,3}\.)?linkedin\.com\/in\/[^/?#\s]{2,}/i;

export const profileUrlSchema = z
  .string()
  .trim()
  .min(1, "Paste a LinkedIn profile URL")
  .max(500, "That URL is too long")
  .regex(PROFILE_URL, "Use a profile URL like https://www.linkedin.com/in/name");
