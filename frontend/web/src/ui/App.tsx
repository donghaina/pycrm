import { useState } from "react";
import DealList from "./DealList";
import DealDetail from "./DealDetail";
import DealCreate from "./DealCreate";

export default function App() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="text-lg font-semibold">pycrm</div>
          <div className="text-sm text-slate-500">Event-driven CRM</div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        <DealCreate onCreated={(id) => setSelectedId(id)} />
        <DealList onSelect={(id) => setSelectedId(id)} />
        {selectedId && <DealDetail id={selectedId} />}
      </main>
    </div>
  );
}
