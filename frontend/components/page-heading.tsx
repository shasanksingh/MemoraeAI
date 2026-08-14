export function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return (
    <div className="mb-7 flex flex-col justify-between gap-4 md:flex-row md:items-end">
      <div>
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-[.2em] text-violet-400">{eyebrow}</p>
        <h1 className="text-2xl font-semibold tracking-[-.025em] text-zinc-100 md:text-3xl">{title}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">{description}</p>
      </div>
      {action}
    </div>
  );
}
