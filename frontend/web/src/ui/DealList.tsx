import { gql, useQuery } from "@apollo/client";

type Deal = {
  id: string;
  title: string;
  amount: number;
  currency: string;
  reviewStatus: string;
};

const STATUS_TONE: Record<string, string> = {
  NOT_REQUIRED: "bg-slate-100 text-slate-700",
  PENDING: "bg-amber-100 text-amber-800",
  APPROVED: "bg-emerald-100 text-emerald-800",
  REJECTED: "bg-rose-100 text-rose-800"
};

const DEALS_QUERY = gql`
  query Deals {
    deals {
      id
      title
      amount
      currency
      reviewStatus
    }
  }
`;

export default function DealList({
  onSelect,
  onCreate,
}: {
  onSelect: (id: string) => void;
  onCreate: () => void;
}) {
  const { data, loading, error } = useQuery(DEALS_QUERY, { fetchPolicy: "cache-and-network" });

  if (loading) return <div>Loading deals...</div>;
  if (error) return <div className="text-red-600">{error.message}</div>;

  const deals: Deal[] = data?.deals ?? [];

  return (
    <section className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-semibold">Deals</h2>
        <button
          className="px-3 py-1 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
          onClick={onCreate}
        >
          Create
        </button>
      </div>
      <div className="divide-y divide-slate-100">
        {deals.map((deal) => (
          <button
            key={deal.id}
            className="w-full text-left py-3 flex items-center justify-between hover:bg-slate-50"
            onClick={() => onSelect(deal.id)}
          >
            <div>
              <div className="font-medium">{deal.title}</div>
              <div className="text-xs text-slate-500">{deal.amount} {deal.currency}</div>
            </div>
            <span className={`text-xs px-2 py-1 rounded ${STATUS_TONE[deal.reviewStatus] || "bg-slate-100 text-slate-700"}`}>
              {deal.reviewStatus}
            </span>
          </button>
        ))}
        {deals.length === 0 && <div className="py-4 text-sm text-slate-500">No deals</div>}
      </div>
    </section>
  );
}
