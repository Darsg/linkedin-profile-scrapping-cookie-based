import { RecentJobs } from "@/features/scrape/recent-jobs";
import { ScrapeForm } from "@/features/scrape/scrape-form";

export default function HomePage() {
  return (
    <div className="space-y-10">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Scrape a LinkedIn profile</h1>
        <p className="mt-2 max-w-2xl text-muted">
          Paste a profile URL. The profile&apos;s name, contact info, experience, education and recent
          activity are collected in the background and saved to your database.
        </p>
        <div className="mt-6">
          <ScrapeForm />
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Recent scrapes</h2>
        <RecentJobs />
      </section>
    </div>
  );
}
