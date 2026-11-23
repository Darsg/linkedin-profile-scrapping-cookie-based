"use client";

import Link from "next/link";
import { useDeferredValue, useState } from "react";

import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorNote, Skeleton } from "@/components/ui/feedback";
import { formatRelative } from "@/lib/format";

import { PAGE_SIZE, useProfiles } from "./api";

export function ProfilesList() {
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const query = useDeferredValue(search.trim());
  const { data, isPending, error, isPlaceholderData } = useProfiles(query, offset);

  return (
    <div className="space-y-4">
      <input
        type="search"
        value={search}
        onChange={(event) => {
          setSearch(event.target.value);
          setOffset(0);
        }}
        placeholder="Search by name, headline or profile id"
        aria-label="Search profiles"
        className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm placeholder:text-muted sm:max-w-sm"
      />

      {isPending ? (
        <div className="space-y-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[4.5rem]" />
          ))}
        </div>
      ) : error ? (
        <ErrorNote message={error.message} />
      ) : data.items.length === 0 ? (
        <EmptyState
          title={query ? `No profiles match “${query}”` : "No profiles stored yet"}
          hint={query ? "Try a different search." : "Scrape a profile from the Scrape page."}
        />
      ) : (
        <>
          <Card className={isPlaceholderData ? "divide-y divide-border opacity-60" : "divide-y divide-border"}>
            {data.items.map((profile) => (
              <Link
                key={profile.id}
                href={`/profiles/${profile.id}`}
                className="flex items-center gap-3 px-4 py-3 transition-colors first:rounded-t-xl last:rounded-b-xl hover:bg-surface-2"
              >
                <Avatar name={profile.full_name} src={profile.photo_url} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{profile.full_name ?? profile.public_id}</p>
                  <p className="truncate text-sm text-muted">
                    {profile.headline ?? "No headline"}
                    {profile.location ? ` · ${profile.location}` : ""}
                  </p>
                </div>
                <div className="hidden shrink-0 flex-col items-end gap-1 sm:flex">
                  <Badge>{profile.source_provider}</Badge>
                  <span className="text-xs text-muted">{formatRelative(profile.last_scraped_at)}</span>
                </div>
              </Link>
            ))}
          </Card>

          <div className="flex items-center justify-between text-sm text-muted">
            <span>
              {offset + 1}–{offset + data.items.length} of {data.total}
            </span>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                className="h-8"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                className="h-8"
                disabled={offset + PAGE_SIZE >= data.total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
