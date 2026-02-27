import { gql, useMutation, useQuery } from "@apollo/client";

const DEAL_QUERY = gql`
  query Deal($id: ID!) {
    deal(id: $id) {
      id
      title
      amount
      currency
      reviewStatus
      reviewReason
    }
  }
`;

const SUBMIT_MUTATION = gql`
  mutation Submit($dealId: ID!) {
    submitDealForReview(dealId: $dealId) {
      id
      reviewStatus
    }
  }
`;

export default function DealDetail({ id }: { id: string }) {
  const { data, loading, error, startPolling, stopPolling } = useQuery(DEAL_QUERY, {
    variables: { id },
    pollInterval: 0
  });

  const [submit, { loading: submitting }] = useMutation(SUBMIT_MUTATION, {
    variables: { dealId: id },
    onCompleted: () => startPolling(2000),
    onError: () => stopPolling()
  });

  if (loading) return <div>Loading deal...</div>;
  if (error) return <div className="text-red-600">{error.message}</div>;

  const deal = data?.deal;
  if (!deal) return <div>No deal found.</div>;
  const canSubmitForReview = deal.reviewStatus === "NOT_REQUIRED";
  const statusTone: Record<string, string> = {
    NOT_REQUIRED: "bg-slate-100 text-slate-700",
    PENDING: "bg-amber-100 text-amber-800",
    APPROVED: "bg-emerald-100 text-emerald-800",
    REJECTED: "bg-rose-100 text-rose-800"
  };
  const statusClass = statusTone[deal.reviewStatus] || "bg-slate-100 text-slate-700";
  const hintText = canSubmitForReview
    ? "Submit for review to trigger the approval workflow."
    : "Review already submitted or completed.";

  return (
    <section className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Deal Detail</h2>
        <div className="flex items-center gap-3">
          <span className={`px-2 py-0.5 text-xs rounded-full ${statusClass}`}>
            {deal.reviewStatus}
          </span>
          {canSubmitForReview && (
            <button
              className="px-3 py-1 text-sm rounded bg-brand-500 text-white disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={() => submit()}
              disabled={submitting}
              aria-disabled={submitting}
            >
              {submitting ? "Submitting..." : "Submit for Review"}
            </button>
          )}
        </div>
      </div>
      <div className="mt-1 text-xs text-slate-500">{hintText}</div>
      <div className="mt-3 text-sm space-y-1">
        <div><span className="text-slate-500">Title:</span> {deal.title}</div>
        <div><span className="text-slate-500">Amount:</span> {deal.amount} {deal.currency}</div>
        <div><span className="text-slate-500">Status:</span> {deal.reviewStatus}</div>
        {deal.reviewReason && <div><span className="text-slate-500">Reason:</span> {deal.reviewReason}</div>}
      </div>
    </section>
  );
}
