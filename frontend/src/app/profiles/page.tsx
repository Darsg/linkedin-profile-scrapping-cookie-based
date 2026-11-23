import type { Metadata } from "next";

import { ProfilesList } from "@/features/profiles/profiles-list";

export const metadata: Metadata = { title: "Profiles" };

export default function ProfilesPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold tracking-tight sm:text-3xl">Stored profiles</h1>
      <ProfilesList />
    </div>
  );
}
