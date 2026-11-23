import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { ProfileSkeleton, ProfileView } from "@/features/profiles/profile-view";

export const metadata: Metadata = { title: "Profile" };

export default function ProfilePage() {
  return (
    <div>
      <Link href="/profiles" className="mb-4 inline-block text-sm text-muted hover:text-fg">
        ← All profiles
      </Link>
      {/* ProfileView reads the route param on the client, which needs a Suspense boundary. */}
      <Suspense fallback={<ProfileSkeleton />}>
        <ProfileView />
      </Suspense>
    </div>
  );
}
