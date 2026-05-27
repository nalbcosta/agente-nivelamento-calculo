export function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-2xl border border-zinc-300/70 bg-white/70 p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-700">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-zinc-500">Nenhum item retornado.</p>
      ) : (
        <ul className="mt-2 space-y-2 text-sm text-zinc-800">
          {items.map((item) => (
            <li key={`${title}-${item}`} className="rounded-lg bg-zinc-100/80 px-3 py-2">
              {item}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
