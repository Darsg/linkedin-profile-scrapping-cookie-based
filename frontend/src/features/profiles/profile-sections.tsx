import { Badge } from "@/components/ui/badge";
import { CardSection } from "@/components/ui/card";
import type { Activity, Contact, Education, Experience } from "@/lib/api/types";
import { formatCount, formatDateRange, formatRelative } from "@/lib/format";

const CONTACT_LABELS: Record<string, string> = {
  email: "Email",
  phone: "Phone",
  website: "Website",
  twitter: "Twitter / X",
  birthday: "Birthday",
  address: "Address",
  im: "Messaging",
};

function contactHref({ type, value }: Contact): string | null {
  if (type === "email") return `mailto:${value}`;
  if (type === "phone") return `tel:${value.replace(/[^\d+]/g, "")}`;
  // Only link real http(s) URLs — never render a scraped `javascript:` value as a link.
  return /^https?:\/\//i.test(value) ? value : null;
}

const None = ({ children }: { children: string }) => (
  <p className="text-sm text-muted">{children}</p>
);

export function ContactSection({ contacts }: { contacts: Contact[] }) {
  return (
    <CardSection title="Contact info">
      {contacts.length === 0 ? (
        <None>No contact details were visible on this profile.</None>
      ) : (
        <dl className="space-y-3 text-sm">
          {contacts.map((contact) => {
            const href = contactHref(contact);
            return (
              <div key={`${contact.type}:${contact.value}`}>
                <dt className="text-xs uppercase tracking-wide text-muted">
                  {CONTACT_LABELS[contact.type] ?? contact.type}
                </dt>
                <dd className="mt-0.5 break-all">
                  {href ? (
                    <a href={href} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
                      {contact.value}
                    </a>
                  ) : (
                    contact.value
                  )}
                </dd>
              </div>
            );
          })}
        </dl>
      )}
    </CardSection>
  );
}

export function ExperienceSection({ experiences }: { experiences: Experience[] }) {
  return (
    <CardSection title="Experience" count={experiences.length}>
      {experiences.length === 0 ? (
        <None>No work experience listed.</None>
      ) : (
        <ol className="space-y-6 border-l border-border pl-5">
          {experiences.map((role, index) => {
            const dates = formatDateRange(role.start_date, role.end_date, role.is_current);
            return (
              <li key={index} className="relative">
                <span
                  aria-hidden
                  className={`absolute top-1.5 -left-[1.6rem] size-2.5 rounded-full ring-4 ring-surface ${
                    role.is_current ? "bg-accent" : "bg-border"
                  }`}
                />
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-medium">{role.title ?? "Untitled role"}</h3>
                  {role.is_current && <Badge tone="info">Current</Badge>}
                </div>
                <p className="text-sm">
                  {[role.company, role.employment_type].filter(Boolean).join(" · ")}
                </p>
                <p className="text-sm text-muted">{[dates, role.location].filter(Boolean).join(" · ")}</p>
                {role.description && (
                  <p className="mt-2 text-sm whitespace-pre-line text-muted">{role.description}</p>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </CardSection>
  );
}

export function EducationSection({ educations }: { educations: Education[] }) {
  return (
    <CardSection title="Education" count={educations.length}>
      {educations.length === 0 ? (
        <None>No education listed.</None>
      ) : (
        <ul className="space-y-5">
          {educations.map((item, index) => (
            <li key={index}>
              <h3 className="font-medium">{item.school ?? "Unknown school"}</h3>
              <p className="text-sm">{[item.degree, item.field_of_study].filter(Boolean).join(", ")}</p>
              <p className="text-sm text-muted">
                {[item.start_year, item.end_year].filter(Boolean).join(" – ")}
              </p>
              {item.description && (
                <p className="mt-1 text-sm whitespace-pre-line text-muted">{item.description}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </CardSection>
  );
}

export function ActivitySection({ activities }: { activities: Activity[] }) {
  return (
    <CardSection title="Recent activity" count={activities.length}>
      {activities.length === 0 ? (
        <None>No recent public activity found.</None>
      ) : (
        <ul className="divide-y divide-border">
          {activities.map((activity, index) => (
            <li key={index} className="py-4 first:pt-0 last:pb-0">
              <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs text-muted">
                <Badge className="capitalize">{activity.kind}</Badge>
                {activity.posted_at && <span>{formatRelative(activity.posted_at)}</span>}
                {activity.reactions_count !== null && (
                  <span>{formatCount(activity.reactions_count, "reaction")}</span>
                )}
                {activity.comments_count !== null && (
                  <span>{formatCount(activity.comments_count, "comment")}</span>
                )}
              </div>
              <p className="line-clamp-4 text-sm whitespace-pre-line">
                {activity.text ?? "No text content."}
              </p>
              {activity.url && /^https?:\/\//i.test(activity.url) && (
                <a
                  href={activity.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-1.5 inline-block text-sm text-accent hover:underline"
                >
                  Open post
                </a>
              )}
            </li>
          ))}
        </ul>
      )}
    </CardSection>
  );
}
