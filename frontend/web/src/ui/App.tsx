import { useEffect, useMemo, useState } from "react";
import DealList from "./DealList";
import DealDetail from "./DealDetail";
import DealCreate from "./DealCreate";

type Route =
  | { page: "list" }
  | { page: "create" }
  | { page: "detail"; id: string };

function parseHash(hash: string): Route {
  if (!hash || hash === "#") return { page: "list" };
  const trimmed = hash.replace(/^#\/?/, "");
  const [page, id] = trimmed.split("/");
  if (page === "create") return { page: "create" };
  if (page === "deal" && id) return { page: "detail", id };
  return { page: "list" };
}

function setHash(path: string) {
  window.location.hash = path;
}

export default function App() {
  const [hash, setHashState] = useState(() => window.location.hash);

  useEffect(() => {
    const onChange = () => setHashState(window.location.hash);
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const route = useMemo(() => parseHash(hash), [hash]);
  const isList = route.page === "list";
  const isCreate = route.page === "create";
  const isDetail = route.page === "detail";

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="text-lg font-semibold">pycrm</div>
          <div className="text-sm text-slate-500">Event-driven CRM</div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        {isList && (
          <DealList
            onSelect={(id) => setHash(`/deal/${id}`)}
            onCreate={() => setHash("/create")}
          />
        )}
        {isCreate && (
          <DealCreate onCreated={(id) => setHash(`/deal/${id}`)} />
        )}
        {isDetail && (
          <div className="space-y-4">
            <button
              className="text-sm text-slate-500 hover:text-slate-700"
              onClick={() => setHash("/deals")}
            >
              ← Back to deals
            </button>
            <DealDetail id={route.id} />
          </div>
        )}
      </main>
    </div>
  );
}
