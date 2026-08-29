import type { ComponentType } from "react";

type EmptyStateProps = {
  icon: ComponentType<{ className?: string }>;
  title: string;
  description: string;
};

export function EmptyState({
  icon: Icon,
  title,
  description,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border px-6 py-16 text-center">
      <Icon aria-hidden="true" className="size-8 text-muted-foreground" />
      <p className="font-heading text-base font-medium text-foreground">
        {title}
      </p>
      <p className="max-w-sm text-sm text-pretty text-muted-foreground">
        {description}
      </p>
    </div>
  );
}
